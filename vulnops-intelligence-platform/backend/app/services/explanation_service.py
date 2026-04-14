"""Risk Explanation Service - generates human-readable risk explanations.

This service creates explanations that connect risk scores to actual factors,
helping analysts understand why specific vulnerabilities are prioritized.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.oltp import Asset, CveRecord, VulnerabilityFinding
from app.services.risk_engine_service import RiskEngineService


@dataclass
class RiskExplanation:
    """Complete risk explanation for a vulnerability."""
    finding_id: str
    risk_score: float
    overall_assessment: str
    severity_level: str  # Critical, High, Medium, Low
    top_factors: list[dict[str, Any]]
    detailed_explanation: str
    remediation_priority_reason: str
    comparable_examples: list[str]
    generated_at: datetime


class ExplanationService:
    """Generates human-readable explanations for risk scores.
    
    Explanations are grounded in actual risk factors from the prioritization engine,
    ensuring accuracy and relevance. No hallucinated or generic text.
    """

    # Risk score thresholds
    CRITICAL_THRESHOLD = 80
    HIGH_THRESHOLD = 60
    MEDIUM_THRESHOLD = 40
    LOW_THRESHOLD = 20

    def __init__(self, db: Session):
        self.db = db
        self.risk_service = RiskEngineService(db)

    def _get_severity_level(self, score: float) -> str:
        """Determine severity level from risk score."""
        if score >= self.CRITICAL_THRESHOLD:
            return "Critical"
        elif score >= self.HIGH_THRESHOLD:
            return "High"
        elif score >= self.MEDIUM_THRESHOLD:
            return "Medium"
        elif score >= self.LOW_THRESHOLD:
            return "Low"
        return "Minimal"

    def _generate_overall_assessment(
        self,
        score: float,
        cve: CveRecord,
        asset: Asset,
        factors: dict[str, Any],
    ) -> str:
        """Generate overall assessment based on score and context."""
        level = self._get_severity_level(score)
        
        parts = [f"This vulnerability has a {level.lower()} risk score of {score:.1f} out of 100."]
        
        # Add CVSS context
        if cve.cvss_base_score:
            cvss = float(cve.cvss_base_score)
            if cvss >= 9.0:
                parts.append(f"The CVSS score of {cvss:.1f} indicates a critical technical severity.")
            elif cvss >= 7.0:
                parts.append(f"The CVSS score of {cvss:.1f} indicates high technical severity.")
            elif cvss >= 4.0:
                parts.append(f"The CVSS score of {cvss:.1f} indicates moderate technical severity.")
        
        # Add asset context
        criticality_desc = {
            1: "business-critical",
            2: "high-value",
            3: "standard",
            4: "low-priority",
            5: "minimal",
        }
        crit_desc = criticality_desc.get(asset.criticality, "standard")
        parts.append(f"It affects a {crit_desc} asset ({asset.name}).")
        
        # Add exposure context
        if asset.is_external:
            parts.append("The asset is internet-facing, increasing exposure to external threats.")
        
        return " ".join(parts)

    def _generate_detailed_explanation(
        self,
        score: float,
        factors: dict[str, Any],
        contributing: list[dict[str, Any]],
        cve: CveRecord,
        finding: VulnerabilityFinding,
    ) -> str:
        """Generate detailed explanation from contributing factors."""
        explanations = []
        
        # Sort by impact
        high_impact = [f for f in contributing if f.get("impact") == "high"]
        medium_impact = [f for f in contributing if f.get("impact") == "medium"]
        
        # High impact factors
        if high_impact:
            explanations.append("The primary drivers of this risk score are:")
            for factor in high_impact[:3]:
                desc = factor.get("description", "")
                weight = factor.get("weight", 0)
                explanations.append(f"• {desc} (contributes {weight*100:.0f}% to risk calculation)")
        
        # Medium impact factors
        if medium_impact:
            if high_impact:
                explanations.append("\nSecondary factors include:")
            else:
                explanations.append("Contributing factors include:")
            for factor in medium_impact[:2]:
                desc = factor.get("description", "")
                explanations.append(f"• {desc}")
        
        # Age-specific context
        age_score = factors.get("age", 0)
        if age_score > 0.5:
            age_days = int(age_score * 90)
            explanations.append(
                f"\nThis vulnerability has been open for approximately {age_days}+ days, "
                "which increases urgency as the exposure window lengthens."
            )
        
        # Exploit context
        if cve.exploit_available:
            explanations.append(
                "\n⚠️ Publicly available exploit code makes this vulnerability "
                "actively weaponizable by threat actors."
            )
        
        # ML context if available
        ml_score = factors.get("ml_score")
        if ml_score and ml_score > 60:
            explanations.append(
                f"\nOur ML model also flagged this as high-priority "
                f"(predicted urgency: {ml_score:.0f}%)."
            )
        
        return "\n".join(explanations)

    def _generate_remediation_reason(
        self,
        score: float,
        factors: dict[str, Any],
        asset: Asset,
        cve: CveRecord,
        finding: VulnerabilityFinding,
    ) -> str:
        """Generate why this should be prioritized for remediation."""
        reasons = []
        
        # Score-based urgency
        if score >= self.CRITICAL_THRESHOLD:
            reasons.append(
                "This should be your TOP priority for immediate remediation. "
                "Critical-risk vulnerabilities on exposed assets have the highest chance of exploitation."
            )
        elif score >= self.HIGH_THRESHOLD:
            reasons.append(
                "This should be addressed in your current remediation sprint. "
                "The combination of severity and asset exposure creates significant risk."
            )
        elif score >= self.MEDIUM_THRESHOLD:
            reasons.append(
                "Include this in your next remediation cycle. "
                "While not immediate, the cumulative risk warrants attention."
            )
        else:
            reasons.append(
                "Schedule for routine remediation. Monitor for changes in exploit availability "
                "or asset exposure that could increase risk."
            )
        
        # SLA consideration
        if finding.due_at:
            days_to_due = (finding.due_at - datetime.now(timezone.utc)).days
            if days_to_due < 0:
                reasons.append(f"\n⚠️ This finding is {abs(days_to_due)} days PAST its SLA deadline.")
            elif days_to_due < 7:
                reasons.append(f"\n⏰ SLA deadline approaching in {days_to_due} days.")
        
        # Asset-specific context
        if asset.criticality <= 2:
            reasons.append(
                f"\nPriority elevated because {asset.name} is a critical business asset."
            )
        
        if asset.is_external:
            reasons.append(
                "External exposure means this vulnerability is continuously visible "
                "to potential attackers scanning the internet."
            )
        
        return " ".join(reasons)

    def _generate_comparable_examples(
        self,
        score: float,
        cve: CveRecord,
        asset: Asset,
    ) -> list[str]:
        """Generate comparable examples for context."""
        examples = []
        
        if score >= 85:
            examples.append(
                "This risk level is comparable to unpatched remote code execution "
                "vulnerabilities on internet-facing production servers."
            )
        elif score >= 70:
            examples.append(
                "This risk level is comparable to high-severity vulnerabilities on "
                "business-critical internal systems."
            )
        elif score >= 50:
            examples.append(
                "This risk level is comparable to medium-severity vulnerabilities "
                "on standard infrastructure."
            )
        
        # CVSS-specific examples
        if cve.cvss_base_score:
            cvss = float(cve.cvss_base_score)
            if cvss >= 9.0:
                examples.append(
                    "The CVSS score indicates trivial exploitability with complete "
                    "system compromise potential (network attack vector, no user interaction)."
                )
            elif cvss >= 7.0 and cve.exploit_available:
                examples.append(
                    "With public exploit code available, this is similar to vulnerabilities "
                    "that are actively targeted in the wild."
                )
        
        return examples

    def explain_finding(
        self, finding_id: uuid.UUID, tenant_id: uuid.UUID | None = None
    ) -> RiskExplanation | None:
        """Generate comprehensive risk explanation for a vulnerability.
        
        Args:
            finding_id: UUID of the vulnerability finding
            
        Returns:
            RiskExplanation with all explanation components, or None if not found
        """
        # Get finding with related data
        finding = self.db.get(VulnerabilityFinding, finding_id)
        if not finding:
            return None
        if tenant_id is not None and finding.tenant_id != tenant_id:
            return None
        
        asset = self.db.get(Asset, finding.asset_id)
        cve = self.db.get(CveRecord, finding.cve_record_id)
        
        if not asset or not cve:
            return None
        
        # Calculate fresh risk score
        calc = self.risk_service.calculate_risk(finding, asset, cve, use_ml=True)
        
        # Get severity level
        severity = self._get_severity_level(calc.risk_score)
        
        # Generate explanations
        overall = self._generate_overall_assessment(
            calc.risk_score, cve, asset, calc.factors.__dict__
        )
        
        detailed = self._generate_detailed_explanation(
            calc.risk_score,
            calc.factors.__dict__,
            calc.contributing_factors,
            cve,
            finding,
        )
        
        remediation = self._generate_remediation_reason(
            calc.risk_score,
            calc.factors.__dict__,
            asset,
            cve,
            finding,
        )
        
        examples = self._generate_comparable_examples(
            calc.risk_score,
            cve,
            asset,
        )
        
        return RiskExplanation(
            finding_id=str(finding_id),
            risk_score=calc.risk_score,
            overall_assessment=overall,
            severity_level=severity,
            top_factors=calc.contributing_factors,
            detailed_explanation=detailed,
            remediation_priority_reason=remediation,
            comparable_examples=examples,
            generated_at=datetime.now(timezone.utc),
        )

    def explain_top_factors(
        self, finding_id: uuid.UUID, tenant_id: uuid.UUID | None = None
    ) -> list[dict[str, Any]] | None:
        """Get just the top contributing factors for quick display.
        
        Args:
            finding_id: UUID of the vulnerability finding
            
        Returns:
            List of top factors, or None if not found
        """
        finding = self.db.get(VulnerabilityFinding, finding_id)
        if not finding or not finding.risk_factors:
            return None
        if tenant_id is not None and finding.tenant_id != tenant_id:
            return None
        
        return finding.risk_factors.get("contributing_factors", [])

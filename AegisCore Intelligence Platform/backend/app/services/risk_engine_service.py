"""Risk Prioritization Engine - Hybrid rule-based + ML scoring.

This service implements a production-grade vulnerability prioritization engine
that combines deterministic rule-based scoring with optional ML predictions.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.oltp import Asset, CveRecord, VulnerabilityFinding
from app.repositories.finding_repository import FindingRepository
from app.services.prioritization_service import PrioritizationService


@dataclass(frozen=True)
class RiskWeights:
    """Configurable weights for risk scoring components.
    
    All weights should sum to 1.0 for normalized scoring.
    """
    cvss: float = 0.30
    criticality: float = 0.25
    exposure: float = 0.20
    exploit: float = 0.15
    age: float = 0.10
    
    def validate(self) -> bool:
        """Check if weights sum to approximately 1.0."""
        total = self.cvss + self.criticality + self.exposure + self.exploit + self.age
        return 0.99 <= total <= 1.01


@dataclass
class RiskFactors:
    """Individual risk factor scores (0-1 scale)."""
    cvss_score: float
    criticality_score: float
    exposure_score: float
    exploit_score: float
    age_score: float
    ml_probability: float | None = None


@dataclass
class RiskCalculation:
    """Complete risk calculation result."""
    risk_score: float  # 0-100 scale
    rule_based_score: float  # 0-100 scale
    ml_score: float | None  # 0-100 scale
    factors: RiskFactors
    contributing_factors: list[dict[str, Any]]
    calculation_method: str
    calculated_at: datetime


class RiskEngineService:
    """Production-grade risk prioritization engine.
    
    Implements hybrid scoring: 70% rule-based + 30% ML (when available).
    Rule-based scoring uses configurable weights for:
    - CVSS severity (30%)
    - Asset criticality (25%)
    - Internet exposure (20%)
    - Exploit availability (15%)
    - Vulnerability age (10%)
    """

    # Weight configuration
    DEFAULT_WEIGHTS = RiskWeights()
    
    # Age decay: score increases as vulnerability ages
    # After 90 days, age component reaches maximum
    AGE_DECAY_DAYS = 90
    
    # ML ensemble weight (when model available)
    ML_ENSEMBLE_WEIGHT = 0.30
    RULE_ENSEMBLE_WEIGHT = 0.70

    def __init__(self, db: Session, weights: RiskWeights | None = None):
        self.db = db
        self.weights = weights or self.DEFAULT_WEIGHTS
        self.finding_repo = FindingRepository(db)
        self.ml_service = PrioritizationService(db)
        self.settings = get_settings()

    def calculate_risk(
        self,
        finding: VulnerabilityFinding,
        asset: Asset,
        cve: CveRecord,
        use_ml: bool = True,
    ) -> RiskCalculation:
        """Calculate comprehensive risk score for a vulnerability finding.
        
        Args:
            finding: The vulnerability finding record
            asset: The affected asset
            cve: The CVE record
            use_ml: Whether to include ML prediction (if available)
            
        Returns:
            RiskCalculation with scores, factors, and contributing factors
        """
        now = datetime.now(timezone.utc)
        
        # Calculate individual factor scores (0-1 scale)
        factors = self._calculate_factors(finding, asset, cve, now)
        
        # Calculate rule-based score
        rule_score = self._calculate_rule_based_score(factors)
        
        # Get ML score if available and requested
        ml_score: float | None = None
        if use_ml and self.ml_service.model_available():
            try:
                ml_result = self.ml_service.predict_for_finding(finding.id)
                ml_score = ml_result.get("probability_urgent", 0) * 100
            except Exception:
                # ML prediction failed, continue with rule-based only
                pass
        
        # Ensemble: combine rule-based and ML scores
        if ml_score is not None:
            final_score = (
                rule_score * self.RULE_ENSEMBLE_WEIGHT +
                ml_score * self.ML_ENSEMBLE_WEIGHT
            )
            method = "hybrid"
        else:
            final_score = rule_score
            method = "rule_based"
        
        # Round to 2 decimal places
        final_score = round(final_score, 2)
        rule_score = round(rule_score, 2)
        if ml_score is not None:
            ml_score = round(ml_score, 2)
        
        # Determine contributing factors (top drivers)
        contributing = self._identify_contributing_factors(factors, cve, asset)
        
        return RiskCalculation(
            risk_score=final_score,
            rule_based_score=rule_score,
            ml_score=ml_score,
            factors=factors,
            contributing_factors=contributing,
            calculation_method=method,
            calculated_at=now,
        )

    def _calculate_factors(
        self,
        finding: VulnerabilityFinding,
        asset: Asset,
        cve: CveRecord,
        now: datetime,
    ) -> RiskFactors:
        """Calculate individual risk factor scores."""
        
        # CVSS score (normalized 0-1 from 0-10 scale)
        cvss = float(cve.cvss_base_score) if cve.cvss_base_score is not None else 5.0
        cvss_score = min(cvss / 10.0, 1.0)
        
        # Asset criticality (1-5 scale, normalized to 0-1)
        # 1 = Critical, 5 = Low
        criticality = max(1, min(5, asset.criticality))
        criticality_score = (6 - criticality) / 5.0  # Invert: 1->1.0, 5->0.2
        
        # Exposure (internet-facing = 1.0, internal = 0.0)
        exposure_score = 1.0 if asset.is_external else 0.0
        
        # Exploit availability
        exploit_score = 1.0 if cve.exploit_available else 0.0
        
        # Age penalty (linear increase to max at AGE_DECAY_DAYS).
        # SQLite may materialize datetimes as naive even when originally UTC.
        discovered_at = finding.discovered_at
        if discovered_at.tzinfo is None:
            discovered_at = discovered_at.replace(tzinfo=timezone.utc)
        comparison_now = now if now.tzinfo is not None else now.replace(tzinfo=timezone.utc)
        age_days = (comparison_now - discovered_at).days
        age_ratio = min(age_days / self.AGE_DECAY_DAYS, 1.0)
        age_score = age_ratio
        
        return RiskFactors(
            cvss_score=cvss_score,
            criticality_score=criticality_score,
            exposure_score=exposure_score,
            exploit_score=exploit_score,
            age_score=age_score,
        )

    def _calculate_rule_based_score(self, factors: RiskFactors) -> float:
        """Calculate weighted rule-based risk score (0-100 scale)."""
        weighted = (
            factors.cvss_score * self.weights.cvss +
            factors.criticality_score * self.weights.criticality +
            factors.exposure_score * self.weights.exposure +
            factors.exploit_score * self.weights.exploit +
            factors.age_score * self.weights.age
        )
        return weighted * 100

    def _identify_contributing_factors(
        self,
        factors: RiskFactors,
        cve: CveRecord,
        asset: Asset,
    ) -> list[dict[str, Any]]:
        """Identify top contributing factors to risk score."""
        contributions = []
        
        # CVSS contribution
        if factors.cvss_score > 0.7:
            contributions.append({
                "factor": "cvss",
                "weight": self.weights.cvss,
                "score": round(factors.cvss_score, 2),
                "description": f"High CVSS severity ({cve.cvss_base_score}/10)",
                "impact": "high" if factors.cvss_score > 0.8 else "medium",
            })
        
        # Criticality contribution
        if factors.criticality_score > 0.6:
            contributions.append({
                "factor": "criticality",
                "weight": self.weights.criticality,
                "score": round(factors.criticality_score, 2),
                "description": f"Asset criticality level {asset.criticality}/5",
                "impact": "high" if factors.criticality_score > 0.8 else "medium",
            })
        
        # Exposure contribution
        if factors.exposure_score > 0:
            contributions.append({
                "factor": "exposure",
                "weight": self.weights.exposure,
                "score": 1.0,
                "description": "Internet-facing asset exposed to external threats",
                "impact": "high",
            })
        
        # Exploit contribution
        if factors.exploit_score > 0:
            contributions.append({
                "factor": "exploit",
                "weight": self.weights.exploit,
                "score": 1.0,
                "description": "Public exploit code available",
                "impact": "high",
            })
        
        # Age contribution
        if factors.age_score > 0.5:
            contributions.append({
                "factor": "age",
                "weight": self.weights.age,
                "score": round(factors.age_score, 2),
                "description": f"Vulnerability age ({int(factors.age_score * self.AGE_DECAY_DAYS)}+ days)",
                "impact": "medium",
            })
        
        # Sort by impact: high first, then by score descending
        impact_order = {"high": 0, "medium": 1, "low": 2}
        contributions.sort(key=lambda x: (impact_order.get(x["impact"], 3), -x["score"]))
        
        return contributions[:5]  # Top 5 contributing factors

    def recalculate_and_store(
        self,
        finding_id: uuid.UUID,
        tenant_id: uuid.UUID,
        use_ml: bool = True,
    ) -> RiskCalculation | None:
        """Recalculate risk for a finding and store in database.
        
        Args:
            finding_id: UUID of the finding to recalculate
            use_ml: Whether to include ML prediction
            
        Returns:
            RiskCalculation if successful, None if finding not found
        """
        finding = self.finding_repo.get_by_id(finding_id, tenant_id=tenant_id)
        if not finding:
            return None
        
        # Get related records
        asset = self.db.get(Asset, finding.asset_id)
        cve = self.db.get(CveRecord, finding.cve_record_id)
        
        if not asset or not cve:
            return None
        
        # Calculate risk
        calc = self.calculate_risk(finding, asset, cve, use_ml=use_ml)
        
        # Store in database
        finding.risk_score = Decimal(str(calc.risk_score))
        finding.risk_factors = {
            "cvss": calc.factors.cvss_score,
            "criticality": calc.factors.criticality_score,
            "exposure": calc.factors.exposure_score,
            "exploit": calc.factors.exploit_score,
            "age": calc.factors.age_score,
            "ml_probability": calc.factors.ml_probability,
            "rule_based_score": calc.rule_based_score,
            "ml_score": calc.ml_score,
            "contributing_factors": calc.contributing_factors,
            "calculation_method": calc.calculation_method,
        }
        finding.risk_calculated_at = calc.calculated_at
        
        self.db.flush()
        
        return calc

    def recalculate_all_open(
        self,
        tenant_id: uuid.UUID,
        batch_size: int = 100,
        use_ml: bool = True,
    ) -> dict[str, Any]:
        """Recalculate risk for all open vulnerabilities.
        
        Args:
            batch_size: Number of findings to process per batch
            use_ml: Whether to include ML predictions
            
        Returns:
            Statistics about the recalculation
        """
        from sqlalchemy import select
        
        stmt = select(VulnerabilityFinding.id).where(
            VulnerabilityFinding.status.in_(["OPEN", "IN_PROGRESS"]),
            VulnerabilityFinding.tenant_id == tenant_id,
        )
        
        finding_ids = [row[0] for row in self.db.execute(stmt).all()]
        
        updated = 0
        failed = 0
        
        for i, fid in enumerate(finding_ids):
            try:
                calc = self.recalculate_and_store(fid, tenant_id=tenant_id, use_ml=use_ml)
                if calc:
                    updated += 1
                else:
                    failed += 1
            except Exception:
                failed += 1
            
            # Commit every batch
            if (i + 1) % batch_size == 0:
                self.db.commit()
        
        # Final commit
        self.db.commit()
        
        return {
            "total": len(finding_ids),
            "updated": updated,
            "failed": failed,
            "batch_size": batch_size,
        }

    def get_prioritized_findings(
        self,
        tenant_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
        min_risk_score: float | None = None,
        status_filter: str | None = None,
        asset_id: uuid.UUID | None = None,
        business_unit_id: uuid.UUID | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Get vulnerabilities sorted by risk score (highest first).
        
        Returns:
            Tuple of (findings list, total count)
        """
        from sqlalchemy import select, func
        from sqlalchemy.orm import joinedload
        
        # Base query with joins
        stmt = select(VulnerabilityFinding).options(
            joinedload(VulnerabilityFinding.asset),
            joinedload(VulnerabilityFinding.cve_record),
        ).where(VulnerabilityFinding.tenant_id == tenant_id)
        
        # Count query
        count_stmt = select(func.count(VulnerabilityFinding.id)).where(
            VulnerabilityFinding.tenant_id == tenant_id
        )
        
        # Apply filters
        if status_filter:
            stmt = stmt.where(VulnerabilityFinding.status == status_filter)
            count_stmt = count_stmt.where(VulnerabilityFinding.status == status_filter)
        else:
            # Default: only open findings
            stmt = stmt.where(VulnerabilityFinding.status.in_(["OPEN", "IN_PROGRESS"]))
            count_stmt = count_stmt.where(VulnerabilityFinding.status.in_(["OPEN", "IN_PROGRESS"]))
        
        if asset_id:
            stmt = stmt.where(VulnerabilityFinding.asset_id == asset_id)
            count_stmt = count_stmt.where(VulnerabilityFinding.asset_id == asset_id)
        
        if business_unit_id:
            stmt = stmt.join(Asset).where(Asset.business_unit_id == business_unit_id)
            count_stmt = count_stmt.join(Asset).where(Asset.business_unit_id == business_unit_id)
        
        if min_risk_score is not None:
            stmt = stmt.where(VulnerabilityFinding.risk_score >= min_risk_score)
            count_stmt = count_stmt.where(VulnerabilityFinding.risk_score >= min_risk_score)
        
        # Order by risk score descending, then by discovered_at
        stmt = stmt.order_by(
            VulnerabilityFinding.risk_score.desc().nullslast(),
            VulnerabilityFinding.discovered_at.desc(),
        )
        
        # Pagination
        stmt = stmt.offset(offset).limit(limit)
        
        # Execute
        findings = self.db.execute(stmt).scalars().all()
        total = self.db.scalar(count_stmt) or 0
        
        # Enrich with risk data
        results = []
        for f in findings:
            results.append({
                "finding": f,
                "risk_score": float(f.risk_score) if f.risk_score else None,
                "risk_factors": f.risk_factors,
                "asset_name": f.asset.name if f.asset else None,
                "asset_criticality": f.asset.criticality if f.asset else None,
                "cve_id": f.cve_record.cve_id if f.cve_record else None,
                "cvss_score": float(f.cve_record.cvss_base_score) if f.cve_record and f.cve_record.cvss_base_score else None,
            })
        
        return results, int(total)

    def get_risk_percentile(self, finding_id: uuid.UUID, tenant_id: uuid.UUID) -> float | None:
        """Calculate the percentile rank of a finding's risk score.
        
        Returns:
            Percentile (0-100) where 100 = highest risk
        """
        from sqlalchemy import select, func
        
        # Get the finding's risk score
        finding = self.finding_repo.get_by_id(finding_id, tenant_id=tenant_id)
        if not finding or not finding.risk_score:
            return None
        
        score = float(finding.risk_score)
        
        # Count total open findings
        total_stmt = select(func.count()).select_from(VulnerabilityFinding).where(
            VulnerabilityFinding.status.in_(["OPEN", "IN_PROGRESS"]),
            VulnerabilityFinding.tenant_id == tenant_id,
        )
        total = self.db.scalar(total_stmt) or 1
        
        # Count findings with lower risk score.
        lower_stmt = select(func.count()).select_from(VulnerabilityFinding).where(
            VulnerabilityFinding.status.in_(["OPEN", "IN_PROGRESS"]),
            VulnerabilityFinding.tenant_id == tenant_id,
            VulnerabilityFinding.risk_score < score,
        )
        lower_count = self.db.scalar(lower_stmt) or 0

        # Percentile is percentage of findings with lower score.
        # Higher risk => higher percentile.
        percentile = (lower_count / total) * 100
        return round(percentile, 2)

"""What-If Risk Simulation Service - simulate risk reduction scenarios.

Allows users to estimate risk reduction before actually fixing vulnerabilities.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.oltp import Asset, CveRecord, VulnerabilityFinding


@dataclass
class SimulationResult:
    """Risk simulation result."""
    scenario_name: str
    selected_count: int
    before_risk: dict[str, Any]
    after_risk: dict[str, Any]
    reduction_percentage: float
    impacted_assets: list[dict[str, Any]]
    remaining_top_risks: list[dict[str, Any]]


class SimulationService:
    """Service for what-if risk simulation scenarios.
    
    Allows security teams to:
    - Estimate risk reduction from fixing specific vulnerabilities
    - Compare remediation scenarios
    - Identify highest-impact fixes
    """

    def __init__(self, db: Session, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id

    @staticmethod
    def _parse_unique_ids(finding_ids: list[str] | set[str]) -> list[uuid.UUID]:
        parsed: list[uuid.UUID] = []
        seen: set[uuid.UUID] = set()
        for raw in finding_ids:
            fid = uuid.UUID(str(raw))
            if fid in seen:
                continue
            seen.add(fid)
            parsed.append(fid)
        return parsed

    def _calculate_aggregate_risk(
        self,
        finding_ids_to_exclude: set[str] | None = None,
    ) -> dict[str, Any]:
        """Calculate aggregate risk metrics for open vulnerabilities.
        
        Args:
            finding_ids_to_exclude: IDs to exclude (simulating remediation)
            
        Returns:
            Risk metrics including total count, average score, weighted score
        """
        # Base query for open findings
        stmt = select(VulnerabilityFinding).where(
            VulnerabilityFinding.status.in_(["OPEN", "IN_PROGRESS"]),
            VulnerabilityFinding.tenant_id == self.tenant_id,
        )
        
        # Exclude specified IDs
        if finding_ids_to_exclude:
            ids = self._parse_unique_ids(finding_ids_to_exclude)
            stmt = stmt.where(~VulnerabilityFinding.id.in_(ids))
        
        findings = self.db.execute(stmt).scalars().all()
        
        if not findings:
            return {
                "total_count": 0,
                "average_risk_score": 0.0,
                "weighted_risk_score": 0.0,
                "critical_count": 0,  # Risk >= 80
                "high_count": 0,      # Risk >= 60
                "medium_count": 0,    # Risk >= 40
            }
        
        total_count = len(findings)
        
        # Risk score statistics
        risk_scores = [
            float(f.risk_score) if f.risk_score else 50.0  # Default to medium
            for f in findings
        ]
        
        average_score = sum(risk_scores) / len(risk_scores)
        
        # Weighted score (higher weight to high-risk items)
        # Use exponential weighting
        weighted_sum = sum(s ** 2 for s in risk_scores)
        weighted_score = (weighted_sum / len(risk_scores)) ** 0.5
        
        # Count by severity buckets
        critical_count = sum(1 for s in risk_scores if s >= 80)
        high_count = sum(1 for s in risk_scores if 60 <= s < 80)
        medium_count = sum(1 for s in risk_scores if 40 <= s < 60)
        
        return {
            "total_count": total_count,
            "average_risk_score": round(average_score, 2),
            "weighted_risk_score": round(weighted_score, 2),
            "critical_count": critical_count,
            "high_count": high_count,
            "medium_count": medium_count,
        }

    def _get_impacted_assets(
        self,
        finding_ids: list[str],
    ) -> list[dict[str, Any]]:
        """Get list of assets impacted by simulated remediation."""
        ids = self._parse_unique_ids(finding_ids)
        
        stmt = select(
            VulnerabilityFinding.asset_id,
            Asset.name,
            Asset.criticality,
            func.count(VulnerabilityFinding.id).label("finding_count"),
            func.avg(VulnerabilityFinding.risk_score).label("avg_risk"),
        ).join(
            Asset, VulnerabilityFinding.asset_id == Asset.id
        ).where(
            VulnerabilityFinding.id.in_(ids),
            VulnerabilityFinding.tenant_id == self.tenant_id,
        ).group_by(
            VulnerabilityFinding.asset_id,
            Asset.name,
            Asset.criticality,
        )
        
        results = self.db.execute(stmt).all()
        
        return [
            {
                "asset_id": str(row.asset_id),
                "asset_name": row.name,
                "criticality": row.criticality,
                "findings_remediated": row.finding_count,
                "avg_risk_score": round(float(row.avg_risk), 2) if row.avg_risk else None,
            }
            for row in results
        ]

    def _get_remaining_top_risks(
        self,
        exclude_ids: set[str],
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Get top remaining risks after simulation."""
        ids = self._parse_unique_ids(exclude_ids)
        
        stmt = select(
            VulnerabilityFinding,
            CveRecord.cve_id,
            Asset.name,
        ).join(
            CveRecord, VulnerabilityFinding.cve_record_id == CveRecord.id
        ).join(
            Asset, VulnerabilityFinding.asset_id == Asset.id
        ).where(
            VulnerabilityFinding.status.in_(["OPEN", "IN_PROGRESS"]),
            VulnerabilityFinding.tenant_id == self.tenant_id,
            ~VulnerabilityFinding.id.in_(ids),
            VulnerabilityFinding.risk_score.isnot(None),
        ).order_by(
            VulnerabilityFinding.risk_score.desc()
        ).limit(limit)
        
        results = self.db.execute(stmt).all()
        
        return [
            {
                "finding_id": str(row.VulnerabilityFinding.id),
                "cve_id": row.cve_id,
                "asset_name": row.name,
                "risk_score": float(row.VulnerabilityFinding.risk_score),
            }
            for row in results
        ]

    def simulate_remediation(
        self,
        finding_ids: list[str],
        scenario_name: str | None = None,
    ) -> SimulationResult:
        """Simulate risk reduction from remediating specific vulnerabilities.
        
        Args:
            finding_ids: List of finding IDs to simulate remediating
            scenario_name: Optional name for the scenario
            
        Returns:
            SimulationResult with before/after metrics
        """
        # Calculate before state
        before_metrics = self._calculate_aggregate_risk()
        
        # Calculate after state (excluding specified IDs)
        exclude_set = set(finding_ids)
        after_metrics = self._calculate_aggregate_risk(exclude_set)
        
        # Calculate reduction percentage
        if before_metrics["weighted_risk_score"] > 0:
            reduction = (
                (before_metrics["weighted_risk_score"] - after_metrics["weighted_risk_score"])
                / before_metrics["weighted_risk_score"]
            ) * 100
        else:
            reduction = 0.0
        
        # Get impacted assets
        impacted = self._get_impacted_assets(finding_ids)
        
        # Get remaining top risks
        remaining = self._get_remaining_top_risks(exclude_set)
        
        return SimulationResult(
            scenario_name=scenario_name or f"Remediate {len(finding_ids)} vulnerabilities",
            selected_count=len(finding_ids),
            before_risk=before_metrics,
            after_risk=after_metrics,
            reduction_percentage=round(reduction, 2),
            impacted_assets=impacted,
            remaining_top_risks=remaining,
        )

    def compare_scenarios(
        self,
        scenarios: list[tuple[str, list[str]]],
    ) -> list[SimulationResult]:
        """Compare multiple remediation scenarios.
        
        Args:
            scenarios: List of (scenario_name, finding_ids) tuples
            
        Returns:
            List of SimulationResult for comparison
        """
        results = []
        for name, finding_ids in scenarios:
            result = self.simulate_remediation(finding_ids, name)
            results.append(result)
        
        # Sort by reduction percentage (highest first)
        results.sort(key=lambda r: r.reduction_percentage, reverse=True)
        
        return results

    def recommend_high_impact_fixes(
        self,
        max_recommendations: int = 10,
        min_risk_score: float = 60,
    ) -> list[dict[str, Any]]:
        """Recommend highest-impact vulnerabilities to fix.
        
        Considers:
        - Individual risk score
        - Asset criticality
        - Clustering (multiple vulns on same asset)
        
        Returns:
            List of recommended vulnerabilities with impact scores
        """
        # Get high-risk open findings
        stmt = select(
            VulnerabilityFinding,
            CveRecord.cve_id,
            Asset.name,
            Asset.criticality,
            Asset.is_external,
        ).join(
            CveRecord, VulnerabilityFinding.cve_record_id == CveRecord.id
        ).join(
            Asset, VulnerabilityFinding.asset_id == Asset.id
        ).where(
            VulnerabilityFinding.status.in_(["OPEN", "IN_PROGRESS"]),
            VulnerabilityFinding.tenant_id == self.tenant_id,
            VulnerabilityFinding.risk_score >= min_risk_score,
        ).order_by(
            VulnerabilityFinding.risk_score.desc()
        )
        
        results = self.db.execute(stmt).all()
        
        recommendations = []
        seen_assets = set()
        
        for row in results[:max_recommendations * 2]:  # Get more to filter
            finding = row.VulnerabilityFinding
            asset_id = str(finding.asset_id)
            
            # Calculate impact score
            base_score = float(finding.risk_score) if finding.risk_score else 50
            
            # Boost for critical assets
            criticality_boost = (6 - row.criticality) * 5  # 1->25, 5->5
            
            # Boost for external exposure
            external_boost = 10 if row.is_external else 0
            
            # Boost for first finding on an asset (addresses clustering)
            clustering_boost = 5 if asset_id not in seen_assets else 0
            seen_assets.add(asset_id)
            
            impact_score = base_score + criticality_boost + external_boost + clustering_boost
            
            recommendations.append({
                "finding_id": str(finding.id),
                "cve_id": row.cve_id,
                "asset_name": row.name,
                "asset_id": asset_id,
                "risk_score": base_score,
                "impact_score": round(impact_score, 2),
                "reasoning": self._generate_recommendation_reason(
                    base_score, row.criticality, row.is_external, asset_id not in seen_assets
                ),
            })
        
        # Sort by impact score and limit
        recommendations.sort(key=lambda r: r["impact_score"], reverse=True)
        return recommendations[:max_recommendations]

    def _generate_recommendation_reason(
        self,
        risk_score: float,
        criticality: int,
        is_external: bool,
        is_first_on_asset: bool,
    ) -> str:
        """Generate human-readable recommendation reason."""
        reasons = []
        
        if risk_score >= 80:
            reasons.append("critical risk score")
        elif risk_score >= 60:
            reasons.append("high risk score")
        
        if criticality <= 2:
            reasons.append("critical asset")
        
        if is_external:
            reasons.append("internet-facing")
        
        if is_first_on_asset:
            reasons.append("highest risk on this asset")
        
        if reasons:
            return f"Recommended because: {', '.join(reasons)}"
        return "Standard remediation candidate"

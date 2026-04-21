from __future__ import annotations

import uuid
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.oltp import Asset, AssetDependency, VulnerabilityFinding


@dataclass
class BlastRadius:
    start_asset_id: str
    max_depth: int
    total_impacted_assets: int
    internet_exposed_assets: int
    high_risk_findings_in_radius: int
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]


class AttackPathService:
    OPEN_STATUSES = ("OPEN", "IN_PROGRESS", "RISK_ACCEPTED")

    def __init__(self, db: Session, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id

    def from_finding(self, finding_id: str, max_depth: int = 3) -> BlastRadius | None:
        try:
            fid = uuid.UUID(str(finding_id))
        except ValueError:
            raise ValueError("Invalid finding id") from None
        finding = self.db.execute(
            select(VulnerabilityFinding).where(
                VulnerabilityFinding.id == fid,
                VulnerabilityFinding.tenant_id == self.tenant_id,
            )
        ).scalar_one_or_none()
        if finding is None:
            return None
        return self.from_asset(str(finding.asset_id), max_depth=max_depth)

    def from_asset(self, asset_id: str, max_depth: int = 3) -> BlastRadius | None:
        try:
            start_id = uuid.UUID(str(asset_id))
        except ValueError:
            raise ValueError("Invalid asset id") from None

        start_asset = self.db.execute(
            select(Asset).where(Asset.id == start_id, Asset.tenant_id == self.tenant_id)
        ).scalar_one_or_none()
        if start_asset is None:
            return None

        dep_rows = self.db.execute(
            select(AssetDependency).where(AssetDependency.tenant_id == self.tenant_id)
        ).scalars().all()
        adjacency: dict[uuid.UUID, list[AssetDependency]] = defaultdict(list)
        for dep in dep_rows:
            adjacency[dep.source_asset_id].append(dep)

        visited: set[uuid.UUID] = {start_id}
        q: deque[tuple[uuid.UUID, int]] = deque([(start_id, 0)])
        edge_list: list[dict[str, Any]] = []

        while q:
            current, depth = q.popleft()
            if depth >= max_depth:
                continue
            for dep in adjacency.get(current, []):
                edge_list.append(
                    {
                        "source_asset_id": str(dep.source_asset_id),
                        "target_asset_id": str(dep.target_asset_id),
                        "dependency_type": dep.dependency_type,
                        "trust_level": dep.trust_level,
                        "lateral_movement_score": float(dep.lateral_movement_score)
                        if dep.lateral_movement_score is not None
                        else None,
                    }
                )
                if dep.target_asset_id not in visited:
                    visited.add(dep.target_asset_id)
                    q.append((dep.target_asset_id, depth + 1))

        assets = self.db.execute(
            select(Asset).where(Asset.id.in_(visited), Asset.tenant_id == self.tenant_id)
        ).scalars().all()
        asset_map = {a.id: a for a in assets}

        finding_stats = self.db.execute(
            select(
                VulnerabilityFinding.asset_id,
                func.count(VulnerabilityFinding.id).label("open_cnt"),
                func.sum(
                    case((VulnerabilityFinding.risk_score >= 70, 1), else_=0)
                ).label("high_cnt"),
                func.max(VulnerabilityFinding.risk_score).label("max_risk"),
            )
            .where(
                VulnerabilityFinding.tenant_id == self.tenant_id,
                VulnerabilityFinding.asset_id.in_(visited),
                VulnerabilityFinding.status.in_(self.OPEN_STATUSES),
            )
            .group_by(VulnerabilityFinding.asset_id)
        ).all()
        stat_map = {
            r.asset_id: {
                "open_cnt": int(r.open_cnt or 0),
                "high_cnt": int(r.high_cnt or 0),
                "max_risk": float(r.max_risk) if r.max_risk is not None else None,
            }
            for r in finding_stats
        }

        nodes: list[dict[str, Any]] = []
        internet_exposed_assets = 0
        high_risk_findings = 0
        for aid in visited:
            asset = asset_map.get(aid)
            if asset is None:
                continue
            stats = stat_map.get(aid, {"open_cnt": 0, "high_cnt": 0, "max_risk": None})
            if asset.is_external:
                internet_exposed_assets += 1
            high_risk_findings += int(stats["high_cnt"])
            nodes.append(
                {
                    "asset_id": str(asset.id),
                    "asset_name": asset.name,
                    "asset_type": asset.asset_type,
                    "criticality": asset.criticality,
                    "is_external": bool(asset.is_external),
                    "open_findings": int(stats["open_cnt"]),
                    "high_risk_findings": int(stats["high_cnt"]),
                    "max_risk_score": stats["max_risk"],
                }
            )

        return BlastRadius(
            start_asset_id=str(start_id),
            max_depth=max_depth,
            total_impacted_assets=len(nodes),
            internet_exposed_assets=internet_exposed_assets,
            high_risk_findings_in_radius=high_risk_findings,
            nodes=nodes,
            edges=edge_list,
        )


class AttackPathSimulationService(AttackPathService):
    """Backward-compatible alias for legacy imports."""

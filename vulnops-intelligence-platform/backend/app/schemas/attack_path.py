from __future__ import annotations

from pydantic import BaseModel, Field


class AttackPathNode(BaseModel):
    asset_id: str
    asset_name: str
    asset_type: str
    criticality: int
    is_external: bool
    open_findings: int
    high_risk_findings: int
    max_risk_score: float | None


class AttackPathEdge(BaseModel):
    source_asset_id: str
    target_asset_id: str
    dependency_type: str
    trust_level: str
    lateral_movement_score: float | None


class BlastRadiusResponse(BaseModel):
    start_asset_id: str
    max_depth: int = Field(ge=1, le=8)
    total_impacted_assets: int
    internet_exposed_assets: int
    high_risk_findings_in_radius: int
    nodes: list[AttackPathNode]
    edges: list[AttackPathEdge]

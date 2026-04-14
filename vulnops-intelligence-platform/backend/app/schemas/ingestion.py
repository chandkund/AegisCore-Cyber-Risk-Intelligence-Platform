from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

ConnectorProvider = Literal["nessus", "qualys", "defender", "crowdstrike", "wiz"]


class ConnectorIngestRequest(BaseModel):
    records: list[dict[str, Any]] = Field(min_length=1, max_length=10000)
    watermark: datetime | None = None
    dry_run: bool = False


class ConnectorIngestResponse(BaseModel):
    provider: ConnectorProvider
    received_records: int
    normalized_records: int
    deduplicated_records: int
    created_assets: int
    created_cves: int
    created_findings: int
    updated_findings: int
    source_confidence_avg: float
    high_confidence_records: int
    watermark_updated: bool

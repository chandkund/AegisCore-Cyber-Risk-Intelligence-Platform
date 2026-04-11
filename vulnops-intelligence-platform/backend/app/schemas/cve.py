from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class CveRecordOut(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    cve_id: str
    title: str | None
    description: str | None
    published_at: datetime | None
    last_modified_at: datetime | None
    cvss_base_score: Decimal | None
    cvss_vector: str | None
    severity: str
    epss_score: Decimal | None
    exploit_available: bool

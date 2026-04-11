from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ExplainFeature(BaseModel):
    name: str
    value: float


class MlPredictionResponse(BaseModel):
    finding_id: str
    probability_urgent: float = Field(ge=0.0, le=1.0)
    explain: list[ExplainFeature]
    reference_time_utc: str


class MlModelInfoResponse(BaseModel):
    inference_enabled: bool
    model_loaded: bool
    artifact_path: str
    model_name: str | None = None
    model_version: str | None = None
    trained_at_utc: str | None = None
    metrics_holdout: dict[str, Any] | None = None
    n_samples: int | None = None

from __future__ import annotations

import uuid

from app.api.deps import ReaderDep
from app.db.deps import get_db
from app.schemas.ml import MlModelInfoResponse, MlPredictionResponse
from app.services.prioritization_service import PrioritizationService
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

router = APIRouter(prefix="/ml", tags=["ml"])


@router.get("/model-info", response_model=MlModelInfoResponse)
def model_info(_: ReaderDep, db: Session = Depends(get_db)):
    svc = PrioritizationService(db)
    meta = svc.metadata_payload()
    return MlModelInfoResponse(
        inference_enabled=meta.get("inference_enabled", False),
        model_loaded=meta.get("model_loaded", False),
        artifact_path=meta.get("artifact_path", ""),
        model_name=meta.get("model_name"),
        model_version=meta.get("model_version"),
        trained_at_utc=meta.get("trained_at_utc"),
        metrics_holdout=meta.get("metrics_holdout"),
        n_samples=meta.get("n_samples"),
    )


@router.post(
    "/predict/finding/{finding_id}",
    response_model=MlPredictionResponse,
)
def predict_finding(
    _: ReaderDep,
    finding_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    svc = PrioritizationService(db)
    try:
        out = svc.predict_for_finding(finding_id)
    except RuntimeError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ML inference disabled or model artifact missing",
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Finding not found",
        )
    return MlPredictionResponse(
        finding_id=out["finding_id"],
        probability_urgent=out["probability_urgent"],
        explain=out["explain"],
        reference_time_utc=out["reference_time_utc"],
    )

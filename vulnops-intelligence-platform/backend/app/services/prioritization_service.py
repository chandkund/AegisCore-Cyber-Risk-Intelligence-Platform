from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.ml.prioritizer import load_model_bundle
from app.repositories.prioritization_repository import PrioritizationRepository

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from ml.features.engineering import rows_from_db_records  # noqa: E402
from ml.inference.predict import explain_with_preprocess, predict_urgent_probability  # noqa: E402


class PrioritizationService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = PrioritizationRepository(db)
        self.settings = get_settings()

    def _bundle(self) -> dict[str, Any] | None:
        if not self.settings.ml_inference_enabled:
            return None
        path = self.settings.ml_model_path_resolved
        return load_model_bundle(path)

    def model_available(self) -> bool:
        return self._bundle() is not None

    def metadata_payload(self) -> dict[str, Any]:
        bundle = self._bundle()
        if bundle is None:
            return {
                "inference_enabled": bool(self.settings.ml_inference_enabled),
                "model_loaded": False,
                "artifact_path": str(self.settings.ml_model_path_resolved),
            }
        meta = dict(bundle["metadata"])
        meta["inference_enabled"] = bool(self.settings.ml_inference_enabled)
        meta["model_loaded"] = True
        meta["artifact_path"] = str(self.settings.ml_model_path_resolved)
        return meta

    def predict_for_finding(self, finding_id: uuid.UUID) -> dict[str, Any]:
        bundle = self._bundle()
        if bundle is None:
            raise RuntimeError("model_unavailable")
        row = self.repo.get_finding_feature_row(finding_id)
        if row is None:
            raise ValueError("finding_not_found")
        ref = datetime.now(timezone.utc)
        X, _ = rows_from_db_records([row], ref)
        pipe = bundle["pipeline"]
        prob = float(predict_urgent_probability(pipe, X)[0])
        explain = explain_with_preprocess(pipe, X, top_k=8)
        return {
            "finding_id": str(finding_id),
            "probability_urgent": prob,
            "explain": explain,
            "reference_time_utc": ref.isoformat(),
        }

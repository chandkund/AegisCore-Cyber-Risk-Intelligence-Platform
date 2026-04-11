from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import joblib
from app.main import app
from fastapi.testclient import TestClient


def test_model_info_requires_auth():
    client = TestClient(app)
    r = client.get("/api/v1/ml/model-info")
    assert r.status_code == 401


def test_metadata_with_bundle(monkeypatch, tmp_path: Path):
    from datetime import datetime, timezone

    from app.core.config import reset_settings_cache
    from app.ml.prioritizer import clear_bundle_cache

    from ml.features.engineering import rows_from_db_records
    from ml.features.synthetic import generate_synthetic_records
    from ml.training.train_prioritizer import train

    recs = generate_synthetic_records(80, seed=3)
    ref = datetime.now(timezone.utc)
    X, y = rows_from_db_records(recs, ref)
    pipe, meta = train(X, y)
    p = tmp_path / "bundle.joblib"
    joblib.dump({"pipeline": pipe, "metadata": meta}, p)

    monkeypatch.setenv("ML_MODEL_PATH", str(p))
    reset_settings_cache()
    clear_bundle_cache()

    from app.services.prioritization_service import PrioritizationService

    svc = PrioritizationService(MagicMock())
    m = svc.metadata_payload()
    assert m.get("model_loaded") is True
    assert m.get("model_version") is not None

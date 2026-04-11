from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np

from ml.features.synthetic import generate_synthetic_records
from ml.inference.predict import load_bundle, predict_urgent_probability
from ml.training.train_prioritizer import train


def test_end_to_end_train_predict(tmp_path: Path):
    recs = generate_synthetic_records(120, seed=7)
    from datetime import datetime, timezone

    from ml.features.engineering import rows_from_db_records

    ref = datetime.now(timezone.utc)
    X, y = rows_from_db_records(recs, ref)
    assert len(np.unique(y)) >= 1
    pipe, meta = train(X, y)
    assert "metrics_holdout" in meta
    out = tmp_path / "m.joblib"
    joblib.dump({"pipeline": pipe, "metadata": meta}, out)
    bundle = load_bundle(out)
    prob = predict_urgent_probability(bundle["pipeline"], X.iloc[:3])
    assert prob.shape == (3,)
    assert float(prob[0]) >= 0.0

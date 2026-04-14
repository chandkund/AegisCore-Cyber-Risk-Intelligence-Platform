"""Load model bundle and score single-row feature frames."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline


def load_bundle(path: Path | str) -> dict[str, Any]:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(str(p))
    bundle = joblib.load(p)
    if not isinstance(bundle, dict) or "pipeline" not in bundle or "metadata" not in bundle:
        raise ValueError("Invalid bundle format")
    if not isinstance(bundle["pipeline"], Pipeline):
        raise TypeError("Bundle pipeline must be sklearn Pipeline")
    return bundle


def predict_urgent_probability(pipeline: Pipeline, X: pd.DataFrame) -> np.ndarray:
    """Return P(urgent) for each row (binary positive class index 1)."""
    proba = pipeline.predict_proba(X)
    if proba.shape[1] < 2:
        return proba[:, 0]
    return proba[:, 1]


def explain_with_preprocess(
    pipeline: Pipeline, X: pd.DataFrame, top_k: int = 8
) -> list[dict[str, Any]]:
    """
    Approximate local explanation: show transformed feature columns with largest
    absolute contribution proxy (gradient-free: use preprocessed values * coef unavailable for HGB).

    For tree ensembles we report global feature names from the preprocessor
    and per-row preprocessed numeric snapshot (first row).
    """
    prep = pipeline.named_steps.get("preprocess")
    if prep is None:
        return []
    Xt = prep.transform(X)
    if hasattr(Xt, "toarray"):
        Xt = Xt.toarray()
    row = np.asarray(Xt[0]).ravel()
    names: list[str] = []
    if hasattr(prep, "get_feature_names_out"):
        names = list(prep.get_feature_names_out())
    else:
        names = [f"f{i}" for i in range(len(row))]
    pairs = sorted(
        zip(names, row.tolist()),
        key=lambda x: abs(float(x[1])),
        reverse=True,
    )[:top_k]
    return [{"name": n, "value": float(v)} for n, v in pairs]

#!/usr/bin/env python3
"""
Train the risk prioritization classifier.

Examples:
  python -m ml.training.train_prioritizer --source synthetic --output ml/models/artifacts/risk_prioritization.joblib
  python -m ml.training.train_prioritizer --source db --output ml/models/artifacts/risk_prioritization.joblib
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from ml.evaluation.report import classification_metrics
from ml.features.dataset import fetch_training_records, reference_time
from ml.features.engineering import FEATURE_COLUMNS_ORDER, rows_from_db_records
from ml.features.synthetic import generate_synthetic_records, synthetic_label_balance

MODEL_NAME = "vulnops_risk_prioritizer"
MODEL_VERSION = "1.0.0"


def build_pipeline() -> Pipeline:
    numeric_features = [
        "cvss",
        "epss",
        "exploit",
        "asset_criticality",
        "days_open",
        "days_until_due",
        "has_assignee",
        "text_n_tokens",
    ]
    categorical_features = ["severity_str", "status_str"]

    numeric_transformer = Pipeline(
        steps=[("imputer", SimpleImputer(strategy="median"))],
    )
    categorical_transformer = OneHotEncoder(handle_unknown="ignore", sparse_output=False)

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, numeric_features),
            ("cat", categorical_transformer, categorical_features),
        ]
    )

    clf = HistGradientBoostingClassifier(
        max_depth=8,
        learning_rate=0.08,
        max_iter=200,
        random_state=42,
    )
    return Pipeline(steps=[("preprocess", preprocessor), ("classifier", clf)])


def train(
    X: pd.DataFrame,
    y: np.ndarray,
) -> tuple[Pipeline, dict]:
    strat = y if len(np.unique(y)) > 1 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=strat
    )
    pipe = build_pipeline()
    pipe.fit(X_train, y_train)
    prob = pipe.predict_proba(X_test)[:, 1]
    metrics = classification_metrics(y_test, prob)
    meta = {
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "n_samples": int(len(X)),
        "n_positive_labels": int(y.sum()),
        "n_negative_labels": int(len(y) - y.sum()),
        "feature_columns": FEATURE_COLUMNS_ORDER,
        "metrics_holdout": metrics,
        "classifier": "HistGradientBoostingClassifier",
    }
    return pipe, meta


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--source", choices=("db", "synthetic"), required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--synthetic-n", type=int, default=800)
    p.add_argument("--min-rows", type=int, default=20)
    args = p.parse_args()

    ref = reference_time()
    if args.source == "synthetic":
        recs = generate_synthetic_records(args.synthetic_n)
        pos, neg = synthetic_label_balance(recs)
        print(f"Synthetic label mix: urgent={pos}, not_urgent={neg}")
    else:
        recs = fetch_training_records()
        if len(recs) < args.min_rows:
            print(f"Only {len(recs)} DB rows; augmenting with synthetic data.")
            extra = generate_synthetic_records(max(args.synthetic_n, args.min_rows - len(recs)))
            recs = recs + extra

    X, y = rows_from_db_records(recs, ref)
    if len(X) < 10:
        raise SystemExit("Not enough rows to train (need >= 10).")

    pipe, meta = train(X, y)
    bundle = {"pipeline": pipe, "metadata": meta}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, args.output)
    sidecar = args.output.with_suffix(".meta.json")
    sidecar.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"Wrote {args.output} and {sidecar}")


if __name__ == "__main__":
    main()

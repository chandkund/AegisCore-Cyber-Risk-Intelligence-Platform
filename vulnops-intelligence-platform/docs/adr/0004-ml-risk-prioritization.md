# ADR 0004: Scikit-learn proxy-label prioritization model

- **Status:** Accepted
- **Date:** 2026-04-11
- **Context:** Phase 4 requires an explainable baseline for vulnerability prioritization integrated with the API without standing up a separate prediction service.
- **Decision:**
  - Implement training and feature logic under repository root `ml/`.
  - Persist a **joblib bundle** `{pipeline, metadata}` consumed by the FastAPI app.
  - Resolve the artifact path via `ML_MODEL_PATH` with fallback relative to the monorepo root (see `Settings.ml_model_path_resolved`).
  - Inject the repo root onto `sys.path` in `app/ml/prioritizer.py` and `app/services/prioritization_service.py` so `import ml.*` works without a separate installable package.
- **Consequences:**
  - **Pros:** Single repo, clear interview story, fast iteration, OpenAPI-discoverable inference.
  - **Cons:** `sys.path` coupling; production may prefer an installable package or gRPC sidecar later.
  - **Follow-up:** Pluggable model registry, calibrated probabilities, deep embeddings, shadow evaluation against analyst outcomes.

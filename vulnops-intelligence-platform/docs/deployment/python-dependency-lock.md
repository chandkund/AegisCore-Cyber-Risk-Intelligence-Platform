# Python dependency locking (`pip-tools`)

## Why

Pinned transitive dependencies improve **reproducible builds** and make CVE triage easier than floating `>=` ranges alone.

## Repository layout (Phase 10+)

| File | Role |
|------|------|
| `backend/requirements/base.in` | **Source** — direct runtime dependencies (ranges). |
| `backend/requirements/base.txt` | **Generated** — `pip-compile` output (committed). |
| `backend/requirements/dev.in` | **Source** — dev tools; uses `-c base.txt`. |
| `backend/requirements/dev.txt` | **Generated**. |
| `backend/requirements.txt` | Aggregator `-r` both (CI / local install). |
| `backend/pyproject.toml` | `[tool.pip-tools]` — `no_header`, `strip_extras`, `newline = "lf"`. |
| `.python-version` | **3.12** — use this Python when regenerating locks (matches CI). |

## Regenerate locks (local)

From **`backend/`** (so `pyproject.toml` is discovered):

```bash
python -m pip install "pip-tools>=7,<8"
python -m piptools compile requirements/base.in -o requirements/base.txt --resolver=backtracking
python -m piptools compile requirements/dev.in -o requirements/dev.txt --resolver=backtracking
```

Commit **`base.txt`** and **`dev.txt`**. CI **`requirements-lock`** fails if they drift.

## Optional hashes

Enable **`generate_hashes = true`** under `[tool.pip-tools]` when you want `pip hash` style lines (slower PRs, stronger install integrity).

## Scripts

[scripts/compile_python_requirements.sh](../../scripts/compile_python_requirements.sh) documents the same commands for POSIX shells.

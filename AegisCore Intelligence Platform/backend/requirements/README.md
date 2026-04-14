# Python requirements

Sources are **`*.in`**; committed pins are **`*.txt`** produced by **`pip-compile`** (see [python-dependency-lock.md](../../docs/deployment/python-dependency-lock.md)). CI job **`requirements-lock`** fails if `base.txt` / `dev.txt` drift from a fresh compile.

| File | Role |
|------|------|
| `base.in` | **Source** — direct runtime dependencies (version ranges). |
| `base.txt` | **Generated** — full lock from `base.in` (committed). |
| `dev.in` | **Source** — lint/test/type tools; constrained with `-c base.txt`. |
| `dev.txt` | **Generated** (committed). |
| `../requirements.txt` | Aggregator (`-r requirements/base.txt` + `-r requirements/dev.txt`) for CI and `pip install -r backend/requirements.txt`. |

Regenerate from **`backend/`** (Python **3.12**, see repo root `.python-version`):

```bash
python -m pip install "pip-tools>=7,<8"
python -m piptools compile requirements/base.in -o requirements/base.txt --resolver=backtracking
python -m piptools compile requirements/dev.in -o requirements/dev.txt --resolver=backtracking
```

Or from repo root: `bash scripts/compile_python_requirements.sh`.

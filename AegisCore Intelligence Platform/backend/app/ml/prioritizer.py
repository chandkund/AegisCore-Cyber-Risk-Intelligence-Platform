from __future__ import annotations

import functools
import sys
from pathlib import Path
from typing import Any

# ML module path resolution - repo root must be in sys.path for ml.* imports
# This works in Docker where backend/ and ml/ are siblings under /app
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:
    from ml.inference.predict import load_bundle  # noqa: E402
except ImportError as e:
    raise ImportError(
        f"Failed to import ml.inference.predict. "
        f"Ensure repo root ({_REPO_ROOT}) is in PYTHONPATH. "
        f"Original error: {e}"
    ) from e


@functools.lru_cache(maxsize=8)
def _cached_bundle(path_str: str, mtime: float) -> dict[str, Any]:
    return load_bundle(path_str)


def load_model_bundle(model_path: Path) -> dict[str, Any] | None:
    if not model_path.is_file():
        return None
    mtime = model_path.stat().st_mtime
    return _cached_bundle(str(model_path.resolve()), mtime)


def clear_bundle_cache() -> None:
    _cached_bundle.cache_clear()

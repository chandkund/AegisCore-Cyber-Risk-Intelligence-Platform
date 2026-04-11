"""Simple per-IP sliding window for login attempts (no Redis required)."""

from __future__ import annotations

import threading
import time
from collections import defaultdict

_lock = threading.Lock()
_buckets: dict[str, list[float]] = defaultdict(list)


def allow_login_attempt(
    client_ip: str, *, max_attempts: int = 30, window_seconds: int = 60
) -> bool:
    key = client_ip or "unknown"
    now = time.monotonic()
    with _lock:
        q = _buckets[key]
        q[:] = [t for t in q if now - t < window_seconds]
        if len(q) >= max_attempts:
            return False
        q.append(now)
        return True


def reset_for_tests() -> None:
    with _lock:
        _buckets.clear()

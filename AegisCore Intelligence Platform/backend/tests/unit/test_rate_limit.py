from __future__ import annotations

import time

import pytest

from app.middleware.login_rate_limit import allow_login_attempt, reset_for_tests


@pytest.fixture(autouse=True)
def reset_buckets(monkeypatch: pytest.MonkeyPatch):
    """Reset rate limit buckets before each test."""
    monkeypatch.setenv("AEGISCORE_TEST_MODE", "false")
    reset_for_tests()
    yield
    reset_for_tests()


def test_allow_login_attempts_within_limit():
    """Login attempts within limit should be allowed."""
    client_ip = "192.168.1.1"
    for i in range(5):
        assert allow_login_attempt(client_ip, max_attempts=10, window_seconds=60)


def test_block_after_max_attempts():
    """Login attempts beyond max should be blocked."""
    client_ip = "192.168.1.2"
    max_attempts = 3
    window = 60

    # First N attempts allowed
    for _ in range(max_attempts):
        assert allow_login_attempt(client_ip, max_attempts=max_attempts, window_seconds=window)

    # (max_attempts+1)th attempt blocked
    assert not allow_login_attempt(client_ip, max_attempts=max_attempts, window_seconds=window)


def test_different_ips_independent():
    """Rate limiting should be per-IP."""
    ip1 = "192.168.1.3"
    ip2 = "192.168.1.4"

    # Block ip1
    for _ in range(5):
        allow_login_attempt(ip1, max_attempts=5, window_seconds=60)
    assert not allow_login_attempt(ip1, max_attempts=5, window_seconds=60)

    # ip2 should still be allowed
    assert allow_login_attempt(ip2, max_attempts=5, window_seconds=60)


def test_window_slide_allows_after_time():
    """Old attempts should expire from window."""
    client_ip = "192.168.1.5"
    window = 1  # 1 second window for fast test

    # Use up the limit
    for _ in range(5):
        allow_login_attempt(client_ip, max_attempts=5, window_seconds=window)
    assert not allow_login_attempt(client_ip, max_attempts=5, window_seconds=window)

    # Wait for window to slide
    time.sleep(1.1)

    # Should be allowed again
    assert allow_login_attempt(client_ip, max_attempts=5, window_seconds=window)


def test_empty_ip_defaults_to_unknown():
    """Empty/None IP should use 'unknown' bucket."""
    # Empty string
    assert allow_login_attempt("", max_attempts=5, window_seconds=60)
    # None
    assert allow_login_attempt(None, max_attempts=5, window_seconds=60)


def test_sliding_window_cleans_old_entries():
    """Old entries should be cleaned when checking."""
    client_ip = "192.168.1.6"
    window = 2

    # Add attempts
    for _ in range(5):
        allow_login_attempt(client_ip, max_attempts=10, window_seconds=window)

    # Wait for half to expire
    time.sleep(1.1)

    # Add more - this should trigger cleanup
    for _ in range(3):
        allow_login_attempt(client_ip, max_attempts=10, window_seconds=window)

    # Should still have capacity (old ones cleaned)
    assert allow_login_attempt(client_ip, max_attempts=10, window_seconds=window)

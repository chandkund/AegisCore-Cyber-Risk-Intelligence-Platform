from __future__ import annotations

import uuid

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)


def test_password_roundtrip():
    h = hash_password("CorrectHorseBatteryStaple!9")
    assert verify_password("CorrectHorseBatteryStaple!9", h)
    assert not verify_password("wrong", h)


def test_refresh_hash_stable():
    assert hash_refresh_token("abc") == hash_refresh_token("abc")
    assert hash_refresh_token("abc") != hash_refresh_token("abd")


def test_jwt_access_roundtrip():
    uid = uuid.uuid4()
    token = create_access_token(subject=uid, roles=["analyst"])
    payload = decode_access_token(token)
    assert payload["sub"] == str(uid)
    assert payload["roles"] == ["analyst"]
    assert payload["typ"] == "access"

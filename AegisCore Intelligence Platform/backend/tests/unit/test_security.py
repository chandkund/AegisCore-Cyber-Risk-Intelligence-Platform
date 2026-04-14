from __future__ import annotations

import time
import uuid
from datetime import timedelta

import jwt
import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.core.config import get_settings


def test_password_roundtrip():
    h = hash_password("CorrectHorseBatteryStaple!9")
    assert verify_password("CorrectHorseBatteryStaple!9", h)
    assert not verify_password("wrong", h)


def test_refresh_hash_stable():
    assert hash_refresh_token("abc") == hash_refresh_token("abc")
    assert hash_refresh_token("abc") != hash_refresh_token("abd")


def test_jwt_access_roundtrip():
    uid = uuid.uuid4()
    tid = uuid.uuid4()
    token = create_access_token(subject=uid, roles=["analyst"], tenant_id=tid)
    payload = decode_access_token(token)
    assert payload["sub"] == str(uid)
    assert payload["tid"] == str(tid)
    assert payload["roles"] == ["analyst"]
    assert payload["typ"] == "access"


def test_expired_token_rejected():
    """Expired tokens must be rejected."""
    uid = uuid.uuid4()
    tid = uuid.uuid4()
    token = create_access_token(
        subject=uid,
        roles=["analyst"],
        tenant_id=tid,
        expires_delta=timedelta(seconds=1),
    )
    time.sleep(1.5)
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token)


def test_tampered_token_rejected():
    """Tampered tokens must be rejected."""
    uid = uuid.uuid4()
    token = create_access_token(subject=uid, roles=["analyst"], tenant_id=uuid.uuid4())
    tampered = token[:-10] + "TAMPERED!!"
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(tampered)


def test_wrong_secret_rejected():
    """Tokens signed with wrong secret must be rejected."""
    uid = uuid.uuid4()
    fake_token = jwt.encode(
        {"sub": str(uid), "roles": ["admin"], "typ": "access"},
        "wrong-secret-key-32chars-minimum!!",
        algorithm="HS256",
    )
    with pytest.raises(jwt.InvalidSignatureError):
        decode_access_token(fake_token)


def test_missing_claims_rejected():
    """Tokens without required claims must be rejected."""
    settings = get_settings()
    # Missing 'sub' claim
    token = jwt.encode(
        {"roles": ["analyst"], "typ": "access"},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(jwt.MissingRequiredClaimError):
        decode_access_token(token)

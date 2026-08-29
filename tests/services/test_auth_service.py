"""Tests for services/auth.py: password hashing and JWT create/decode.

Pure logic, no DB involved.
"""

from datetime import datetime, timedelta, timezone

import jwt
import pytest

from config import ALGORITHM, SECRET_KEY
from services import auth


def test_hash_password_round_trip():
    hashed = auth.hash_password("correct-horse")
    assert hashed != "correct-horse"
    assert auth.verify_password("correct-horse", hashed) is True


def test_verify_password_rejects_wrong_password():
    hashed = auth.hash_password("correct-horse")
    assert auth.verify_password("wrong-password", hashed) is False


def test_verify_password_rejects_unusable_placeholder_hash():
    # "!" is the unusable hash used for anonymized placeholder users; it must
    # never validate against any password, and must not raise.
    assert auth.verify_password("anything", "!") is False


def test_create_and_decode_access_token_round_trip():
    token = auth.create_access_token("42")
    assert auth.decode_token(token) == "42"


def test_decode_token_rejects_garbage_token():
    with pytest.raises(auth.InvalidTokenError):
        auth.decode_token("not-a-real-jwt")


def test_decode_token_rejects_expired_token():
    expired_payload = {
        "sub": "1",
        "iat": datetime.now(timezone.utc) - timedelta(minutes=10),
        "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
    }
    expired_token = jwt.encode(expired_payload, SECRET_KEY, algorithm=ALGORITHM)

    with pytest.raises(auth.InvalidTokenError):
        auth.decode_token(expired_token)


def test_decode_token_rejects_missing_sub_claim():
    payload = {
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    with pytest.raises(auth.InvalidTokenError):
        auth.decode_token(token)

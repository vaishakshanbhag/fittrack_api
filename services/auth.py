"""Authentication primitives: password hashing and JWT create/decode.

Pure logic with no FastAPI/web concerns — the request-layer dependency that
turns a token into the current user lives in ``deps.py``.
"""

from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from config import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEY

# ``recommended()`` selects Argon2id (via the argon2 extra) with sensible
# parameters. Hash format is self-describing, so it can be upgraded later.
_password_hash = PasswordHash.recommended()


class InvalidTokenError(Exception):
    """Raised when a JWT is missing, malformed, expired, or otherwise invalid."""


def hash_password(password: str) -> str:
    """Return a secure hash of the given plaintext password."""
    return _password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Return True if the password matches the hash.

    Returns False (rather than raising) for malformed/unusable hashes, so the
    anonymized placeholder accounts (hash ``"!"``) can never authenticate.
    """
    try:
        return _password_hash.verify(password, hashed_password)
    except Exception:
        return False


def create_access_token(subject: str) -> str:
    """Create a signed JWT whose ``sub`` claim identifies the user."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> str:
    """Validate a JWT and return its ``sub`` claim, or raise InvalidTokenError."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc
    subject = payload.get("sub")
    if subject is None:
        raise InvalidTokenError("token missing 'sub' claim")
    return subject

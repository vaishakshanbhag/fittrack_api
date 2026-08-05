"""FastAPI request-layer dependencies for authentication.

``get_current_user`` is the guard applied to protected routes: it validates the
bearer token and resolves it to the owning ``User`` row.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from db import get_db
from models.db_models import User
from services import auth

# tokenUrl points at the login endpoint so Swagger's "Authorize" button works.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

_credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Validate the bearer token and return the authenticated user.

    Raises 401 for any failure: bad/expired token, non-integer subject, or a
    user that no longer exists.
    """
    try:
        subject = auth.decode_token(token)
        user_id = int(subject)
    except (auth.InvalidTokenError, ValueError):
        raise _credentials_exception

    user = db.get(User, user_id)
    if user is None:
        raise _credentials_exception
    return user

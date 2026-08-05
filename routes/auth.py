from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from db import get_db
from models.auth import Token
from models.user import UserIn, UserOut
from services import auth, users

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def signup(payload: UserIn, db: Session = Depends(get_db)):
    """Register a new user account and return the created user."""
    try:
        return users.create_user(db, payload)
    except users.EmailAlreadyRegisteredError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Authenticate with email (as 'username') and password; return a JWT.

    Uses the OAuth2 password flow so the interactive docs 'Authorize' button
    works. The form 'username' field carries the user's email.
    """
    user = users.authenticate(db, form_data.username, form_data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=auth.create_access_token(str(user.id)))

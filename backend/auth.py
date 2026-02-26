"""JWT-based authentication utilities for FastAPI."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import User, get_db

# ---------------------------------------------------------------------------
# Password hashing (using bcrypt directly — passlib is unmaintained)
# ---------------------------------------------------------------------------


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches the bcrypt *hashed* value."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def hash_password(password: str) -> str:
    """Return a bcrypt hash of *password*."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


# ---------------------------------------------------------------------------
# OAuth2 scheme (auto_error=False for optional auth)
# ---------------------------------------------------------------------------

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login",
    auto_error=False,
)

# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------


def create_access_token(user_id: int) -> str:
    """Create a signed JWT containing the user id as the subject claim."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_expire_minutes,
    )
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    """Decode the JWT and return the corresponding User, or None on any failure.

    Returning None (instead of raising) allows routes to support optional
    authentication.
    """
    if token is None:
        return None
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        user_id: str | None = payload.get("sub")
        if user_id is None:
            return None
    except JWTError:
        return None

    user = db.query(User).filter(User.id == int(user_id)).first()
    return user


async def require_current_user(
    user: User | None = Depends(get_current_user),
) -> User:
    """Dependency that enforces authentication.

    Raises HTTP 401 if no valid user was resolved.
    """
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

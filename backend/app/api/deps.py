"""FastAPI dependencies: DB session and current user from JWT.

SECURITY: Supports JWT from:
1. Authorization header (for API clients)
2. httpOnly cookie (for web frontend)
"""
from typing import Generator, Optional

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.core.security import decode_access_token
from app.models.user import User

security = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user_id(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> int:
    """
    Extract user ID from JWT token.
    SECURITY: Checks both Authorization header and httpOnly cookie.
    Header takes precedence over cookie.
    """
    token = None

    # Try from Authorization header first (for API clients)
    if credentials:
        token = credentials.credentials
    # Fall back to httpOnly cookie (for web frontend)
    elif "bharat_owner_token" in request.cookies:
        token = request.cookies["bharat_owner_token"]

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    sub = decode_access_token(token)
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return int(sub)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def get_current_user(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> User:
    """Load current user from DB."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


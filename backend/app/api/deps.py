"""FastAPI dependencies: DB session and current user from JWT."""
from typing import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.core.security import decode_access_token
from app.models.user import User

# Owner Website uses Bearer JWT
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)
security = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> int:
    """Extract user id from JWT. Trust: all owner APIs require valid JWT."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
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

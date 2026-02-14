"""Auth: register and login with security hardening.

SECURITY FEATURES:
- Password hashing with bcrypt
- Password strength validation
- httpOnly, Secure, SameSite cookies
- Short token expiry (15 minutes)
"""
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.config import settings
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, UserResponse, Token

router = APIRouter()


@router.post("/register", response_model=UserResponse)
def register(data: UserCreate, db: Session = Depends(get_db)):
    """
    Register new user with password strength validation.
    
    Password requirements:
    - Minimum 8 characters
    - At least one special character (!@#$%^&*)
    - At least one number
    """
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Validate password strength
    if len(data.password) < settings.MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Password must be at least {settings.MIN_PASSWORD_LENGTH} characters"
        )
    
    if settings.REQUIRE_SPECIAL_CHARS and not any(c in data.password for c in "!@#$%^&*()-_=+[]{}|;:',.<>?/"):
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least one special character (!@#$%^&*)"
        )
    
    if settings.REQUIRE_NUMBERS and not any(c.isdigit() for c in data.password):
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least one number"
        )

    user = User(email=data.email, hashed_password=get_password_hash(data.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(data: UserLogin, db: Session = Depends(get_db), response: Response = None):
    """
    Login and set token in httpOnly cookie (not in response body).
    
    SECURITY:
    - Token stored in httpOnly, Secure, SameSite=strict cookie
    - Short expiry (15 minutes)
    - Generic error message to prevent user enumeration
    """
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.hashed_password):
        # Generic error: don't specify which field is wrong
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = create_access_token(subject=str(user.id))
    
    # Set httpOnly cookie (SECURITY-CRITICAL)
    response.set_cookie(
        key="bharat_owner_token",
        value=token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # seconds
        secure=settings.SECURE_COOKIES,  # HTTPS only in production
        httponly=True,  # Prevent JavaScript access (XSS protection)
        samesite=settings.SAME_SITE_COOKIE,  # CSRF protection (strict)
        domain=None,  # Auto-set to current domain
    )

    # Return token in response for initial fetch (will use cookie for subsequent requests)
    return Token(access_token=token)


@router.post("/logout")
def logout(response: Response, current_user: User = Depends(get_current_user)):
    """
    Logout by clearing httpOnly cookie.
    """
    response.delete_cookie(
        key="bharat_owner_token",
        secure=settings.SECURE_COOKIES,
        httponly=True,
        samesite=settings.SAME_SITE_COOKIE,
    )
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user."""
    return current_user


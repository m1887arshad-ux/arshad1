"""Application configuration with security-first defaults.

Environment variables override all defaults.
CRITICAL: SECRET_KEY must be set in .env - will fail fast if missing in production.
"""

import os
from pathlib import Path
from typing import List


# Load .env for local development (safe no-op if not installed)
try:
    from dotenv import load_dotenv  # type: ignore

    _BACKEND_DIR = Path(__file__).resolve().parents[2]
    load_dotenv(dotenv_path=_BACKEND_DIR / ".env", override=False)
except Exception:
    pass


class Settings:
    # Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./bharat.db")

    # JWT Security - CRITICAL
    SECRET_KEY: str = os.getenv("SECRET_KEY", None)
    if not SECRET_KEY:
        # In production, this will fail immediately (no weak defaults)
        # Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
        if os.getenv("ENVIRONMENT", "development") == "production":
            raise ValueError(
                "⛔ CRITICAL: SECRET_KEY must be set in production environment. "
                "Generate with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
        import warnings
        warnings.warn(
            "⚠️  SECRET_KEY not set in environment. Using development default. "
            "CHANGE THIS BEFORE PRODUCTION. "
            "Set SECRET_KEY in .env to a strong random value.",
            RuntimeWarning
        )
        SECRET_KEY = "development-only-weak-default-change-in-production"

    ALGORITHM: str = "HS256"
    # Token expiry: 15 minutes (not 7 days)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    # Refresh token: 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 1

    # CORS (Restrictive - specific origins only, no wildcards)
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3002",
        "http://localhost:3003",
        "http://127.0.0.1:3003"
    ]

    # Security Headers
    SECURE_COOKIES: bool = os.getenv("ENVIRONMENT", "development") == "production"
    SAME_SITE_COOKIE: str = "strict"  # Prevent CSRF
    HTTP_ONLY_COOKIE: bool = True  # Prevent XSS token theft

    # Telegram Bot (Must be set via .env, never in code)
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")

    # Groq API Key (Must be set via .env, never in code)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

    # Rate Limiting (NEW SECURITY)
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_WINDOW_SECONDS: int = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))

    # Password Policy (NEW SECURITY)
    MIN_PASSWORD_LENGTH: int = 12  # NIST 800-63B recommendation
    REQUIRE_SPECIAL_CHARS: bool = True
    REQUIRE_NUMBERS: bool = True

    # Security Features
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = ENVIRONMENT == "development"


settings = Settings()

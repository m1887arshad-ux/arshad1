import os
from pathlib import Path
from typing import List

try:
    from dotenv import load_dotenv

    _BACKEND_DIR = Path(__file__).resolve().parents[2]
    load_dotenv(dotenv_path=_BACKEND_DIR / ".env", override=False)
except Exception:
    pass


class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./bharat.db")
    
    SECRET_KEY: str = os.getenv("SECRET_KEY", None)
    if not SECRET_KEY:
        import secrets
        SECRET_KEY = secrets.token_urlsafe(32)
        import warnings
        warnings.warn(
            "⚠️  SECRET_KEY not set - auto-generated secure random key for this session. "
            "For production: Set SECRET_KEY environment variable. "
            f"Generated key: {SECRET_KEY[:8]}... (save this if persistence needed)",
            RuntimeWarning
        )

    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 1

    CORS_ORIGINS: List[str] = os.getenv("CORS_ALLOW_ORIGIN", "").split(",") if os.getenv("CORS_ALLOW_ORIGIN") else [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3002",
        "http://localhost:3003",
        "http://127.0.0.1:3003"
    ]

    SECURE_COOKIES: bool = os.getenv("ENVIRONMENT", "development") == "production"
    SAME_SITE_COOKIE: str = "strict"
    HTTP_ONLY_COOKIE: bool = True

    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_WINDOW_SECONDS: int = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))

    MIN_PASSWORD_LENGTH: int = 8
    REQUIRE_SPECIAL_CHARS: bool = True
    REQUIRE_NUMBERS: bool = True

    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = ENVIRONMENT == "development"


settings = Settings()

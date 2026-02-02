"""Application configuration. Environment variables override defaults."""
import os
from typing import List


class Settings:
    # Database: SQLite local-first (hackathon safe)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./bharat.db")

    # JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production-hackathon-secret")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # CORS (Owner Website)
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000", 
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001"
    ]

    # Telegram (optional for local run without bot)
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")


settings = Settings()

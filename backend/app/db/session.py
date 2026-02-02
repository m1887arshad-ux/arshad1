"""Database session. SQLite compatible."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.base import Base

# SQLite needs check_same_thread=False for FastAPI
connect_args = {} if not settings.DATABASE_URL.startswith("sqlite") else {"check_same_thread": False}
engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

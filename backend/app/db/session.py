"""Database session. SQLite compatible with connection pooling."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.base import Base

connect_args = (
    {"check_same_thread": False}
    if settings.DATABASE_URL.startswith("sqlite")
    else {}
)

# Configure connection pooling for better concurrency
if settings.DATABASE_URL.startswith("sqlite"):
    # SQLite: Use NullPool for thread-safety
    from sqlalchemy.pool import NullPool
    engine = create_engine(
        settings.DATABASE_URL, 
        connect_args=connect_args,
        poolclass=NullPool
    )
else:
    # PostgreSQL/MySQL: Use QueuePool with sensible defaults
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args=connect_args,
        pool_size=5,  # Number of persistent connections
        max_overflow=10,  # Max temporary connections
        pool_timeout=30,  # Seconds to wait for connection
        pool_recycle=3600,  # Recycle connections after 1 hour
        pool_pre_ping=True  # Verify connection health
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

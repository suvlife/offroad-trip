"""Database setup - supports PostgreSQL (prod) and SQLite (local dev fallback).

Auto-falls back to SQLite if psycopg2 is not installed (local dev without Docker).
"""

import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

logger = logging.getLogger(__name__)

# Determine the actual database URL
_db_url = settings.DATABASE_URL

# If using PostgreSQL but psycopg2 is not installed, fall back to SQLite
if _db_url.startswith("postgresql"):
    try:
        import psycopg2  # noqa: F401
    except ImportError:
        _db_url = "sqlite:///./offroadtrip.db"
        logger.warning("psycopg2 not installed - falling back to SQLite for local dev")

# Pick the right engine based on final URL
if _db_url.startswith("sqlite"):
    engine = create_engine(
        _db_url,
        connect_args={"check_same_thread": False},
        echo=settings.DEBUG,
    )
    logger.info("Using SQLite database (local dev mode)")
else:
    engine = create_engine(_db_url, echo=settings.DEBUG, pool_pre_ping=True)
    logger.info("Using PostgreSQL database")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency: yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables. Called on startup (dev mode)."""
    # Import models so SQLAlchemy registers them before create_all
    from app.models import route  # noqa: F401

    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized")

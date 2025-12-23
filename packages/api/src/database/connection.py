"""Database connection - connects to engine's signals.db"""

import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base

# Path to engine's signals database
ENGINE_PATH = Path(__file__).parent.parent.parent.parent / "engine"
DATABASE_PATH = ENGINE_PATH / "signals.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite specific
    pool_pre_ping=True
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base for models (if needed)
Base = declarative_base()


def get_db() -> Session:
    """
    Get database session.

    Yields:
        Database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database connection"""
    # Check if database exists
    if not DATABASE_PATH.exists():
        print(f"⚠️  Warning: Database not found at {DATABASE_PATH}")
        print("   Make sure the signal service has run at least once.")
        return False

    print(f"✅ Connected to database: {DATABASE_PATH}")
    return True

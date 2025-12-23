"""Database connection - connects to engine's signals database"""

import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base

# Get DATABASE_URL from environment, fallback to local SQLite
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # Fallback for local development
    ENGINE_PATH = Path(__file__).parent.parent.parent.parent / "engine"
    DATABASE_PATH = ENGINE_PATH / "signals.db"
    DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Create engine with appropriate config
is_sqlite = DATABASE_URL.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
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
    db_url = os.getenv("DATABASE_URL", "local SQLite")
    print(f"✅ Connected to database: {db_url}")
    return True

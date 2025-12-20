"""
Database connection management.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import os
from pathlib import Path

# Default database URL (SQLite for development)
DEFAULT_DATABASE_URL = "sqlite:///signals.db"


class DatabaseManager:
    """Manages database connections and sessions."""

    def __init__(self, database_url: str = None):
        """
        Initialize database manager.

        Args:
            database_url: SQLAlchemy database URL. If None, uses DEFAULT_DATABASE_URL
        """
        self.database_url = database_url or os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
        self.engine = None
        self.SessionLocal = None
        self._initialize()

    def _initialize(self):
        """Initialize database engine and session factory."""
        # Create engine
        self.engine = create_engine(
            self.database_url,
            echo=False,  # Set to True for SQL logging
            pool_pre_ping=True,  # Verify connections before using
        )

        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )

    def get_session(self) -> Session:
        """
        Get a new database session.

        Returns:
            SQLAlchemy Session
        """
        return self.SessionLocal()

    @contextmanager
    def session_scope(self):
        """
        Provide a transactional scope for database operations.

        Usage:
            with db_manager.session_scope() as session:
                session.add(signal)
                # Automatically commits or rolls back
        """
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def close(self):
        """Close database connections."""
        if self.engine:
            self.engine.dispose()


# Global database manager instance
_db_manager = None


def get_db_manager(database_url: str = None) -> DatabaseManager:
    """
    Get or create global database manager instance.

    Args:
        database_url: Database URL (only used on first call)

    Returns:
        DatabaseManager instance
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager(database_url)
    return _db_manager


def get_db() -> Session:
    """
    Dependency function for FastAPI to get database session.

    Usage in FastAPI:
        @app.get("/signals")
        def get_signals(db: Session = Depends(get_db)):
            ...
    """
    db_manager = get_db_manager()
    db = db_manager.get_session()
    try:
        yield db
    finally:
        db.close()


if __name__ == "__main__":
    # Test database connection
    print("Testing database connection...")
    db_manager = DatabaseManager()
    print(f"✅ Connected to: {db_manager.database_url}")

    with db_manager.session_scope() as session:
        print("✅ Session created successfully")

    db_manager.close()
    print("✅ Connection closed")

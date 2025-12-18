#!/usr/bin/env python3
"""
Database initialization script.

This script initializes the database tables for the Gold Trader's Edge application.
Run this before starting the API for the first time.

Usage:
    python scripts/init_db.py

    Or with environment variable for a different database:
    DATABASE_URL=postgresql://user:pass@host:5432/db python scripts/init_db.py
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set up logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def init_database():
    """Initialize the database with all required tables."""
    from api.database.connection import init_db, check_db_connection, engine
    from api.core.config import settings

    logger.info("=" * 60)
    logger.info("Gold Trader's Edge - Database Initialization")
    logger.info("=" * 60)

    # Log database URL (masking password)
    db_url = settings.DATABASE_URL
    if '@' in db_url:
        # Mask the password in the URL
        parts = db_url.split('@')
        prefix = parts[0].rsplit(':', 1)[0]  # Remove password
        masked_url = f"{prefix}:****@{parts[1]}"
    else:
        masked_url = db_url

    logger.info(f"Database URL: {masked_url}")

    # Check connection
    logger.info("Testing database connection...")
    if check_db_connection():
        logger.info("✓ Database connection successful")
    else:
        logger.error("✗ Database connection failed!")
        logger.error("Please ensure the database server is running and the URL is correct.")
        logger.error("For local development, start PostgreSQL with:")
        logger.error("  docker-compose up -d postgres")
        return False

    # Initialize tables
    logger.info("Creating database tables...")
    try:
        init_db()
        logger.info("✓ Database tables created successfully")
    except Exception as e:
        logger.error(f"✗ Failed to create tables: {e}")
        return False

    # List created tables
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    logger.info(f"\nCreated tables ({len(tables)}):")
    for table in sorted(tables):
        columns = inspector.get_columns(table)
        logger.info(f"  - {table} ({len(columns)} columns)")

    logger.info("\n" + "=" * 60)
    logger.info("Database initialization complete!")
    logger.info("=" * 60)

    return True


def reset_database():
    """Drop and recreate all tables (WARNING: destroys all data)."""
    from api.database.connection import Base, engine

    logger.warning("=" * 60)
    logger.warning("WARNING: This will DELETE all existing data!")
    logger.warning("=" * 60)

    confirm = input("Type 'yes' to confirm: ")
    if confirm.lower() != 'yes':
        logger.info("Operation cancelled.")
        return False

    logger.info("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    logger.info("✓ Tables dropped")

    return init_database()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Initialize the Gold Trader's Edge database"
    )
    parser.add_argument(
        '--reset',
        action='store_true',
        help='Drop and recreate all tables (WARNING: destroys data)'
    )

    args = parser.parse_args()

    if args.reset:
        success = reset_database()
    else:
        success = init_database()

    sys.exit(0 if success else 1)

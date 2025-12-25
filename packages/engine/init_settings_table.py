#!/usr/bin/env python3
"""
Initialize Settings Table

Creates the settings table and seeds it with default values.
Run this once after deploying the settings management system.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from database.connection import DatabaseManager
from database.settings_models import Setting, Base
from database.settings_repository import SettingsRepository
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Initialize settings table and seed defaults"""
    logger.info("=" * 70)
    logger.info("SETTINGS TABLE INITIALIZATION")
    logger.info("=" * 70)

    # Get database URL from environment
    import os
    database_url = os.getenv(
        'DATABASE_URL',
        'postgresql://postgres:postgres@localhost:5432/gold_signals'
    )

    logger.info(f"\n📡 Connecting to database...")
    logger.info(f"   URL: {database_url[:30]}...")

    # Create database manager
    db_manager = DatabaseManager(database_url)

    # Create settings table if it doesn't exist
    logger.info(f"\n📊 Creating settings table...")
    try:
        # Import all models to ensure they're registered
        from database.settings_models import Setting

        # Create table
        Base.metadata.create_all(bind=db_manager.engine)
        logger.info("   ✅ Settings table created (or already exists)")
    except Exception as e:
        logger.error(f"   ❌ Failed to create table: {e}")
        return 1

    # Seed default settings
    logger.info(f"\n🌱 Seeding default settings...")
    try:
        with db_manager.session_scope() as session:
            repo = SettingsRepository(session)
            repo.initialize_defaults()
        logger.info("   ✅ Default settings initialized")
    except Exception as e:
        logger.error(f"   ❌ Failed to seed defaults: {e}")
        return 1

    # Display current settings
    logger.info(f"\n📋 Current Settings Summary:")
    logger.info("=" * 70)

    with db_manager.session_scope() as session:
        repo = SettingsRepository(session)
        settings = repo.get_all()

        logger.info(f"\n   Total settings: {len(settings)}")

        for category in ['trading', 'risk_management', 'strategies', 'notifications', 'system']:
            from database.settings_models import SettingCategory
            try:
                cat_enum = SettingCategory(category)
                cat_settings = repo.get_by_category(cat_enum)
                logger.info(f"\n   {category.upper().replace('_', ' ')} ({len(cat_settings)} settings):")
                for s in cat_settings:
                    logger.info(f"      • {s.key}: {s.get_typed_value()}")
            except ValueError:
                pass

    logger.info("\n" + "=" * 70)
    logger.info("✅ INITIALIZATION COMPLETE!")
    logger.info("=" * 70)
    logger.info("\nNext steps:")
    logger.info("1. Access settings via API: GET /v1/settings")
    logger.info("2. Update settings via API: PUT /v1/settings/{key}")
    logger.info("3. View by category: GET /v1/settings/categories")
    logger.info("\nSettings are now managed via database - no need to redeploy!")

    return 0


if __name__ == "__main__":
    sys.exit(main())

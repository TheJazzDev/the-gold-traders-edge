"""
Settings Repository

Provides database operations for settings management.
Includes caching for performance and automatic initialization.
"""

import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from database.settings_models import Setting, SettingCategory, DEFAULT_SETTINGS

logger = logging.getLogger(__name__)


class SettingsRepository:
    """Repository for managing application settings"""

    def __init__(self, session: Session):
        self.session = session
        self._cache: Dict[str, Setting] = {}

    def initialize_defaults(self):
        """
        Initialize default settings if they don't exist.
        Called on application startup.
        """
        for setting_data in DEFAULT_SETTINGS:
            existing = self.session.query(Setting).filter_by(key=setting_data['key']).first()

            if not existing:
                setting = Setting(**setting_data)
                self.session.add(setting)
                logger.info(f"Initialized setting: {setting_data['key']} = {setting_data['value']}")

        self.session.commit()
        logger.info(f"✅ Settings initialized ({len(DEFAULT_SETTINGS)} total)")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a setting value by key.

        Args:
            key: Setting key
            default: Default value if setting not found

        Returns:
            Typed setting value or default
        """
        # Check cache first
        if key in self._cache:
            return self._cache[key].get_typed_value()

        # Query database
        setting = self.session.query(Setting).filter_by(key=key).first()

        if not setting:
            logger.warning(f"Setting '{key}' not found, using default: {default}")
            return default

        # Cache it
        self._cache[key] = setting
        return setting.get_typed_value()

    def get_setting(self, key: str) -> Optional[Setting]:
        """Get Setting object by key"""
        return self.session.query(Setting).filter_by(key=key).first()

    def set(self, key: str, value: Any, modified_by: str = "system") -> bool:
        """
        Update a setting value.

        Args:
            key: Setting key
            value: New value
            modified_by: User/system that made the change

        Returns:
            True if updated successfully
        """
        setting = self.session.query(Setting).filter_by(key=key).first()

        if not setting:
            logger.error(f"Cannot set unknown setting: {key}")
            return False

        if not setting.editable:
            logger.error(f"Setting '{key}' is not editable")
            return False

        # Validate value range
        if setting.value_type in ['int', 'float']:
            numeric_value = float(value)
            if setting.min_value is not None and numeric_value < setting.min_value:
                logger.error(f"Value {value} below minimum {setting.min_value} for '{key}'")
                return False
            if setting.max_value is not None and numeric_value > setting.max_value:
                logger.error(f"Value {value} above maximum {setting.max_value} for '{key}'")
                return False

        # Update value
        setting.set_typed_value(value)
        setting.last_modified_by = modified_by
        self.session.commit()

        # Clear cache
        if key in self._cache:
            del self._cache[key]

        logger.info(f"✅ Updated setting: {key} = {value} (by {modified_by})")

        if setting.requires_restart:
            logger.warning(f"⚠️  Setting '{key}' requires service restart to take effect")

        return True

    def get_by_category(self, category: SettingCategory) -> List[Setting]:
        """Get all settings in a category"""
        return self.session.query(Setting).filter_by(category=category).all()

    def get_all(self) -> List[Setting]:
        """Get all settings"""
        return self.session.query(Setting).all()

    def get_all_as_dict(self) -> Dict[str, Any]:
        """
        Get all settings as a dictionary with typed values.

        Returns:
            Dictionary of key: typed_value
        """
        settings = self.get_all()
        return {s.key: s.get_typed_value() for s in settings}

    def reset_to_default(self, key: str, modified_by: str = "system") -> bool:
        """Reset a setting to its default value"""
        setting = self.session.query(Setting).filter_by(key=key).first()

        if not setting:
            return False

        setting.value = setting.default_value
        setting.last_modified_by = modified_by
        self.session.commit()

        # Clear cache
        if key in self._cache:
            del self._cache[key]

        logger.info(f"Reset setting '{key}' to default: {setting.default_value}")
        return True

    def reset_all_to_defaults(self, modified_by: str = "system"):
        """Reset all settings to their default values"""
        settings = self.get_all()

        for setting in settings:
            if setting.editable:
                setting.value = setting.default_value
                setting.last_modified_by = modified_by

        self.session.commit()
        self._cache.clear()

        logger.info("Reset all settings to defaults")

    def clear_cache(self):
        """Clear the settings cache"""
        self._cache.clear()
        logger.debug("Settings cache cleared")


class SettingsManager:
    """
    Singleton settings manager for easy access throughout the application.

    Usage:
        from database.settings_repository import settings_manager

        # Get settings
        auto_trading = settings_manager.get('auto_trading_enabled', default=False)
        max_risk = settings_manager.get('max_risk_per_trade', default=1.0)

        # Update settings
        settings_manager.set('max_risk_per_trade', 2.0, modified_by='admin')
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SettingsManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._db_manager = None
        self._initialized = True

    def initialize(self, db_manager):
        """
        Initialize the settings manager with a database connection.

        Args:
            db_manager: DatabaseManager instance
        """
        self._db_manager = db_manager

        # Initialize default settings if needed
        with db_manager.session_scope() as session:
            repo = SettingsRepository(session)
            repo.initialize_defaults()

        logger.info("✅ SettingsManager initialized")

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value"""
        if not self._db_manager:
            logger.warning("SettingsManager not initialized, using default")
            return default

        with self._db_manager.session_scope() as session:
            repo = SettingsRepository(session)
            return repo.get(key, default)

    def set(self, key: str, value: Any, modified_by: str = "system") -> bool:
        """Update a setting value"""
        if not self._db_manager:
            logger.error("SettingsManager not initialized")
            return False

        with self._db_manager.session_scope() as session:
            repo = SettingsRepository(session)
            return repo.set(key, value, modified_by)

    def get_all_as_dict(self) -> Dict[str, Any]:
        """Get all settings as a dictionary"""
        if not self._db_manager:
            logger.error("SettingsManager not initialized")
            return {}

        with self._db_manager.session_scope() as session:
            repo = SettingsRepository(session)
            return repo.get_all_as_dict()


# Global singleton instance
settings_manager = SettingsManager()

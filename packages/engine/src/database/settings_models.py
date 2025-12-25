"""
Settings Models for Database-Driven Configuration

Allows runtime configuration changes without redeploying the service.
Settings are stored in PostgreSQL and can be updated via web admin panel.
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, Enum as SQLEnum
from sqlalchemy.sql import func
from database.base import Base
import enum


class SettingCategory(enum.Enum):
    """Categories for organizing settings"""
    TRADING = "trading"
    RISK_MANAGEMENT = "risk_management"
    STRATEGIES = "strategies"
    NOTIFICATIONS = "notifications"
    SYSTEM = "system"


class Setting(Base):
    """
    System-wide configuration settings.

    This table stores all configurable parameters that can be modified
    through the admin panel without redeploying the service.
    """
    __tablename__ = 'settings'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Setting identification
    key = Column(String(100), unique=True, nullable=False, index=True)
    category = Column(SQLEnum(SettingCategory), nullable=False, index=True)

    # Value (stored as string, converted to appropriate type by application)
    value = Column(String(500), nullable=False)
    value_type = Column(String(20), nullable=False)  # 'string', 'int', 'float', 'bool', 'json'
    default_value = Column(String(500), nullable=False)

    # Metadata
    description = Column(String(500))
    unit = Column(String(20))  # '%', 'USD', 'pips', etc.
    min_value = Column(Float)
    max_value = Column(Float)

    # UI hints
    editable = Column(Boolean, default=True)  # Can be changed via UI
    requires_restart = Column(Boolean, default=False)  # Does changing this require service restart?

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_modified_by = Column(String(100))  # User who last changed this setting

    def get_typed_value(self):
        """Convert string value to appropriate Python type"""
        if self.value_type == 'bool':
            return self.value.lower() in ['true', '1', 'yes']
        elif self.value_type == 'int':
            return int(self.value)
        elif self.value_type == 'float':
            return float(self.value)
        elif self.value_type == 'json':
            import json
            return json.loads(self.value)
        else:
            return self.value

    def set_typed_value(self, value):
        """Set value from Python type"""
        if self.value_type == 'bool':
            self.value = 'true' if value else 'false'
        elif self.value_type == 'json':
            import json
            self.value = json.dumps(value)
        else:
            self.value = str(value)

    def __repr__(self):
        return f"<Setting(key='{self.key}', value='{self.value}', category='{self.category.value}')>"


# Default settings that will be seeded on first run
DEFAULT_SETTINGS = [
    # ==================== TRADING SETTINGS ====================
    {
        'key': 'auto_trading_enabled',
        'category': SettingCategory.TRADING,
        'value': 'false',
        'value_type': 'bool',
        'default_value': 'false',
        'description': 'Enable automatic trade execution on MT5 account',
        'editable': True,
        'requires_restart': True,
    },
    {
        'key': 'trading_symbol',
        'category': SettingCategory.TRADING,
        'value': 'XAUUSD',
        'value_type': 'string',
        'default_value': 'XAUUSD',
        'description': 'Trading symbol (default: Gold)',
        'editable': True,
        'requires_restart': True,
    },
    {
        'key': 'dry_run_mode',
        'category': SettingCategory.TRADING,
        'value': 'false',
        'value_type': 'bool',
        'default_value': 'false',
        'description': 'Dry run mode - log trades but don\'t execute them',
        'editable': True,
        'requires_restart': True,
    },
    {
        'key': 'enabled_timeframes',
        'category': SettingCategory.TRADING,
        'value': '["5m", "15m", "30m", "1h", "4h", "1d"]',
        'value_type': 'json',
        'default_value': '["5m", "15m", "30m", "1h", "4h", "1d"]',
        'description': 'Timeframes to monitor for signals',
        'editable': True,
        'requires_restart': True,
    },

    # ==================== RISK MANAGEMENT ====================
    {
        'key': 'max_risk_per_trade',
        'category': SettingCategory.RISK_MANAGEMENT,
        'value': '1.0',
        'value_type': 'float',
        'default_value': '1.0',
        'description': 'Maximum risk per trade',
        'unit': '%',
        'min_value': 0.1,
        'max_value': 10.0,
        'editable': True,
        'requires_restart': False,
    },
    {
        'key': 'max_positions',
        'category': SettingCategory.RISK_MANAGEMENT,
        'value': '5',
        'value_type': 'int',
        'default_value': '5',
        'description': 'Maximum number of concurrent positions',
        'min_value': 1,
        'max_value': 20,
        'editable': True,
        'requires_restart': False,
    },
    {
        'key': 'max_daily_loss',
        'category': SettingCategory.RISK_MANAGEMENT,
        'value': '3.0',
        'value_type': 'float',
        'default_value': '3.0',
        'description': 'Maximum daily loss limit',
        'unit': '%',
        'min_value': 1.0,
        'max_value': 20.0,
        'editable': True,
        'requires_restart': False,
    },
    {
        'key': 'max_weekly_loss',
        'category': SettingCategory.RISK_MANAGEMENT,
        'value': '10.0',
        'value_type': 'float',
        'default_value': '10.0',
        'description': 'Maximum weekly loss limit',
        'unit': '%',
        'min_value': 3.0,
        'max_value': 50.0,
        'editable': True,
        'requires_restart': False,
    },
    {
        'key': 'max_correlated_positions',
        'category': SettingCategory.RISK_MANAGEMENT,
        'value': '2',
        'value_type': 'int',
        'default_value': '2',
        'description': 'Maximum positions in correlated pairs',
        'min_value': 1,
        'max_value': 10,
        'editable': True,
        'requires_restart': False,
    },

    # ==================== STRATEGY SETTINGS ====================
    {
        'key': 'enabled_strategies',
        'category': SettingCategory.STRATEGIES,
        'value': '["momentum_equilibrium", "london_session_breakout", "golden_fibonacci", "ath_retest", "order_block_retest"]',
        'value_type': 'json',
        'default_value': '["momentum_equilibrium", "london_session_breakout", "golden_fibonacci", "ath_retest", "order_block_retest"]',
        'description': 'List of enabled trading strategies',
        'editable': True,
        'requires_restart': True,
    },
    {
        'key': 'min_rr_ratio',
        'category': SettingCategory.STRATEGIES,
        'value': '1.5',
        'value_type': 'float',
        'default_value': '1.5',
        'description': 'Minimum risk:reward ratio for signals',
        'min_value': 1.0,
        'max_value': 5.0,
        'editable': True,
        'requires_restart': False,
    },
    {
        'key': 'min_confidence',
        'category': SettingCategory.STRATEGIES,
        'value': '0.6',
        'value_type': 'float',
        'default_value': '0.6',
        'description': 'Minimum confidence score for signals',
        'unit': '',
        'min_value': 0.0,
        'max_value': 1.0,
        'editable': True,
        'requires_restart': False,
    },
    {
        'key': 'duplicate_window_hours',
        'category': SettingCategory.STRATEGIES,
        'value': '4',
        'value_type': 'int',
        'default_value': '4',
        'description': 'Hours to check for duplicate signals',
        'unit': 'hours',
        'min_value': 1,
        'max_value': 24,
        'editable': True,
        'requires_restart': False,
    },

    # ==================== NOTIFICATION SETTINGS ====================
    {
        'key': 'telegram_enabled',
        'category': SettingCategory.NOTIFICATIONS,
        'value': 'false',
        'value_type': 'bool',
        'default_value': 'false',
        'description': 'Enable Telegram notifications for signals',
        'editable': True,
        'requires_restart': False,
    },
    {
        'key': 'email_enabled',
        'category': SettingCategory.NOTIFICATIONS,
        'value': 'false',
        'value_type': 'bool',
        'default_value': 'false',
        'description': 'Enable email notifications for signals',
        'editable': True,
        'requires_restart': False,
    },
    {
        'key': 'notify_on_signal',
        'category': SettingCategory.NOTIFICATIONS,
        'value': 'true',
        'value_type': 'bool',
        'default_value': 'true',
        'description': 'Send notification when signal is generated',
        'editable': True,
        'requires_restart': False,
    },
    {
        'key': 'notify_on_trade_open',
        'category': SettingCategory.NOTIFICATIONS,
        'value': 'true',
        'value_type': 'bool',
        'default_value': 'true',
        'description': 'Send notification when trade is opened',
        'editable': True,
        'requires_restart': False,
    },
    {
        'key': 'notify_on_trade_close',
        'category': SettingCategory.NOTIFICATIONS,
        'value': 'true',
        'value_type': 'bool',
        'default_value': 'true',
        'description': 'Send notification when trade is closed',
        'editable': True,
        'requires_restart': False,
    },

    # ==================== SYSTEM SETTINGS ====================
    {
        'key': 'service_status',
        'category': SettingCategory.SYSTEM,
        'value': 'running',
        'value_type': 'string',
        'default_value': 'running',
        'description': 'Service status (running/paused/stopped)',
        'editable': True,
        'requires_restart': False,
    },
    {
        'key': 'log_level',
        'category': SettingCategory.SYSTEM,
        'value': 'INFO',
        'value_type': 'string',
        'default_value': 'INFO',
        'description': 'Logging level (DEBUG/INFO/WARNING/ERROR)',
        'editable': True,
        'requires_restart': False,
    },
    {
        'key': 'data_feed_type',
        'category': SettingCategory.SYSTEM,
        'value': 'yahoo',
        'value_type': 'string',
        'default_value': 'yahoo',
        'description': 'Data feed provider (yahoo/mt5/metaapi)',
        'editable': True,
        'requires_restart': True,
    },
]

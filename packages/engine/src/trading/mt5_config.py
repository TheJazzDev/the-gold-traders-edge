"""MT5 Configuration Settings"""

import os
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class MT5ConnectionType(Enum):
    """MT5 connection type"""
    DIRECT = "direct"  # Direct MT5 terminal connection (Windows only)
    METAAPI = "metaapi"  # Cloud-based MetaAPI connection (cross-platform)


class PositionSizeMode(Enum):
    """Position sizing mode"""
    RISK_BASED = "risk_based"  # Calculate lots based on risk %
    FIXED_LOTS = "fixed_lots"  # Use fixed lot size


@dataclass
class MT5Config:
    """MT5 connection and trading configuration"""

    # Connection settings
    connection_type: MT5ConnectionType

    # Direct MT5 settings (Windows)
    mt5_login: Optional[int] = None
    mt5_password: Optional[str] = None
    mt5_server: Optional[str] = None

    # MetaAPI settings (Cloud)
    metaapi_token: Optional[str] = None
    metaapi_account_id: Optional[str] = None

    # Trading symbol
    symbol: str = "XAUUSD"

    # Risk management
    max_risk_per_trade: float = 0.02  # 2%
    max_positions: int = 3
    max_daily_loss: float = 0.05  # 5%
    position_size_mode: PositionSizeMode = PositionSizeMode.RISK_BASED
    fixed_lot_size: float = 0.01  # Used when position_size_mode = FIXED_LOTS

    # Slippage and execution
    max_slippage_pips: int = 5
    magic_number: int = 123456  # Unique identifier for our EA

    # Connection health
    reconnect_attempts: int = 5
    reconnect_delay_seconds: int = 5
    heartbeat_interval_seconds: int = 60

    @classmethod
    def from_env(cls) -> "MT5Config":
        """Load configuration from environment variables"""

        # Determine connection type
        connection_type_str = os.getenv("MT5_CONNECTION_TYPE", "direct").lower()
        connection_type = MT5ConnectionType(connection_type_str)

        # Position size mode
        position_mode_str = os.getenv("POSITION_SIZE_MODE", "risk_based").lower()
        position_size_mode = PositionSizeMode(position_mode_str)

        return cls(
            connection_type=connection_type,

            # Direct MT5
            mt5_login=int(os.getenv("MT5_LOGIN")) if os.getenv("MT5_LOGIN") else None,
            mt5_password=os.getenv("MT5_PASSWORD"),
            mt5_server=os.getenv("MT5_SERVER"),

            # MetaAPI
            metaapi_token=os.getenv("METAAPI_TOKEN"),
            metaapi_account_id=os.getenv("METAAPI_ACCOUNT_ID"),

            # Symbol
            symbol=os.getenv("MT5_SYMBOL", "XAUUSD"),

            # Risk management
            max_risk_per_trade=float(os.getenv("MAX_RISK_PER_TRADE", "0.02")),
            max_positions=int(os.getenv("MAX_POSITIONS", "3")),
            max_daily_loss=float(os.getenv("MAX_DAILY_LOSS", "0.05")),
            position_size_mode=position_size_mode,
            fixed_lot_size=float(os.getenv("FIXED_LOT_SIZE", "0.01")),

            # Execution
            max_slippage_pips=int(os.getenv("MAX_SLIPPAGE_PIPS", "5")),
            magic_number=int(os.getenv("MAGIC_NUMBER", "123456")),

            # Connection
            reconnect_attempts=int(os.getenv("RECONNECT_ATTEMPTS", "5")),
            reconnect_delay_seconds=int(os.getenv("RECONNECT_DELAY", "5")),
            heartbeat_interval_seconds=int(os.getenv("HEARTBEAT_INTERVAL", "60")),
        )

    def validate(self) -> bool:
        """Validate configuration"""
        if self.connection_type == MT5ConnectionType.DIRECT:
            if not all([self.mt5_login, self.mt5_password, self.mt5_server]):
                raise ValueError(
                    "Direct MT5 connection requires MT5_LOGIN, MT5_PASSWORD, and MT5_SERVER"
                )

        elif self.connection_type == MT5ConnectionType.METAAPI:
            if not all([self.metaapi_token, self.metaapi_account_id]):
                raise ValueError(
                    "MetaAPI connection requires METAAPI_TOKEN and METAAPI_ACCOUNT_ID"
                )

        # Validate risk parameters
        if not 0 < self.max_risk_per_trade <= 0.1:  # Max 10%
            raise ValueError("max_risk_per_trade must be between 0 and 0.1 (10%)")

        if not 0 < self.max_daily_loss <= 0.2:  # Max 20%
            raise ValueError("max_daily_loss must be between 0 and 0.2 (20%)")

        if self.max_positions < 1:
            raise ValueError("max_positions must be at least 1")

        return True

    def __repr__(self) -> str:
        """String representation (hide sensitive data)"""
        return (
            f"MT5Config(\n"
            f"  connection_type={self.connection_type.value},\n"
            f"  symbol={self.symbol},\n"
            f"  max_risk_per_trade={self.max_risk_per_trade*100}%,\n"
            f"  max_positions={self.max_positions},\n"
            f"  max_daily_loss={self.max_daily_loss*100}%,\n"
            f"  position_size_mode={self.position_size_mode.value}\n"
            f")"
        )

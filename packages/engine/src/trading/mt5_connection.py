"""
MT5 Connection Manager
Handles connection to MetaTrader 5 terminal (direct or via MetaAPI cloud)
"""

import logging
import threading
import time
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from datetime import datetime
from .mt5_config import MT5Config, MT5ConnectionType

logger = logging.getLogger(__name__)

# One broker connection per account, shared by every worker.
_metaapi_connections: Dict[str, 'MT5ConnectionBase'] = {}
_metaapi_lock = threading.Lock()


class MT5ConnectionBase(ABC):
    """Base class for MT5 connections"""

    def __init__(self, config: MT5Config):
        self.config = config
        self.connected = False
        self.last_heartbeat = None
        self.connection_attempts = 0

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to MT5"""
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """Close connection to MT5"""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connected"""
        pass

    @abstractmethod
    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """Get account information"""
        pass

    def open_position_tickets(self) -> Optional[List[int]]:
        """Open positions at the broker; None where that can't be read."""
        return None

    @abstractmethod
    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get symbol information"""
        pass

    def reconnect(self) -> bool:
        """Attempt to reconnect with exponential backoff"""
        logger.info("Attempting to reconnect to MT5...")

        for attempt in range(self.config.reconnect_attempts):
            self.connection_attempts += 1
            delay = self.config.reconnect_delay_seconds * (2 ** attempt)  # Exponential backoff

            logger.info(f"Reconnection attempt {attempt + 1}/{self.config.reconnect_attempts}")

            if self.connect():
                logger.info("Reconnection successful!")
                self.connection_attempts = 0
                return True

            if attempt < self.config.reconnect_attempts - 1:
                logger.warning(f"Reconnection failed. Retrying in {delay} seconds...")
                time.sleep(delay)

        logger.error(f"Failed to reconnect after {self.config.reconnect_attempts} attempts")
        return False

    def heartbeat(self) -> bool:
        """Send heartbeat to check connection health"""
        if not self.is_connected():
            logger.warning("Heartbeat failed: Not connected")
            return False

        self.last_heartbeat = datetime.now()
        logger.debug("Heartbeat successful")
        return True


class DirectMT5Connection(MT5ConnectionBase):
    """Direct connection to MT5 terminal (Windows only)"""

    def __init__(self, config: MT5Config):
        super().__init__(config)
        self.mt5 = None

    def connect(self) -> bool:
        """Connect to MT5 terminal"""
        try:
            import MetaTrader5 as mt5
            self.mt5 = mt5

            logger.info("Initializing MT5 terminal...")

            if not mt5.initialize():
                error = mt5.last_error()
                logger.error(f"MT5 initialization failed: {error}")
                return False

            logger.info(f"Logging in to MT5 account {self.config.mt5_login}...")

            if not mt5.login(
                login=self.config.mt5_login,
                password=self.config.mt5_password,
                server=self.config.mt5_server
            ):
                error = mt5.last_error()
                logger.error(f"MT5 login failed: {error}")
                mt5.shutdown()
                return False

            self.connected = True
            self.last_heartbeat = datetime.now()

            # Get account info
            account_info = mt5.account_info()
            if account_info:
                logger.info(f"Connected to MT5 account: {account_info.login}")
                logger.info(f"Account balance: ${account_info.balance:.2f}")
                logger.info(f"Account leverage: 1:{account_info.leverage}")
            else:
                logger.warning("Could not retrieve account info")

            return True

        except ImportError:
            logger.error(
                "MetaTrader5 package not installed. "
                "Install with: pip install MetaTrader5"
            )
            return False
        except Exception as e:
            logger.error(f"Error connecting to MT5: {e}")
            return False

    def disconnect(self) -> bool:
        """Disconnect from MT5 terminal"""
        try:
            if self.mt5:
                self.mt5.shutdown()
                self.connected = False
                logger.info("Disconnected from MT5")
                return True
            return False
        except Exception as e:
            logger.error(f"Error disconnecting from MT5: {e}")
            return False

    def is_connected(self) -> bool:
        """Check if connected to MT5"""
        if not self.mt5 or not self.connected:
            return False

        # Check terminal info to verify connection
        try:
            terminal_info = self.mt5.terminal_info()
            return terminal_info is not None
        except:
            return False

    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """Get account information"""
        if not self.is_connected():
            return None

        try:
            account_info = self.mt5.account_info()
            if not account_info:
                return None

            return {
                "login": account_info.login,
                "balance": account_info.balance,
                "equity": account_info.equity,
                "margin": account_info.margin,
                "free_margin": account_info.margin_free,
                "margin_level": account_info.margin_level if account_info.margin > 0 else 0,
                "leverage": account_info.leverage,
                "profit": account_info.profit,
                "currency": account_info.currency,
            }
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return None

    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get symbol information"""
        if not self.is_connected():
            return None

        try:
            symbol_info = self.mt5.symbol_info(symbol)
            if not symbol_info:
                logger.error(f"Symbol {symbol} not found")
                return None

            return {
                "name": symbol_info.name,
                "bid": symbol_info.bid,
                "ask": symbol_info.ask,
                "digits": symbol_info.digits,
                "point": symbol_info.point,
                "trade_contract_size": symbol_info.trade_contract_size,
                "volume_min": symbol_info.volume_min,
                "volume_max": symbol_info.volume_max,
                "volume_step": symbol_info.volume_step,
            }
        except Exception as e:
            logger.error(f"Error getting symbol info: {e}")
            return None


def create_mt5_connection(config: MT5Config) -> MT5ConnectionBase:
    """
    Factory function to create appropriate MT5 connection based on config

    Args:
        config: MT5 configuration

    Returns:
        MT5ConnectionBase: Either DirectMT5Connection or MetaAPIConnection
    """
    config.validate()

    if config.connection_type == MT5ConnectionType.DIRECT:
        logger.info("Creating direct MT5 connection (Windows)")
        return DirectMT5Connection(config)
    elif config.connection_type == MT5ConnectionType.METAAPI:
        logger.info("Creating MetaAPI cloud connection (cross-platform)")
        from .metaapi_connection import MetaAPIConnection
        with _metaapi_lock:
            key = config.metaapi_account_id
            if key not in _metaapi_connections:
                _metaapi_connections[key] = MetaAPIConnection(config)
            return _metaapi_connections[key]
    else:
        raise ValueError(f"Unknown connection type: {config.connection_type}")

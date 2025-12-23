"""
MT5 Connection Manager
Handles connection to MetaTrader 5 terminal (direct or via MetaAPI cloud)
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from datetime import datetime
from .mt5_config import MT5Config, MT5ConnectionType

logger = logging.getLogger(__name__)


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


class MetaAPIConnection(MT5ConnectionBase):
    """Cloud-based MT5 connection via MetaAPI (cross-platform)"""

    def __init__(self, config: MT5Config):
        super().__init__(config)
        self.api = None
        self.account = None
        self.connection = None

    def connect(self) -> bool:
        """Connect to MT5 via MetaAPI cloud (synchronous wrapper)"""
        import asyncio

        try:
            # Create event loop if none exists
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Run async connection
            return loop.run_until_complete(self._async_connect())

        except Exception as e:
            logger.error(f"Error in connect: {e}")
            return False

    async def _async_connect(self) -> bool:
        """Async connection to MetaAPI"""
        try:
            from metaapi_cloud_sdk import MetaApi

            logger.info("Initializing MetaAPI connection...")

            self.api = MetaApi(self.config.metaapi_token)
            self.account = await self.api.metatrader_account_api.get_account(
                self.config.metaapi_account_id
            )

            logger.info(f"Deploying account {self.config.metaapi_account_id}...")
            await self.account.deploy()

            logger.info("Waiting for API server to connect...")
            await self.account.wait_connected()

            logger.info("Connecting to MetaAPI RPC...")
            self.connection = self.account.get_rpc_connection()
            await self.connection.connect()
            await self.connection.wait_synchronized()

            self.connected = True
            self.last_heartbeat = datetime.now()

            # Get account info
            account_info = await self.connection.get_account_information()
            logger.info(f"Connected to MetaAPI account: {account_info['login']}")
            logger.info(f"Account balance: ${account_info['balance']:.2f}")
            logger.info(f"Account leverage: 1:{account_info['leverage']}")

            return True

        except ImportError:
            logger.error(
                "MetaAPI SDK not installed. "
                "Install with: pip install metaapi-cloud-sdk"
            )
            return False
        except Exception as e:
            logger.error(f"Error connecting to MetaAPI: {e}")
            return False

    def disconnect(self) -> bool:
        """Disconnect from MetaAPI"""
        try:
            if self.connection:
                self.connection.close()
            self.connected = False
            logger.info("Disconnected from MetaAPI")
            return True
        except Exception as e:
            logger.error(f"Error disconnecting from MetaAPI: {e}")
            return False

    def is_connected(self) -> bool:
        """Check if connected to MetaAPI"""
        if not self.connection or not self.connected:
            return False

        try:
            # Try to get account info to verify connection
            self.connection.get_account_information()
            return True
        except:
            return False

    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """Get account information from MetaAPI (synchronous wrapper)"""
        import asyncio

        if not self.is_connected():
            return None

        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self._async_get_account_info())
        except Exception as e:
            logger.error(f"Error in get_account_info: {e}")
            return None

    async def _async_get_account_info(self) -> Optional[Dict[str, Any]]:
        """Async get account information"""
        try:
            account_info = await self.connection.get_account_information()
            return {
                "login": account_info.get("login"),
                "balance": account_info.get("balance"),
                "equity": account_info.get("equity"),
                "margin": account_info.get("margin"),
                "free_margin": account_info.get("freeMargin"),
                "margin_level": account_info.get("marginLevel", 0),
                "leverage": account_info.get("leverage"),
                "profit": account_info.get("profit"),
                "currency": account_info.get("currency"),
            }
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return None

    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get symbol information from MetaAPI (synchronous wrapper)"""
        import asyncio

        if not self.is_connected():
            return None

        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self._async_get_symbol_info(symbol))
        except Exception as e:
            logger.error(f"Error in get_symbol_info: {e}")
            return None

    async def _async_get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Async get symbol information"""
        try:
            symbol_spec = await self.connection.get_symbol_specification(symbol)
            symbol_price = await self.connection.get_symbol_price(symbol)

            return {
                "name": symbol,
                "bid": symbol_price.get("bid"),
                "ask": symbol_price.get("ask"),
                "digits": symbol_spec.get("digits"),
                "point": 10 ** (-symbol_spec.get("digits")),
                "trade_contract_size": symbol_spec.get("contractSize"),
                "volume_min": symbol_spec.get("minVolume"),
                "volume_max": symbol_spec.get("maxVolume"),
                "volume_step": symbol_spec.get("volumeStep"),
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
        return MetaAPIConnection(config)
    else:
        raise ValueError(f"Unknown connection type: {config.connection_type}")

"""
MT5 through MetaAPI's cloud, the connection that runs on Linux.

All SDK calls go through one running event loop (see async_bridge.py), and
every worker in the process shares one instance.
"""
import logging
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

from .async_bridge import shared_bridge
from .mt5_config import MT5Config
from .mt5_connection import MT5ConnectionBase

logger = logging.getLogger(__name__)


class MetaAPIConnection(MT5ConnectionBase):
    def __init__(self, config: MT5Config):
        super().__init__(config)
        self.api = None
        self.account = None
        self.connection = None
        self._connect_lock = threading.Lock()

    def _broker_symbol(self, symbol: str) -> str:
        return symbol + self.config.symbol_suffix

    def connect(self) -> bool:
        with self._connect_lock:
            if self.connected:
                return True
            try:
                return shared_bridge().run(self._async_connect(), timeout=300)
            except Exception as e:
                logger.error(f"Error connecting to MetaAPI: {e}")
                return False

    async def _async_connect(self) -> bool:
        from metaapi_cloud_sdk import MetaApi

        self.api = MetaApi(self.config.metaapi_token)
        self.account = await self.api.metatrader_account_api.get_account(self.config.metaapi_account_id)
        await self.account.deploy()
        await self.account.wait_connected()
        self.connection = self.account.get_rpc_connection()
        await self.connection.connect()
        await self.connection.wait_synchronized()

        self.connected = True
        self.last_heartbeat = datetime.now()
        info = await self.connection.get_account_information()
        logger.info(f"Connected to MetaAPI: balance {info['balance']:.2f}, leverage 1:{info['leverage']}")
        return True

    def disconnect(self) -> bool:
        try:
            if self.connection:
                shared_bridge().run(self.connection.close())
            self.connected = False
            return True
        except Exception as e:
            logger.error(f"Error disconnecting from MetaAPI: {e}")
            return False

    def is_connected(self) -> bool:
        if not self.connection or not self.connected:
            return False
        try:
            shared_bridge().run(self.connection.get_account_information(), timeout=30)
            return True
        except Exception as e:
            logger.error(f"MetaAPI connection check failed: {e}")
            return False

    def get_account_info(self) -> Optional[Dict[str, Any]]:
        try:
            info = shared_bridge().run(self.connection.get_account_information())
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return None
        return {
            "login": info.get("login"),
            "balance": info.get("balance"),
            "equity": info.get("equity"),
            "margin": info.get("margin"),
            "free_margin": info.get("freeMargin"),
            "margin_level": info.get("marginLevel", 0),
            "leverage": info.get("leverage"),
            "profit": info.get("profit"),
            "currency": info.get("currency"),
        }

    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        name = self._broker_symbol(symbol)
        try:
            spec = shared_bridge().run(self.connection.get_symbol_specification(name))
            price = shared_bridge().run(self.connection.get_symbol_price(name))
        except Exception as e:
            logger.error(f"Error getting symbol info for {name}: {e}")
            return None
        return {
            "name": name,
            "bid": price.get("bid"),
            "ask": price.get("ask"),
            "digits": spec.get("digits"),
            "point": 10 ** (-spec.get("digits")),
            "trade_contract_size": spec.get("contractSize"),
            "volume_min": spec.get("minVolume"),
            "volume_max": spec.get("maxVolume"),
            "volume_step": spec.get("volumeStep"),
        }

    def market_order(self, symbol: str, direction: str, volume: float, stop_loss: float,
                     take_profit: float) -> Dict[str, Any]:
        """Open a position. Raises on a broker rejection."""
        name = self._broker_symbol(symbol)
        options = {"comment": "GoldTrader", "magic": self.config.magic_number}
        send = (self.connection.create_market_buy_order if direction == "LONG"
                else self.connection.create_market_sell_order)
        result = shared_bridge().run(send(name, volume, stop_loss, take_profit, options))
        ticket = result["positionId"]
        position = shared_bridge().run(self.connection.get_position(ticket))
        return {"ticket": int(ticket), "entry_price": position.get("openPrice")}

    def open_position_tickets(self) -> Optional[List[int]]:
        """This bot's open positions; None if the broker can't be read."""
        try:
            positions = shared_bridge().run(self.connection.get_positions())
        except Exception as e:
            logger.error(f"Error reading positions: {e}")
            return None
        return [int(p["id"]) for p in positions if str(p.get("magic")) == str(self.config.magic_number)]

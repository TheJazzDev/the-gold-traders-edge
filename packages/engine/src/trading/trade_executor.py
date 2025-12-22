"""
Trade Executor
Handles order placement and execution on MT5
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

from .mt5_connection import MT5ConnectionBase, DirectMT5Connection, MetaAPIConnection
from .position_calculator import PositionCalculator
from .mt5_config import MT5Config

logger = logging.getLogger(__name__)


class OrderType(Enum):
    """Order type"""
    BUY = "BUY"
    SELL = "SELL"


class TradeResult:
    """Result of trade execution"""

    def __init__(
        self,
        success: bool,
        ticket: Optional[int] = None,
        entry_price: Optional[float] = None,
        lot_size: Optional[float] = None,
        error_message: Optional[str] = None,
        order_details: Optional[Dict[str, Any]] = None
    ):
        self.success = success
        self.ticket = ticket
        self.entry_price = entry_price
        self.lot_size = lot_size
        self.error_message = error_message
        self.order_details = order_details or {}
        self.timestamp = datetime.now()

    def __repr__(self) -> str:
        if self.success:
            return (
                f"TradeResult(success=True, ticket={self.ticket}, "
                f"entry={self.entry_price}, lots={self.lot_size})"
            )
        else:
            return f"TradeResult(success=False, error='{self.error_message}')"


class TradeExecutor:
    """Execute trades on MT5"""

    def __init__(
        self,
        connection: MT5ConnectionBase,
        config: MT5Config,
        position_calculator: PositionCalculator
    ):
        self.connection = connection
        self.config = config
        self.calculator = position_calculator

    def execute_signal(
        self,
        signal: Dict[str, Any],
        account_balance: float
    ) -> TradeResult:
        """
        Execute a trading signal

        Args:
            signal: Signal dict with entry, stop_loss, take_profit, direction, etc.
            account_balance: Current account balance

        Returns:
            TradeResult: Result of trade execution
        """
        symbol = signal.get("symbol", self.config.symbol)
        direction = signal["direction"]  # "LONG" or "SHORT"
        entry_price = signal["entry_price"]
        stop_loss = signal["stop_loss"]
        take_profit = signal["take_profit"]

        logger.info(
            f"Executing {direction} signal for {symbol}:\n"
            f"  Entry: {entry_price}\n"
            f"  Stop Loss: {stop_loss}\n"
            f"  Take Profit: {take_profit}"
        )

        # Get symbol info
        symbol_info = self.connection.get_symbol_info(symbol)
        if not symbol_info:
            return TradeResult(
                success=False,
                error_message=f"Could not get symbol info for {symbol}"
            )

        # Calculate lot size
        lot_size = self.calculator.calculate_lot_size(
            account_balance=account_balance,
            entry_price=entry_price,
            stop_loss=stop_loss,
            symbol_info=symbol_info
        )

        if lot_size <= 0:
            return TradeResult(
                success=False,
                error_message="Calculated lot size is zero or negative"
            )

        # Validate position size
        account_info = self.connection.get_account_info()
        if not account_info:
            return TradeResult(
                success=False,
                error_message="Could not get account info"
            )

        is_valid, error_msg = self.calculator.validate_position_size(
            lot_size=lot_size,
            account_balance=account_balance,
            account_leverage=account_info["leverage"],
            symbol_info=symbol_info,
            entry_price=entry_price
        )

        if not is_valid:
            return TradeResult(success=False, error_message=error_msg)

        # Execute order based on connection type
        if isinstance(self.connection, DirectMT5Connection):
            return self._execute_direct_mt5(
                symbol=symbol,
                direction=direction,
                lot_size=lot_size,
                stop_loss=stop_loss,
                take_profit=take_profit,
                symbol_info=symbol_info
            )
        elif isinstance(self.connection, MetaAPIConnection):
            return self._execute_metaapi(
                symbol=symbol,
                direction=direction,
                lot_size=lot_size,
                stop_loss=stop_loss,
                take_profit=take_profit
            )
        else:
            return TradeResult(
                success=False,
                error_message="Unknown connection type"
            )

    def _execute_direct_mt5(
        self,
        symbol: str,
        direction: str,
        lot_size: float,
        stop_loss: float,
        take_profit: float,
        symbol_info: dict
    ) -> TradeResult:
        """Execute trade via direct MT5 connection"""
        try:
            mt5 = self.connection.mt5

            # Determine order type
            order_type = mt5.ORDER_TYPE_BUY if direction == "LONG" else mt5.ORDER_TYPE_SELL

            # Get current price
            if direction == "LONG":
                price = symbol_info["ask"]
            else:
                price = symbol_info["bid"]

            # Prepare request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": lot_size,
                "type": order_type,
                "price": price,
                "sl": stop_loss,
                "tp": take_profit,
                "deviation": self.config.max_slippage_pips,
                "magic": self.config.magic_number,
                "comment": "GoldTrader Signal",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            logger.info(f"Sending order to MT5: {request}")

            # Send order
            result = mt5.order_send(request)

            if result is None:
                return TradeResult(
                    success=False,
                    error_message="Order send returned None"
                )

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                error_msg = f"Order failed: {result.retcode} - {result.comment}"
                logger.error(error_msg)
                return TradeResult(
                    success=False,
                    error_message=error_msg,
                    order_details=result._asdict() if hasattr(result, '_asdict') else {}
                )

            logger.info(
                f"Order executed successfully!\n"
                f"  Ticket: {result.order}\n"
                f"  Price: {result.price}\n"
                f"  Volume: {result.volume}\n"
                f"  Comment: {result.comment}"
            )

            return TradeResult(
                success=True,
                ticket=result.order,
                entry_price=result.price,
                lot_size=result.volume,
                order_details=result._asdict() if hasattr(result, '_asdict') else {}
            )

        except Exception as e:
            logger.error(f"Error executing direct MT5 order: {e}")
            return TradeResult(
                success=False,
                error_message=str(e)
            )

    def _execute_metaapi(
        self,
        symbol: str,
        direction: str,
        lot_size: float,
        stop_loss: float,
        take_profit: float
    ) -> TradeResult:
        """Execute trade via MetaAPI cloud connection"""
        try:
            connection = self.connection.connection

            # Prepare trade request
            trade_request = {
                "actionType": "ORDER_TYPE_BUY" if direction == "LONG" else "ORDER_TYPE_SELL",
                "symbol": symbol,
                "volume": lot_size,
                "stopLoss": stop_loss,
                "takeProfit": take_profit,
                "comment": "GoldTrader Signal"
            }

            logger.info(f"Sending order to MetaAPI: {trade_request}")

            # Execute trade
            result = connection.create_market_buy_order(**trade_request) \
                if direction == "LONG" \
                else connection.create_market_sell_order(**trade_request)

            logger.info(
                f"Order executed successfully via MetaAPI!\n"
                f"  Order ID: {result.get('orderId')}\n"
                f"  Position ID: {result.get('positionId')}"
            )

            return TradeResult(
                success=True,
                ticket=result.get("positionId"),  # MetaAPI uses position ID
                entry_price=result.get("price"),
                lot_size=lot_size,
                order_details=result
            )

        except Exception as e:
            logger.error(f"Error executing MetaAPI order: {e}")
            return TradeResult(
                success=False,
                error_message=str(e)
            )

    def close_position(
        self,
        ticket: int,
        reason: str = "manual"
    ) -> TradeResult:
        """
        Close an open position

        Args:
            ticket: Position ticket/ID
            reason: Reason for closure (manual, tp, sl, etc.)

        Returns:
            TradeResult: Result of close operation
        """
        logger.info(f"Closing position {ticket} (reason: {reason})")

        if isinstance(self.connection, DirectMT5Connection):
            return self._close_direct_mt5(ticket)
        elif isinstance(self.connection, MetaAPIConnection):
            return self._close_metaapi(ticket)
        else:
            return TradeResult(
                success=False,
                error_message="Unknown connection type"
            )

    def _close_direct_mt5(self, ticket: int) -> TradeResult:
        """Close position via direct MT5"""
        try:
            mt5 = self.connection.mt5

            # Get position info
            position = mt5.positions_get(ticket=ticket)
            if not position:
                return TradeResult(
                    success=False,
                    error_message=f"Position {ticket} not found"
                )

            position = position[0]

            # Determine close order type (opposite of opening)
            close_type = mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY

            # Get close price
            symbol_info = self.connection.get_symbol_info(position.symbol)
            close_price = symbol_info["bid"] if close_type == mt5.ORDER_TYPE_SELL else symbol_info["ask"]

            # Prepare close request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": position.symbol,
                "volume": position.volume,
                "type": close_type,
                "position": ticket,
                "price": close_price,
                "deviation": self.config.max_slippage_pips,
                "magic": self.config.magic_number,
                "comment": "GoldTrader Close",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            # Send close order
            result = mt5.order_send(request)

            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"Position {ticket} closed successfully at {result.price}")
                return TradeResult(
                    success=True,
                    ticket=ticket,
                    entry_price=result.price,
                    order_details=result._asdict() if hasattr(result, '_asdict') else {}
                )
            else:
                error_msg = f"Failed to close position: {result.comment if result else 'Unknown error'}"
                return TradeResult(success=False, error_message=error_msg)

        except Exception as e:
            logger.error(f"Error closing MT5 position: {e}")
            return TradeResult(success=False, error_message=str(e))

    def _close_metaapi(self, position_id: str) -> TradeResult:
        """Close position via MetaAPI"""
        try:
            connection = self.connection.connection
            result = connection.close_position(position_id)

            logger.info(f"Position {position_id} closed successfully via MetaAPI")
            return TradeResult(
                success=True,
                ticket=position_id,
                order_details=result
            )

        except Exception as e:
            logger.error(f"Error closing MetaAPI position: {e}")
            return TradeResult(success=False, error_message=str(e))

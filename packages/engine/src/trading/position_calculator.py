"""
Position Size Calculator
Calculates lot size based on risk percentage and account balance
"""

import logging
from typing import Optional
from .mt5_config import MT5Config, PositionSizeMode

logger = logging.getLogger(__name__)


class PositionCalculator:
    """Calculate position size based on risk management rules"""

    def __init__(self, config: MT5Config):
        self.config = config

    def calculate_lot_size(
        self,
        account_balance: float,
        entry_price: float,
        stop_loss: float,
        symbol_info: dict,
        risk_percentage: Optional[float] = None
    ) -> float:
        """
        Calculate lot size based on risk parameters

        Args:
            account_balance: Account balance in account currency
            entry_price: Entry price for the trade
            stop_loss: Stop loss price
            symbol_info: Symbol information from MT5 (digits, point, contract_size, etc.)
            risk_percentage: Risk percentage (overrides config if provided)

        Returns:
            float: Lot size rounded to symbol's volume step
        """
        # Use fixed lots if configured
        if self.config.position_size_mode == PositionSizeMode.FIXED_LOTS:
            logger.info(f"Using fixed lot size: {self.config.fixed_lot_size}")
            return self.config.fixed_lot_size

        # Calculate risk-based position size
        risk_pct = risk_percentage or self.config.max_risk_per_trade
        risk_amount = account_balance * risk_pct

        # Calculate pip/point difference between entry and stop loss
        pip_value = symbol_info["point"]
        digits = symbol_info["digits"]
        contract_size = symbol_info["trade_contract_size"]

        # Calculate stop loss distance in price
        sl_distance = abs(entry_price - stop_loss)

        # Calculate stop loss distance in pips
        sl_pips = sl_distance / pip_value

        # Calculate pip value per lot
        # For XAUUSD: 1 pip = 0.01, contract size = 100
        # Pip value = (pip size * contract size)
        pip_value_per_lot = pip_value * contract_size

        # Calculate lot size
        # risk_amount = lot_size * sl_pips * pip_value_per_lot
        # lot_size = risk_amount / (sl_pips * pip_value_per_lot)
        if sl_pips == 0:
            logger.error("Stop loss distance is zero, cannot calculate position size")
            return 0.0

        lot_size = risk_amount / (sl_pips * pip_value_per_lot)

        # Round to symbol's volume step
        volume_step = symbol_info["volume_step"]
        lot_size = round(lot_size / volume_step) * volume_step

        # Ensure within min/max volume
        volume_min = symbol_info["volume_min"]
        volume_max = symbol_info["volume_max"]
        lot_size = max(volume_min, min(lot_size, volume_max))

        logger.info(
            f"Position size calculation:\n"
            f"  Account balance: ${account_balance:.2f}\n"
            f"  Risk amount: ${risk_amount:.2f} ({risk_pct*100}%)\n"
            f"  Entry: {entry_price}\n"
            f"  Stop loss: {stop_loss}\n"
            f"  SL distance: {sl_distance:.{digits}f} ({sl_pips:.1f} pips)\n"
            f"  Pip value per lot: ${pip_value_per_lot:.2f}\n"
            f"  Calculated lot size: {lot_size:.2f}\n"
            f"  Min/Max lots: {volume_min}/{volume_max}"
        )

        return lot_size

    def calculate_risk_amount(
        self,
        lot_size: float,
        entry_price: float,
        stop_loss: float,
        symbol_info: dict
    ) -> float:
        """
        Calculate the risk amount for a given lot size

        Args:
            lot_size: Position size in lots
            entry_price: Entry price
            stop_loss: Stop loss price
            symbol_info: Symbol information

        Returns:
            float: Risk amount in account currency
        """
        pip_value = symbol_info["point"]
        contract_size = symbol_info["trade_contract_size"]

        sl_distance = abs(entry_price - stop_loss)
        sl_pips = sl_distance / pip_value
        pip_value_per_lot = pip_value * contract_size

        risk_amount = lot_size * sl_pips * pip_value_per_lot

        return risk_amount

    def calculate_position_value(
        self,
        lot_size: float,
        price: float,
        symbol_info: dict
    ) -> float:
        """
        Calculate the total position value

        Args:
            lot_size: Position size in lots
            price: Current price
            symbol_info: Symbol information

        Returns:
            float: Position value in account currency
        """
        contract_size = symbol_info["trade_contract_size"]
        position_value = lot_size * contract_size * price
        return position_value

    def validate_position_size(
        self,
        lot_size: float,
        account_balance: float,
        account_leverage: int,
        symbol_info: dict,
        entry_price: float
    ) -> tuple[bool, Optional[str]]:
        """
        Validate if position size is acceptable

        Args:
            lot_size: Proposed lot size
            account_balance: Account balance
            account_leverage: Account leverage
            symbol_info: Symbol information
            entry_price: Entry price

        Returns:
            tuple: (is_valid, error_message)
        """
        # Check against min/max volume
        if lot_size < symbol_info["volume_min"]:
            return False, f"Lot size {lot_size} below minimum {symbol_info['volume_min']}"

        if lot_size > symbol_info["volume_max"]:
            return False, f"Lot size {lot_size} above maximum {symbol_info['volume_max']}"

        # Check if lot size is multiple of volume step
        volume_step = symbol_info["volume_step"]
        if lot_size % volume_step != 0:
            return False, f"Lot size must be multiple of {volume_step}"

        # Check margin requirement
        contract_size = symbol_info["trade_contract_size"]
        position_value = lot_size * contract_size * entry_price
        required_margin = position_value / account_leverage

        if required_margin > account_balance * 0.5:  # Don't use more than 50% margin
            return False, f"Position requires too much margin: ${required_margin:.2f}"

        logger.info(
            f"Position validation:\n"
            f"  Lot size: {lot_size}\n"
            f"  Position value: ${position_value:.2f}\n"
            f"  Required margin: ${required_margin:.2f}\n"
            f"  Available balance: ${account_balance:.2f}\n"
            f"  Margin usage: {(required_margin/account_balance)*100:.1f}%"
        )

        return True, None

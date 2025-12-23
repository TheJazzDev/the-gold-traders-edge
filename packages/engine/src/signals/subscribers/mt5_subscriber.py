"""
MT5 Trade Execution Subscriber
Automatically executes trades when signals are generated
"""

import logging
import sys
from pathlib import Path
from typing import Optional

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database.connection import DatabaseManager
from database.signal_repository import SignalRepository
from database.models import SignalStatus

from trading.mt5_connection import MT5ConnectionBase
from trading.trade_executor import TradeExecutor
from trading.risk_manager import RiskManager
from trading.position_calculator import PositionCalculator
from trading.mt5_config import MT5Config

logger = logging.getLogger(__name__)


class MT5Subscriber:
    """
    Subscriber that executes trades on MT5 when signals are generated

    This integrates with the signal generator's pub/sub system to automatically
    execute trades based on validated signals.
    """

    def __init__(
        self,
        connection: MT5ConnectionBase,
        config: MT5Config,
        db_manager: DatabaseManager,
        risk_manager: RiskManager,
        dry_run: bool = False
    ):
        """
        Initialize MT5 subscriber

        Args:
            connection: MT5 connection instance
            config: MT5 configuration
            db_manager: Database manager
            risk_manager: Risk manager instance
            dry_run: If True, log trades but don't execute them (for testing)
        """
        self.connection = connection
        self.config = config
        self.db_manager = db_manager
        self.risk_manager = risk_manager
        self.dry_run = dry_run

        # Initialize components
        self.position_calculator = PositionCalculator(config)
        self.trade_executor = TradeExecutor(connection, config, self.position_calculator)
        self.signal_repo = SignalRepository(db_manager)

        # Statistics
        self.signals_received = 0
        self.signals_executed = 0
        self.signals_rejected = 0

        logger.info(
            f"MT5Subscriber initialized (dry_run={dry_run})\n"
            f"  Connection type: {config.connection_type.value}\n"
            f"  Max risk per trade: {config.max_risk_per_trade*100}%\n"
            f"  Max positions: {config.max_positions}\n"
            f"  Max daily loss: {config.max_daily_loss*100}%"
        )

    def __call__(self, signal: 'ValidatedSignal'):
        """
        Called when a new signal is generated

        Args:
            signal: ValidatedSignal instance from the signal generator
        """
        self.signals_received += 1

        logger.info(
            f"\n{'='*70}\n"
            f"📊 NEW TRADING SIGNAL RECEIVED (#{self.signals_received})\n"
            f"{'='*70}\n"
            f"{signal}\n"
            f"{'='*70}"
        )

        try:
            # Execute the signal
            success = self._execute_signal(signal)

            if success:
                self.signals_executed += 1
                logger.info(
                    f"✅ Signal executed successfully "
                    f"({self.signals_executed}/{self.signals_received})"
                )
            else:
                self.signals_rejected += 1
                logger.warning(
                    f"❌ Signal rejected "
                    f"({self.signals_rejected}/{self.signals_received})"
                )

        except Exception as e:
            self.signals_rejected += 1
            logger.error(f"Error executing signal: {e}", exc_info=True)

    def _execute_signal(self, signal: 'ValidatedSignal') -> bool:
        """
        Execute a validated signal

        Args:
            signal: ValidatedSignal instance

        Returns:
            bool: True if executed successfully
        """
        # Check if connection is alive
        if not self.connection.is_connected():
            logger.error("MT5 connection is not active")
            return False

        # Get account info
        account_info = self.connection.get_account_info()
        if not account_info:
            logger.error("Could not retrieve account information")
            return False

        account_balance = account_info["balance"]
        account_equity = account_info["equity"]

        logger.info(
            f"Account status:\n"
            f"  Balance: ${account_balance:.2f}\n"
            f"  Equity: ${account_equity:.2f}\n"
            f"  Free Margin: ${account_info['free_margin']:.2f}"
        )

        # Get symbol info
        symbol_info = self.connection.get_symbol_info(signal.symbol)
        if not symbol_info:
            logger.error(f"Could not get symbol info for {signal.symbol}")
            return False

        # Calculate position size
        lot_size = self.position_calculator.calculate_lot_size(
            account_balance=account_balance,
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
            symbol_info=symbol_info
        )

        if lot_size <= 0:
            logger.error("Calculated lot size is zero or negative")
            return False

        # Calculate risk amount
        risk_amount = self.position_calculator.calculate_risk_amount(
            lot_size=lot_size,
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
            symbol_info=symbol_info
        )

        # RISK MANAGEMENT CHECK
        can_trade, reason = self.risk_manager.can_open_position(
            account_balance=account_balance,
            proposed_risk=risk_amount,
            signal=signal.__dict__ if hasattr(signal, '__dict__') else None
        )

        if not can_trade:
            logger.warning(f"❌ RISK CHECK FAILED: {reason}")
            self._log_rejected_signal(signal, reason)
            return False

        logger.info(f"✅ RISK CHECK PASSED - Proceeding with execution")

        # DRY RUN MODE - Don't actually execute
        if self.dry_run:
            logger.info(
                f"\n{'='*70}\n"
                f"🧪 DRY RUN MODE - Trade NOT executed\n"
                f"{'='*70}\n"
                f"Would have opened:\n"
                f"  {signal.direction} {lot_size} lots of {signal.symbol}\n"
                f"  Entry: {signal.entry_price}\n"
                f"  SL: {signal.stop_loss} | TP: {signal.take_profit}\n"
                f"  Risk: ${risk_amount:.2f}\n"
                f"{'='*70}"
            )
            return True

        # EXECUTE TRADE
        logger.info(
            f"\n{'='*70}\n"
            f"🚀 EXECUTING TRADE\n"
            f"{'='*70}"
        )

        trade_result = self.trade_executor.execute_signal(
            signal={
                "symbol": signal.symbol,
                "direction": signal.direction,
                "entry_price": signal.entry_price,
                "stop_loss": signal.stop_loss,
                "take_profit": signal.take_profit,
                "confidence": signal.confidence,
            },
            account_balance=account_balance
        )

        if not trade_result.success:
            logger.error(f"Trade execution failed: {trade_result.error_message}")
            self._log_failed_execution(signal, trade_result.error_message)
            return False

        # SUCCESS - Update database and risk manager
        logger.info(
            f"\n{'='*70}\n"
            f"✅ TRADE EXECUTED SUCCESSFULLY\n"
            f"{'='*70}\n"
            f"  Ticket: {trade_result.ticket}\n"
            f"  Entry Price: {trade_result.entry_price}\n"
            f"  Lot Size: {trade_result.lot_size}\n"
            f"  Risk: ${risk_amount:.2f}\n"
            f"{'='*70}"
        )

        # Find the signal in database (it should have been saved by DatabaseSubscriber)
        with self.db_manager.session_scope() as session:
            # Get the most recent pending signal for this symbol/timeframe
            db_signal = self.signal_repo.get_pending_signals(session, limit=1)

            if db_signal:
                # Mark as executed
                self.signal_repo.mark_as_executed(
                    session=session,
                    signal_id=db_signal[0].id,
                    mt5_ticket=trade_result.ticket,
                    actual_entry=trade_result.entry_price
                )
                logger.info(f"Database updated: Signal #{db_signal[0].id} marked as executed")

        # Register position with risk manager
        self.risk_manager.register_position_opened(
            ticket=trade_result.ticket,
            symbol=signal.symbol,
            direction=signal.direction,
            lot_size=trade_result.lot_size,
            entry_price=trade_result.entry_price,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            risk_amount=risk_amount
        )

        return True

    def _log_rejected_signal(self, signal: 'ValidatedSignal', reason: str):
        """Log rejected signal to database"""
        try:
            with self.db_manager.session_scope() as session:
                # Find the pending signal
                pending = self.signal_repo.get_pending_signals(session, limit=1)
                if pending:
                    signal_obj = pending[0]
                    signal_obj.status = SignalStatus.CANCELLED
                    signal_obj.error_message = f"Risk check failed: {reason}"
                    session.commit()
                    logger.info(f"Signal #{signal_obj.id} marked as cancelled in database")
        except Exception as e:
            logger.error(f"Error logging rejected signal: {e}")

    def _log_failed_execution(self, signal: 'ValidatedSignal', error_message: str):
        """Log failed execution to database"""
        try:
            with self.db_manager.session_scope() as session:
                pending = self.signal_repo.get_pending_signals(session, limit=1)
                if pending:
                    signal_obj = pending[0]
                    signal_obj.error_message = f"Execution failed: {error_message}"
                    signal_obj.status = SignalStatus.CANCELLED
                    session.commit()
                    logger.info(f"Signal #{signal_obj.id} marked as cancelled (execution failed)")
        except Exception as e:
            logger.error(f"Error logging failed execution: {e}")

    def get_statistics(self) -> dict:
        """Get execution statistics"""
        success_rate = (self.signals_executed / self.signals_received * 100) if self.signals_received > 0 else 0

        return {
            "signals_received": self.signals_received,
            "signals_executed": self.signals_executed,
            "signals_rejected": self.signals_rejected,
            "execution_rate": success_rate,
            "dry_run": self.dry_run,
        }

    def reset_statistics(self):
        """Reset execution statistics"""
        self.signals_received = 0
        self.signals_executed = 0
        self.signals_rejected = 0
        logger.info("MT5Subscriber statistics reset")

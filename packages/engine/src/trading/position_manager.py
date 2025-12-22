"""
Position Manager
Monitors open positions and updates database with real-time P&L
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import sys
from pathlib import Path

# Add src to path for database imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import DatabaseManager
from database.signal_repository import SignalRepository
from database.models import SignalStatus

from .mt5_connection import MT5ConnectionBase, DirectMT5Connection, MetaAPIConnection
from .risk_manager import RiskManager

logger = logging.getLogger(__name__)


class PositionManager:
    """Monitor and manage open trading positions"""

    def __init__(
        self,
        connection: MT5ConnectionBase,
        db_manager: DatabaseManager,
        risk_manager: RiskManager,
        update_interval_seconds: int = 60
    ):
        self.connection = connection
        self.db_manager = db_manager
        self.signal_repo = SignalRepository(db_manager)
        self.risk_manager = risk_manager
        self.update_interval = update_interval_seconds
        self.running = False
        self._task = None

    async def start_monitoring(self):
        """Start monitoring positions in the background"""
        if self.running:
            logger.warning("Position manager already running")
            return

        self.running = True
        logger.info(f"Starting position monitoring (update interval: {self.update_interval}s)")

        self._task = asyncio.create_task(self._monitor_loop())

    async def stop_monitoring(self):
        """Stop monitoring positions"""
        if not self.running:
            return

        logger.info("Stopping position monitoring...")
        self.running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("Position monitoring stopped")

    async def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                await self.update_positions()
                await asyncio.sleep(self.update_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in position monitoring loop: {e}")
                await asyncio.sleep(self.update_interval)

    async def update_positions(self):
        """Update all open positions from MT5"""
        try:
            # Get all open positions from MT5
            mt5_positions = self._get_mt5_positions()

            if mt5_positions is None:
                logger.warning("Could not retrieve MT5 positions")
                return

            logger.debug(f"Retrieved {len(mt5_positions)} positions from MT5")

            # Get all active signals from database
            with self.db_manager.session_scope() as session:
                active_signals = self.signal_repo.get_open_signals(session)

                # Create map of ticket -> signal
                signal_map = {signal.mt5_ticket: signal for signal in active_signals if signal.mt5_ticket}

                # Process each MT5 position
                for mt5_pos in mt5_positions:
                    ticket = self._get_position_ticket(mt5_pos)

                    if ticket in signal_map:
                        signal = signal_map[ticket]
                        await self._update_signal_from_position(session, signal, mt5_pos)
                    else:
                        logger.debug(f"Position {ticket} not found in database (might be manual trade)")

                # Check for positions that closed
                for signal in active_signals:
                    if signal.mt5_ticket and signal.mt5_ticket not in [self._get_position_ticket(p) for p in mt5_positions]:
                        logger.info(f"Position {signal.mt5_ticket} closed, checking final state...")
                        await self._handle_closed_position(session, signal)

        except Exception as e:
            logger.error(f"Error updating positions: {e}")

    def _get_mt5_positions(self) -> Optional[List[Any]]:
        """Get all open positions from MT5"""
        try:
            if isinstance(self.connection, DirectMT5Connection):
                mt5 = self.connection.mt5
                positions = mt5.positions_get()
                return list(positions) if positions else []

            elif isinstance(self.connection, MetaAPIConnection):
                connection = self.connection.connection
                positions = connection.get_positions()
                return positions if positions else []

            return None

        except Exception as e:
            logger.error(f"Error getting MT5 positions: {e}")
            return None

    def _get_position_ticket(self, position) -> int:
        """Extract ticket number from position (handles both MT5 and MetaAPI)"""
        if isinstance(self.connection, DirectMT5Connection):
            return position.ticket
        elif isinstance(self.connection, MetaAPIConnection):
            return int(position.get("id", 0))
        return 0

    async def _update_signal_from_position(self, session, signal, mt5_position):
        """Update signal with current position data"""
        try:
            # Get current P&L
            if isinstance(self.connection, DirectMT5Connection):
                current_pnl = mt5_position.profit
                current_price = mt5_position.price_current
                open_price = mt5_position.price_open
                volume = mt5_position.volume
            elif isinstance(self.connection, MetaAPIConnection):
                current_pnl = mt5_position.get("profit", 0)
                current_price = mt5_position.get("currentPrice", 0)
                open_price = mt5_position.get("openPrice", 0)
                volume = mt5_position.get("volume", 0)
            else:
                return

            # Calculate P&L in pips
            symbol_info = self.connection.get_symbol_info(signal.symbol)
            if symbol_info:
                pip_value = symbol_info["point"]
                pnl_pips = (current_price - open_price) / pip_value
                if signal.direction.value == "SHORT":
                    pnl_pips = -pnl_pips
            else:
                pnl_pips = 0

            # Update signal (but don't change status, it's still active)
            signal.pnl = current_pnl
            signal.pnl_pips = pnl_pips
            if current_pnl != 0 and signal.actual_entry:
                signal.pnl_pct = (current_pnl / (signal.actual_entry * volume * 100)) * 100

            session.commit()

            logger.debug(
                f"Updated position {signal.mt5_ticket}: "
                f"P&L=${current_pnl:.2f} ({pnl_pips:.1f} pips)"
            )

        except Exception as e:
            logger.error(f"Error updating signal from position: {e}")
            session.rollback()

    async def _handle_closed_position(self, session, signal):
        """Handle a position that has been closed"""
        try:
            # Get closed trades history to find final P&L
            if isinstance(self.connection, DirectMT5Connection):
                mt5 = self.connection.mt5
                # Get deals for this position
                from datetime import timedelta
                from_date = signal.executed_at - timedelta(days=1) if signal.executed_at else datetime.now() - timedelta(days=7)
                deals = mt5.history_deals_get(from_date, datetime.now(), position=signal.mt5_ticket)

                if deals:
                    # Last deal should be the close
                    close_deal = deals[-1]
                    close_price = close_deal.price
                    final_pnl = sum(deal.profit for deal in deals)

                    # Determine close reason
                    if abs(close_price - signal.take_profit) < 0.01:
                        close_status = SignalStatus.CLOSED_TP
                    elif abs(close_price - signal.stop_loss) < 0.01:
                        close_status = SignalStatus.CLOSED_SL
                    else:
                        close_status = SignalStatus.CLOSED_MANUAL

                    # Close the signal in database
                    self.signal_repo.close_signal(
                        session=session,
                        signal_id=signal.id,
                        actual_exit=close_price,
                        pnl=final_pnl,
                        status=close_status
                    )

                    # Update risk manager
                    pnl_pips = signal.pnl_pips or 0
                    self.risk_manager.register_position_closed(
                        ticket=signal.mt5_ticket,
                        close_price=close_price,
                        pnl=final_pnl,
                        pnl_pips=pnl_pips,
                        close_reason=close_status.value
                    )

                    logger.info(
                        f"Position {signal.mt5_ticket} closed:\n"
                        f"  Close price: {close_price}\n"
                        f"  Final P&L: ${final_pnl:.2f}\n"
                        f"  Status: {close_status.value}"
                    )

            elif isinstance(self.connection, MetaAPIConnection):
                # For MetaAPI, we need to check history
                connection = self.connection.connection
                # MetaAPI automatically tracks closed positions
                # We can mark it as closed in our database
                self.signal_repo.close_signal(
                    session=session,
                    signal_id=signal.id,
                    actual_exit=signal.actual_entry,  # We don't have exact close price
                    pnl=signal.pnl or 0,
                    status=SignalStatus.CLOSED_MANUAL
                )

                self.risk_manager.register_position_closed(
                    ticket=signal.mt5_ticket,
                    close_price=signal.actual_entry,
                    pnl=signal.pnl or 0,
                    pnl_pips=signal.pnl_pips or 0,
                    close_reason="closed"
                )

                logger.info(f"Position {signal.mt5_ticket} closed (MetaAPI)")

        except Exception as e:
            logger.error(f"Error handling closed position: {e}")
            session.rollback()

    def sync_positions_on_startup(self):
        """
        Sync positions on startup to catch any that were opened/closed while service was down
        """
        logger.info("Syncing positions on startup...")

        try:
            mt5_positions = self._get_mt5_positions()
            if mt5_positions is None:
                logger.warning("Could not retrieve MT5 positions for sync")
                return

            mt5_tickets = {self._get_position_ticket(p) for p in mt5_positions}

            with self.db_manager.session_scope() as session:
                active_signals = self.signal_repo.get_open_signals(session)

                for signal in active_signals:
                    if signal.mt5_ticket:
                        if signal.mt5_ticket not in mt5_tickets:
                            # Position is closed but still marked as active in database
                            logger.warning(
                                f"Signal {signal.id} (ticket {signal.mt5_ticket}) is marked as active "
                                f"but position is closed. Marking as closed."
                            )
                            self.signal_repo.close_signal(
                                session=session,
                                signal_id=signal.id,
                                actual_exit=signal.entry_price,  # Best guess
                                pnl=0,  # Unknown
                                status=SignalStatus.CLOSED_MANUAL,
                                notes="Closed while service was offline"
                            )

                # Register open positions with risk manager
                for mt5_pos in mt5_positions:
                    ticket = self._get_position_ticket(mt5_pos)

                    # Find corresponding signal
                    signal = next((s for s in active_signals if s.mt5_ticket == ticket), None)

                    if signal:
                        # Calculate risk amount
                        if isinstance(self.connection, DirectMT5Connection):
                            volume = mt5_pos.volume
                            entry = mt5_pos.price_open
                        else:
                            volume = mt5_pos.get("volume", 0)
                            entry = mt5_pos.get("openPrice", 0)

                        symbol_info = self.connection.get_symbol_info(signal.symbol)
                        if symbol_info:
                            pip_value = symbol_info["point"]
                            contract_size = symbol_info["trade_contract_size"]
                            sl_pips = abs(entry - signal.stop_loss) / pip_value
                            risk_amount = volume * sl_pips * pip_value * contract_size

                            self.risk_manager.register_position_opened(
                                ticket=ticket,
                                symbol=signal.symbol,
                                direction=signal.direction.value,
                                lot_size=volume,
                                entry_price=entry,
                                stop_loss=signal.stop_loss,
                                take_profit=signal.take_profit,
                                risk_amount=risk_amount
                            )

            logger.info(f"Position sync complete. {len(mt5_tickets)} open positions found.")

        except Exception as e:
            logger.error(f"Error syncing positions on startup: {e}")

    def get_position_summary(self) -> Dict[str, Any]:
        """Get summary of current positions"""
        try:
            mt5_positions = self._get_mt5_positions()
            if mt5_positions is None:
                return {"error": "Could not retrieve positions"}

            total_pnl = 0
            positions_summary = []

            for mt5_pos in mt5_positions:
                if isinstance(self.connection, DirectMT5Connection):
                    positions_summary.append({
                        "ticket": mt5_pos.ticket,
                        "symbol": mt5_pos.symbol,
                        "type": "LONG" if mt5_pos.type == 0 else "SHORT",
                        "volume": mt5_pos.volume,
                        "entry": mt5_pos.price_open,
                        "current": mt5_pos.price_current,
                        "sl": mt5_pos.sl,
                        "tp": mt5_pos.tp,
                        "pnl": mt5_pos.profit,
                    })
                    total_pnl += mt5_pos.profit

                elif isinstance(self.connection, MetaAPIConnection):
                    pos = mt5_pos
                    positions_summary.append({
                        "ticket": pos.get("id"),
                        "symbol": pos.get("symbol"),
                        "type": pos.get("type", "").upper(),
                        "volume": pos.get("volume"),
                        "entry": pos.get("openPrice"),
                        "current": pos.get("currentPrice"),
                        "sl": pos.get("stopLoss"),
                        "tp": pos.get("takeProfit"),
                        "pnl": pos.get("profit"),
                    })
                    total_pnl += pos.get("profit", 0)

            return {
                "total_positions": len(positions_summary),
                "total_pnl": total_pnl,
                "positions": positions_summary
            }

        except Exception as e:
            logger.error(f"Error getting position summary: {e}")
            return {"error": str(e)}

"""
Signal repository for CRUD operations.
"""

from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from typing import List, Optional
from datetime import datetime, timedelta

from .models import Signal, SignalStatus, SignalDirection


class SignalRepository:
    """Repository for managing signals in the database."""

    def __init__(self, session: Session):
        """
        Initialize repository with database session.

        Args:
            session: SQLAlchemy session
        """
        self.session = session

    def create(self, signal: Signal) -> Signal:
        """
        Create a new signal in the database.

        Args:
            signal: Signal object to create

        Returns:
            Created signal with ID assigned
        """
        self.session.add(signal)
        self.session.commit()
        self.session.refresh(signal)
        return signal

    def get_by_id(self, signal_id: int) -> Optional[Signal]:
        """
        Get signal by ID.

        Args:
            signal_id: Signal ID

        Returns:
            Signal or None if not found
        """
        return self.session.query(Signal).filter(Signal.id == signal_id).first()

    def get_all(self, limit: int = 100, offset: int = 0) -> List[Signal]:
        """
        Get all signals with pagination.

        Args:
            limit: Maximum number of signals to return
            offset: Number of signals to skip

        Returns:
            List of signals
        """
        return (
            self.session.query(Signal)
            .order_by(desc(Signal.timestamp))
            .limit(limit)
            .offset(offset)
            .all()
        )

    def get_recent(self, days: int = 30, limit: int = 100) -> List[Signal]:
        """
        Get recent signals from the last N days.

        Args:
            days: Number of days to look back
            limit: Maximum number of signals to return

        Returns:
            List of recent signals
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        return (
            self.session.query(Signal)
            .filter(Signal.timestamp >= cutoff_date)
            .order_by(desc(Signal.timestamp))
            .limit(limit)
            .all()
        )

    def get_by_status(self, status: SignalStatus, limit: int = 100) -> List[Signal]:
        """
        Get signals by status.

        Args:
            status: Signal status to filter by
            limit: Maximum number of signals to return

        Returns:
            List of signals with given status
        """
        return (
            self.session.query(Signal)
            .filter(Signal.status == status)
            .order_by(desc(Signal.timestamp))
            .limit(limit)
            .all()
        )

    def get_open_signals(self) -> List[Signal]:
        """
        Get all currently open signals.

        Returns:
            List of active signals
        """
        return self.get_by_status(SignalStatus.ACTIVE)

    def get_pending_signals(self) -> List[Signal]:
        """
        Get all pending signals (not yet executed).

        Returns:
            List of pending signals
        """
        return self.get_by_status(SignalStatus.PENDING)

    def update(self, signal: Signal) -> Signal:
        """
        Update an existing signal.

        Args:
            signal: Signal object to update

        Returns:
            Updated signal
        """
        self.session.commit()
        self.session.refresh(signal)
        return signal

    def close_signal(
        self,
        signal_id: int,
        exit_price: float,
        pnl: float,
        status: SignalStatus = SignalStatus.CLOSED_MANUAL
    ) -> Optional[Signal]:
        """
        Close a signal and record the outcome.

        Args:
            signal_id: ID of signal to close
            exit_price: Exit price
            pnl: Profit/Loss in dollars
            status: Close status (TP, SL, or manual)

        Returns:
            Updated signal or None if not found
        """
        signal = self.get_by_id(signal_id)
        if not signal:
            return None

        signal.actual_exit = exit_price
        signal.pnl = pnl
        signal.status = status
        signal.closed_at = datetime.utcnow()

        # Calculate P&L percentage
        if signal.actual_entry:
            signal.pnl_pct = (pnl / signal.actual_entry) * 100

        # Calculate P&L in pips
        if signal.direction == SignalDirection.LONG:
            signal.pnl_pips = (exit_price - signal.actual_entry) * 10
        else:
            signal.pnl_pips = (signal.actual_entry - exit_price) * 10

        return self.update(signal)

    def mark_as_executed(
        self,
        signal_id: int,
        mt5_ticket: int,
        actual_entry: float
    ) -> Optional[Signal]:
        """
        Mark signal as executed with MT5 details.

        Args:
            signal_id: ID of signal
            mt5_ticket: MT5 order ticket number
            actual_entry: Actual entry price

        Returns:
            Updated signal or None if not found
        """
        signal = self.get_by_id(signal_id)
        if not signal:
            return None

        signal.status = SignalStatus.ACTIVE
        signal.mt5_ticket = mt5_ticket
        signal.actual_entry = actual_entry
        signal.executed_at = datetime.utcnow()

        return self.update(signal)

    def get_performance_stats(self, days: int = 30) -> dict:
        """
        Calculate performance statistics for the last N days.

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary with performance metrics
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Get all closed signals in period
        closed_signals = (
            self.session.query(Signal)
            .filter(
                and_(
                    Signal.timestamp >= cutoff_date,
                    Signal.status.in_([SignalStatus.CLOSED_TP, SignalStatus.CLOSED_SL, SignalStatus.CLOSED_MANUAL])
                )
            )
            .all()
        )

        if not closed_signals:
            return {
                'total_signals': 0,
                'winning_signals': 0,
                'losing_signals': 0,
                'win_rate': 0.0,
                'total_pnl': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'largest_win': 0.0,
                'largest_loss': 0.0,
                'profit_factor': 0.0,
            }

        # Calculate metrics
        winners = [s for s in closed_signals if s.pnl and s.pnl > 0]
        losers = [s for s in closed_signals if s.pnl and s.pnl < 0]

        total_wins = sum(s.pnl for s in winners)
        total_losses = abs(sum(s.pnl for s in losers))

        return {
            'total_signals': len(closed_signals),
            'winning_signals': len(winners),
            'losing_signals': len(losers),
            'win_rate': (len(winners) / len(closed_signals) * 100) if closed_signals else 0.0,
            'total_pnl': sum(s.pnl for s in closed_signals if s.pnl),
            'avg_win': (total_wins / len(winners)) if winners else 0.0,
            'avg_loss': (total_losses / len(losers)) if losers else 0.0,
            'largest_win': max((s.pnl for s in winners), default=0.0),
            'largest_loss': min((s.pnl for s in losers), default=0.0),
            'profit_factor': (total_wins / total_losses) if total_losses > 0 else 0.0,
        }

    def delete(self, signal_id: int) -> bool:
        """
        Delete a signal (use with caution).

        Args:
            signal_id: ID of signal to delete

        Returns:
            True if deleted, False if not found
        """
        signal = self.get_by_id(signal_id)
        if not signal:
            return False

        self.session.delete(signal)
        self.session.commit()
        return True

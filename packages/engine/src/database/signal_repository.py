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

    def get_open_signals(self, symbol: str = None, timeframe: str = None) -> List[Signal]:
        """
        Get all signals that are still open (PENDING or ACTIVE), optionally
        filtered by symbol and/or timeframe.

        Args:
            symbol: If given, only signals for this symbol
            timeframe: If given, only signals for this timeframe

        Returns:
            List of open signals, most recent first
        """
        query = self.session.query(Signal).filter(
            Signal.status.in_([SignalStatus.PENDING, SignalStatus.ACTIVE])
        )
        if symbol:
            query = query.filter(Signal.symbol == symbol)
        if timeframe:
            query = query.filter(Signal.timeframe == timeframe)
        return query.order_by(desc(Signal.timestamp)).all()

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

    def close_open_signal(
        self,
        signal_id: int,
        exit_price: Optional[float],
        status: SignalStatus,
        closed_at: datetime,
        note_suffix: str = "",
    ) -> Optional[Signal]:
        """
        Close a signal that was never executed via MT5 (no actual_entry set),
        computing pnl_pips from the planned entry_price instead. Used by the
        signal outcome tracker for TP/SL hits and expiry — does not set
        pnl/pnl_pct since there is no real account behind these signals yet.

        Args:
            signal_id: ID of signal to close
            exit_price: Exit price, or None for an expiry with no resolution
            status: CLOSED_TP, CLOSED_SL, or CANCELLED (expiry)
            closed_at: Timestamp of the candle that triggered this close
            note_suffix: Text appended to the signal's existing notes

        Returns:
            Updated signal or None if not found
        """
        signal = self.get_by_id(signal_id)
        if not signal:
            return None

        signal.actual_exit = exit_price
        signal.status = status
        signal.closed_at = closed_at

        if exit_price is not None:
            if signal.direction == SignalDirection.LONG:
                signal.pnl_pips = (exit_price - signal.entry_price) * 10
            else:
                signal.pnl_pips = (signal.entry_price - exit_price) * 10

        if note_suffix:
            signal.notes = (signal.notes or "") + note_suffix

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

    def get_performance_stats(self, days: int = 30, symbol: str = None, timeframe: str = None) -> dict:
        """
        Calculate signal outcome statistics for the last N days.

        No dollar P&L is used (there is no real account behind these signals
        yet) — win rate is measured over resolved (TP/SL) signals, and
        edge is measured in R-multiples (pnl_pips / risk_pips).

        Args:
            days: Number of days to analyze
            symbol: If given, only signals for this symbol
            timeframe: If given, only signals for this timeframe

        Returns:
            Dictionary with keys: total_signals, tp_hits, sl_hits, expired,
            still_open, closed_manual, win_rate, avg_r_multiple, net_r_multiple
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        filters = [Signal.timestamp >= cutoff_date]
        if symbol:
            filters.append(Signal.symbol == symbol)
        if timeframe:
            filters.append(Signal.timeframe == timeframe)

        all_signals = self.session.query(Signal).filter(and_(*filters)).all()

        tp_hits = [s for s in all_signals if s.status == SignalStatus.CLOSED_TP]
        sl_hits = [s for s in all_signals if s.status == SignalStatus.CLOSED_SL]
        expired = [
            s for s in all_signals
            if s.status == SignalStatus.CANCELLED and s.notes and '[expired' in s.notes
        ]
        still_open = [s for s in all_signals if s.status in (SignalStatus.PENDING, SignalStatus.ACTIVE)]
        closed_manual = [s for s in all_signals if s.status == SignalStatus.CLOSED_MANUAL]

        resolved = tp_hits + sl_hits
        win_rate = (len(tp_hits) / len(resolved) * 100) if resolved else 0.0

        r_multiples = [
            s.pnl_pips / s.risk_pips
            for s in resolved
            if s.risk_pips and s.pnl_pips is not None
        ]
        avg_r = (sum(r_multiples) / len(r_multiples)) if r_multiples else 0.0
        net_r = sum(r_multiples)

        return {
            'total_signals': len(all_signals),
            'tp_hits': len(tp_hits),
            'sl_hits': len(sl_hits),
            'expired': len(expired),
            'still_open': len(still_open),
            'closed_manual': len(closed_manual),
            'win_rate': win_rate,
            'avg_r_multiple': avg_r,
            'net_r_multiple': net_r,
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

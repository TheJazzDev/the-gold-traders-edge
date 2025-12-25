"""
Database Subscriber

Saves validated signals to SQLite database for persistence and tracking.
"""

import sys
from pathlib import Path
import logging
from datetime import datetime

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database.models import Signal, SignalDirection, SignalStatus, init_database
from database.connection import DatabaseManager
from database.signal_repository import SignalRepository

logger = logging.getLogger(__name__)


class DatabaseSubscriber:
    """
    Subscriber that saves signals to database.

    Features:
    - Saves all signal metadata to SQLite
    - Stores signals as "pending" status initially
    - Calculates and stores risk metrics
    - Provides signal retrieval methods
    - Thread-safe database operations
    """

    def __init__(self, database_url: str = None):
        """
        Initialize database subscriber.

        Args:
            database_url: SQLAlchemy database URL (default: sqlite:///signals.db)
        """
        # Create our own database manager (don't use global singleton)
        self.db_manager = DatabaseManager(database_url)

        # Create tables if they don't exist
        init_database(self.db_manager.database_url)

        logger.info(f"✅ DatabaseSubscriber initialized: {self.db_manager.database_url}")

    def __call__(self, signal):
        """
        Receive and save signal to database.

        This method is called by the signal generator when a new signal is published.

        Args:
            signal: ValidatedSignal instance
        """
        try:
            self.save_signal(signal)
        except Exception as e:
            logger.error(f"Failed to save signal to database: {e}", exc_info=True)

    def save_signal(self, validated_signal) -> Signal:
        """
        Save validated signal to database.

        Args:
            validated_signal: ValidatedSignal from signal generator

        Returns:
            Saved Signal model instance
        """
        # Map direction string to enum
        direction = (
            SignalDirection.LONG
            if validated_signal.direction == "LONG"
            else SignalDirection.SHORT
        )

        # Helper function to convert NumPy types to Python types
        def to_python_float(value):
            """Convert NumPy float64/float32 to Python float."""
            if hasattr(value, 'item'):  # NumPy scalar
                return float(value.item())
            return float(value)

        # Create Signal model instance (convert all NumPy types to Python types)
        signal = Signal(
            # Metadata
            timestamp=validated_signal.timestamp,
            symbol=validated_signal.symbol,
            timeframe=validated_signal.timeframe,
            strategy_name=validated_signal.strategy_name,

            # Signal details (convert NumPy floats to Python floats)
            direction=direction,
            entry_price=to_python_float(validated_signal.entry_price),
            stop_loss=to_python_float(validated_signal.stop_loss),
            take_profit=to_python_float(validated_signal.take_profit),
            confidence=to_python_float(validated_signal.confidence),

            # Risk metrics (convert NumPy floats to Python floats)
            risk_pips=to_python_float(validated_signal.risk_pips),
            reward_pips=to_python_float(validated_signal.reward_pips),
            risk_reward_ratio=to_python_float(validated_signal.risk_reward_ratio),

            # Status (pending until executed)
            status=SignalStatus.PENDING,

            # Notes
            notes=validated_signal.notes
        )

        # Save to database using repository
        with self.db_manager.session_scope() as session:
            repository = SignalRepository(session)
            saved_signal = repository.create(signal)

            logger.info(
                f"💾 Signal saved to database: ID={saved_signal.id}, "
                f"{validated_signal.direction} @ ${validated_signal.entry_price:.2f}"
            )

            return saved_signal

    def get_recent_signals(self, days: int = 30, limit: int = 100):
        """
        Get recent signals from database.

        Args:
            days: Number of days to look back
            limit: Maximum signals to return

        Returns:
            List of Signal instances
        """
        with self.db_manager.session_scope() as session:
            repository = SignalRepository(session)
            return repository.get_recent(days=days, limit=limit)

    def get_pending_signals(self):
        """
        Get all pending signals (not yet executed).

        Returns:
            List of pending Signal instances
        """
        with self.db_manager.session_scope() as session:
            repository = SignalRepository(session)
            return repository.get_pending_signals()

    def get_performance_stats(self, days: int = 30):
        """
        Get performance statistics.

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary with performance metrics
        """
        with self.db_manager.session_scope() as session:
            repository = SignalRepository(session)
            return repository.get_performance_stats(days=days)

    def mark_signal_executed(self, signal_id: int, mt5_ticket: int, actual_entry: float):
        """
        Mark a signal as executed (trade placed).

        Args:
            signal_id: Database signal ID
            mt5_ticket: MT5 order ticket number
            actual_entry: Actual entry price executed

        Returns:
            Updated Signal instance
        """
        with self.db_manager.session_scope() as session:
            repository = SignalRepository(session)
            return repository.mark_as_executed(signal_id, mt5_ticket, actual_entry)

    def close_signal(
        self,
        signal_id: int,
        exit_price: float,
        pnl: float,
        status: SignalStatus = SignalStatus.CLOSED_MANUAL
    ):
        """
        Close a signal and record outcome.

        Args:
            signal_id: Database signal ID
            exit_price: Exit price
            pnl: Profit/Loss in dollars
            status: Close status (TP/SL/manual)

        Returns:
            Updated Signal instance
        """
        with self.db_manager.session_scope() as session:
            repository = SignalRepository(session)
            return repository.close_signal(signal_id, exit_price, pnl, status)


if __name__ == "__main__":
    """Test database subscriber."""
    from signals.realtime_generator import ValidatedSignal
    import pandas as pd

    print("=" * 70)
    print("🧪 TESTING DATABASE SUBSCRIBER")
    print("=" * 70)

    # Create subscriber
    print("\n1. Creating database subscriber...")
    subscriber = DatabaseSubscriber()

    # Create a test signal
    print("\n2. Creating test signal...")
    test_signal = ValidatedSignal(
        timestamp=pd.Timestamp.now(),
        symbol="XAUUSD",
        timeframe="4H",
        strategy_name="Momentum Equilibrium",
        direction="LONG",
        entry_price=2650.50,
        stop_loss=2635.20,
        take_profit=2681.10,
        confidence=0.75,
        risk_pips=153.0,
        reward_pips=306.0,
        risk_reward_ratio=2.0,
        notes="Test signal for database subscriber",
        current_price=2650.50
    )

    # Save signal
    print("\n3. Saving signal to database...")
    saved = subscriber.save_signal(test_signal)
    print(f"   ✅ Signal saved with ID: {saved.id}")

    # Retrieve recent signals
    print("\n4. Retrieving recent signals...")
    recent = subscriber.get_recent_signals(days=1, limit=10)
    print(f"   Found {len(recent)} signal(s) in last 24 hours")

    for signal in recent:
        print(f"\n   Signal ID: {signal.id}")
        print(f"   {signal.direction.value} @ ${signal.entry_price:.2f}")
        print(f"   Status: {signal.status.value}")
        print(f"   R:R: 1:{signal.risk_reward_ratio:.2f}")
        print(f"   Timestamp: {signal.timestamp}")

    # Get pending signals
    print("\n5. Getting pending signals...")
    pending = subscriber.get_pending_signals()
    print(f"   Found {len(pending)} pending signal(s)")

    # Get performance stats
    print("\n6. Getting performance statistics...")
    stats = subscriber.get_performance_stats(days=30)
    print(f"   Total signals: {stats['total_signals']}")
    print(f"   Win rate: {stats['win_rate']:.1f}%")

    print("\n" + "=" * 70)
    print("✅ DATABASE SUBSCRIBER TEST COMPLETE!")
    print("=" * 70)

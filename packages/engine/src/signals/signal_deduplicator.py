"""
Signal Deduplicator

Prevents duplicate signals from being sent across multiple timeframes.

When the same setup appears on multiple timeframes (e.g., an order block on 1H, 4H, and 1D),
only the first signal is sent. Subsequent duplicate signals within a time window are suppressed.

IMPORTANT: This deduplicator is DATABASE-BACKED to persist across deployments.
On startup, it loads recent signals from the database to prevent duplicate notifications
when the service restarts.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
import hashlib
import os

logger = logging.getLogger(__name__)


@dataclass
class SignalFingerprint:
    """
    Unique identifier for a signal based on its key characteristics.
    """
    direction: str  # LONG or SHORT
    strategy_name: str  # e.g., "Order Block Retest"
    entry_price: float
    stop_loss: float
    take_profit: float
    timestamp: datetime

    def to_hash(self) -> str:
        """
        Create a hash from signal characteristics.

        Signals are considered duplicates if they have:
        - Same direction
        - Same strategy
        - Similar entry price (within 0.1%)
        - Similar stop loss (within 0.1%)
        - Similar take profit (within 0.1%)
        """
        # Round prices to reduce false negatives from minor price differences
        entry_rounded = round(self.entry_price, 2)
        sl_rounded = round(self.stop_loss, 2)
        tp_rounded = round(self.take_profit, 2)

        # Create a string representation
        signal_str = f"{self.direction}_{self.strategy_name}_{entry_rounded}_{sl_rounded}_{tp_rounded}"

        # Return hash for efficient comparison
        return hashlib.md5(signal_str.encode()).hexdigest()


class SignalDeduplicator:
    """
    Shared deduplicator across all timeframes.

    This prevents the same signal from being sent multiple times when it appears
    on different timeframes (which is common for strong setups).

    Example:
        - 1H timeframe detects Order Block LONG @ 2650.50
        - 4H timeframe detects same Order Block LONG @ 2650.50
        - 1D timeframe detects same Order Block LONG @ 2650.50

        Only the FIRST signal is sent. The other two are suppressed.

    DATABASE-BACKED: On startup, loads recent signals from database to prevent
    duplicate notifications when the service restarts (Railway deployments).
    """

    def __init__(self, dedup_window_hours: int = 4, database_url: Optional[str] = None):
        """
        Initialize deduplicator.

        Args:
            dedup_window_hours: Time window for duplicate detection (default: 4 hours)
            database_url: Database URL for persistence (default: from DATABASE_URL env)
        """
        self.dedup_window_hours = dedup_window_hours
        self.recent_signals: Dict[str, SignalFingerprint] = {}
        self.database_url = database_url or os.getenv('DATABASE_URL')

        # Load recent signals from database on startup
        self._load_recent_signals_from_db()

        logger.info(f"✅ SignalDeduplicator initialized (window: {dedup_window_hours}h, db-backed: {self.database_url is not None})")

    def is_duplicate(self, validated_signal) -> bool:
        """
        Check if this signal is a duplicate of a recent signal.

        Args:
            validated_signal: ValidatedSignal instance

        Returns:
            True if duplicate, False if unique
        """
        # Create fingerprint
        fingerprint = SignalFingerprint(
            direction=validated_signal.direction,
            strategy_name=validated_signal.strategy_name,
            entry_price=validated_signal.entry_price,
            stop_loss=validated_signal.stop_loss,
            take_profit=validated_signal.take_profit,
            timestamp=validated_signal.timestamp
        )

        signal_hash = fingerprint.to_hash()

        # Clean up old signals
        self._cleanup_old_signals()

        # Check if this signal hash exists
        if signal_hash in self.recent_signals:
            existing = self.recent_signals[signal_hash]
            logger.info(
                f"🚫 Duplicate signal detected:\n"
                f"   Original: {existing.strategy_name} {existing.direction} @ ${existing.entry_price:.2f} "
                f"from {validated_signal.timeframe} at {existing.timestamp}\n"
                f"   Suppressed: Same signal from {validated_signal.timeframe}"
            )
            return True

        # Not a duplicate - add to recent signals
        self.recent_signals[signal_hash] = fingerprint
        logger.debug(f"✅ Unique signal: {fingerprint.strategy_name} {fingerprint.direction} @ ${fingerprint.entry_price:.2f}")

        return False

    def _cleanup_old_signals(self):
        """Remove signals outside the deduplication window."""
        cutoff = datetime.now() - timedelta(hours=self.dedup_window_hours)

        # Remove old signals
        old_count = len(self.recent_signals)
        self.recent_signals = {
            hash_key: signal
            for hash_key, signal in self.recent_signals.items()
            if signal.timestamp.replace(tzinfo=None) > cutoff
        }

        removed = old_count - len(self.recent_signals)
        if removed > 0:
            logger.debug(f"🧹 Cleaned up {removed} old signal(s)")

    def _load_recent_signals_from_db(self):
        """
        Load recent signals from database on startup.

        This prevents duplicate notifications when the service restarts (e.g., Railway deployments).
        Without this, the in-memory deduplicator would be empty on startup and all signals
        would appear "unique", causing duplicate Telegram notifications.
        """
        if not self.database_url:
            logger.warning("⚠️  No database URL provided - deduplicator will NOT persist across restarts!")
            logger.warning("   Set DATABASE_URL environment variable to enable database-backed deduplication")
            return

        try:
            from database.connection import DatabaseManager
            from database.models import Signal
            from datetime import timezone

            # Create database manager
            db_manager = DatabaseManager(self.database_url)

            # Calculate cutoff time (only load signals within dedup window)
            cutoff = datetime.now(timezone.utc) - timedelta(hours=self.dedup_window_hours)

            # Load recent signals from database
            with db_manager.get_session() as session:
                recent_db_signals = (
                    session.query(Signal)
                    .filter(Signal.timestamp >= cutoff)
                    .order_by(Signal.timestamp.desc())
                    .all()
                )

                # Convert to fingerprints and add to in-memory cache
                loaded_count = 0
                for db_signal in recent_db_signals:
                    # Create fingerprint from database signal
                    fingerprint = SignalFingerprint(
                        direction=db_signal.direction.value if hasattr(db_signal.direction, 'value') else db_signal.direction,
                        strategy_name=db_signal.strategy_name,
                        entry_price=float(db_signal.entry_price),
                        stop_loss=float(db_signal.stop_loss),
                        take_profit=float(db_signal.take_profit),
                        timestamp=db_signal.timestamp
                    )

                    # Add to in-memory cache
                    signal_hash = fingerprint.to_hash()
                    self.recent_signals[signal_hash] = fingerprint
                    loaded_count += 1

                if loaded_count > 0:
                    logger.info(
                        f"✅ Loaded {loaded_count} recent signal(s) from database "
                        f"(prevents duplicate notifications on restart)"
                    )
                else:
                    logger.info("✅ No recent signals in database (clean startup)")

        except ImportError as e:
            logger.warning(f"⚠️  Database modules not available: {e}")
            logger.warning("   Deduplicator will work but won't persist across restarts")
        except Exception as e:
            logger.error(f"❌ Failed to load recent signals from database: {e}", exc_info=True)
            logger.warning("   Deduplicator will work but may send duplicate notifications on restart")

    def get_stats(self) -> Dict:
        """Get deduplicator statistics."""
        return {
            "recent_signals_count": len(self.recent_signals),
            "dedup_window_hours": self.dedup_window_hours,
            "oldest_signal": min(
                (s.timestamp for s in self.recent_signals.values()),
                default=None
            ),
            "newest_signal": max(
                (s.timestamp for s in self.recent_signals.values()),
                default=None
            )
        }


# Global singleton instance (shared across all timeframes)
_deduplicator_instance = None


def get_deduplicator(dedup_window_hours: int = 4, database_url: Optional[str] = None) -> SignalDeduplicator:
    """
    Get the global deduplicator instance (singleton pattern).

    Args:
        dedup_window_hours: Deduplication window in hours
        database_url: Database URL for persistence (default: from DATABASE_URL env)

    Returns:
        SignalDeduplicator instance
    """
    global _deduplicator_instance

    if _deduplicator_instance is None:
        _deduplicator_instance = SignalDeduplicator(dedup_window_hours, database_url)

    return _deduplicator_instance


if __name__ == "__main__":
    """Test the deduplicator."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from signals.realtime_generator import ValidatedSignal
    import pandas as pd

    print("=" * 70)
    print("🧪 TESTING SIGNAL DEDUPLICATOR")
    print("=" * 70)

    # Create deduplicator
    dedup = get_deduplicator(dedup_window_hours=4)

    # Create test signal
    signal1 = ValidatedSignal(
        timestamp=pd.Timestamp.now(),
        symbol="XAUUSD",
        timeframe="1h",
        strategy_name="Order Block Retest",
        direction="LONG",
        entry_price=2650.50,
        stop_loss=2635.20,
        take_profit=2681.10,
        confidence=0.75,
        risk_pips=153.0,
        reward_pips=306.0,
        risk_reward_ratio=2.0,
        notes="Test signal",
        current_price=2650.50
    )

    # Test 1: First signal should not be duplicate
    print("\n1. Testing first signal (should be unique)...")
    is_dup = dedup.is_duplicate(signal1)
    print(f"   Result: {'DUPLICATE' if is_dup else 'UNIQUE'} ✅")

    # Test 2: Same signal from different timeframe should be duplicate
    print("\n2. Testing same signal from 4h (should be duplicate)...")
    signal2 = ValidatedSignal(
        timestamp=pd.Timestamp.now(),
        symbol="XAUUSD",
        timeframe="4h",  # Different timeframe
        strategy_name="Order Block Retest",
        direction="LONG",
        entry_price=2650.50,  # Same levels
        stop_loss=2635.20,
        take_profit=2681.10,
        confidence=0.80,
        risk_pips=153.0,
        reward_pips=306.0,
        risk_reward_ratio=2.0,
        notes="Test signal from 4h",
        current_price=2650.50
    )

    is_dup = dedup.is_duplicate(signal2)
    print(f"   Result: {'DUPLICATE ✅' if is_dup else 'UNIQUE ❌'}")

    # Test 3: Different strategy should not be duplicate
    print("\n3. Testing different strategy (should be unique)...")
    signal3 = ValidatedSignal(
        timestamp=pd.Timestamp.now(),
        symbol="XAUUSD",
        timeframe="1h",
        strategy_name="Momentum Equilibrium",  # Different strategy
        direction="LONG",
        entry_price=2650.50,
        stop_loss=2635.20,
        take_profit=2681.10,
        confidence=0.75,
        risk_pips=153.0,
        reward_pips=306.0,
        risk_reward_ratio=2.0,
        notes="Test signal",
        current_price=2650.50
    )

    is_dup = dedup.is_duplicate(signal3)
    print(f"   Result: {'DUPLICATE ❌' if is_dup else 'UNIQUE ✅'}")

    # Test 4: Different direction should not be duplicate
    print("\n4. Testing opposite direction (should be unique)...")
    signal4 = ValidatedSignal(
        timestamp=pd.Timestamp.now(),
        symbol="XAUUSD",
        timeframe="1h",
        strategy_name="Order Block Retest",
        direction="SHORT",  # Different direction
        entry_price=2650.50,
        stop_loss=2665.80,
        take_profit=2619.90,
        confidence=0.75,
        risk_pips=153.0,
        reward_pips=306.0,
        risk_reward_ratio=2.0,
        notes="Test signal",
        current_price=2650.50
    )

    is_dup = dedup.is_duplicate(signal4)
    print(f"   Result: {'DUPLICATE ❌' if is_dup else 'UNIQUE ✅'}")

    # Show stats
    print("\n5. Deduplicator stats:")
    stats = dedup.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    print("\n" + "=" * 70)
    print("✅ DEDUPLICATOR TEST COMPLETE!")
    print("=" * 70)

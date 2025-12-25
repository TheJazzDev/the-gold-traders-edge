"""
Deduplication Subscriber

Wraps other subscribers and filters out duplicate signals before passing them through.
This ensures that when the same signal appears on multiple timeframes, only the first
instance is sent to Telegram, saved to database, etc.
"""

import logging
from typing import List, Callable
from signals.signal_deduplicator import get_deduplicator

logger = logging.getLogger(__name__)


class DeduplicationSubscriber:
    """
    Meta-subscriber that wraps other subscribers and prevents duplicates.

    Usage:
        # Create actual subscribers
        telegram = TelegramSubscriber()
        database = DatabaseSubscriber()

        # Wrap them with deduplication
        dedup = DeduplicationSubscriber([telegram, database])

        # Add to signal generator
        generator.add_subscriber(dedup)
    """

    def __init__(self, subscribers: List[Callable], dedup_window_hours: int = 4):
        """
        Initialize deduplication subscriber.

        Args:
            subscribers: List of subscriber callables to wrap
            dedup_window_hours: Deduplication time window in hours
        """
        self.subscribers = subscribers
        self.deduplicator = get_deduplicator(dedup_window_hours)

        logger.info(
            f"✅ DeduplicationSubscriber initialized with {len(subscribers)} subscriber(s), "
            f"{dedup_window_hours}h window"
        )

    def __call__(self, signal):
        """
        Receive signal, check for duplicates, and pass to subscribers if unique.

        Args:
            signal: ValidatedSignal instance
        """
        # Check if duplicate
        if self.deduplicator.is_duplicate(signal):
            logger.info(
                f"🚫 Suppressing duplicate signal: {signal.strategy_name} {signal.direction} "
                f"@ ${signal.entry_price:.2f} from {signal.timeframe}"
            )
            return

        # Not a duplicate - pass to all subscribers
        logger.debug(f"✅ Passing unique signal to {len(self.subscribers)} subscriber(s)")

        for subscriber in self.subscribers:
            try:
                subscriber(signal)
            except Exception as e:
                logger.error(
                    f"Subscriber {subscriber.__class__.__name__} failed: {e}",
                    exc_info=True
                )

    def add_subscriber(self, subscriber: Callable):
        """Add a subscriber to the list."""
        self.subscribers.append(subscriber)
        logger.info(f"Added subscriber: {subscriber.__class__.__name__}")

    def remove_subscriber(self, subscriber: Callable):
        """Remove a subscriber from the list."""
        self.subscribers.remove(subscriber)
        logger.info(f"Removed subscriber: {subscriber.__class__.__name__}")


if __name__ == "__main__":
    """Test deduplication subscriber."""
    from signals.realtime_generator import ValidatedSignal
    import pandas as pd

    print("=" * 70)
    print("🧪 TESTING DEDUPLICATION SUBSCRIBER")
    print("=" * 70)

    # Mock subscribers
    class MockSubscriber:
        def __init__(self, name):
            self.name = name
            self.received_count = 0

        def __call__(self, signal):
            self.received_count += 1
            print(f"   {self.name} received signal #{self.received_count}: "
                  f"{signal.direction} @ ${signal.entry_price:.2f}")

    # Create mock subscribers
    mock1 = MockSubscriber("Database")
    mock2 = MockSubscriber("Telegram")

    # Create dedup subscriber
    dedup = DeduplicationSubscriber([mock1, mock2])

    # Create test signals
    print("\n1. Sending first signal from 1h timeframe...")
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
        notes="Test signal from 1h",
        current_price=2650.50
    )
    dedup(signal1)

    print("\n2. Sending duplicate signal from 4h timeframe (should be suppressed)...")
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
        notes="Test signal from 4h (duplicate)",
        current_price=2650.50
    )
    dedup(signal2)

    print("\n3. Sending different signal (should pass through)...")
    signal3 = ValidatedSignal(
        timestamp=pd.Timestamp.now(),
        symbol="XAUUSD",
        timeframe="1h",
        strategy_name="Momentum Equilibrium",  # Different strategy
        direction="LONG",
        entry_price=2655.00,
        stop_loss=2640.00,
        take_profit=2685.00,
        confidence=0.70,
        risk_pips=150.0,
        reward_pips=300.0,
        risk_reward_ratio=2.0,
        notes="Test signal - Momentum",
        current_price=2655.00
    )
    dedup(signal3)

    print("\n" + "=" * 70)
    print("📊 RESULTS:")
    print("=" * 70)
    print(f"Database subscriber received: {mock1.received_count} signals (expected: 2)")
    print(f"Telegram subscriber received: {mock2.received_count} signals (expected: 2)")
    print("\n✅ TEST COMPLETE!")
    print("=" * 70)

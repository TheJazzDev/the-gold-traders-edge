"""
Real-Time Signal Generator Service

This module generates trading signals in real-time by:
1. Connecting to a data feed (Yahoo Finance, MT5, or MetaAPI)
2. Waiting for candle closes
3. Running strategy analysis
4. Validating signals
5. Publishing signals to subscribers

Architecture:
- Data Feed → Signal Generator → Signal Publisher → Database/Telegram/WebAPI
"""

import pandas as pd
import sys
from pathlib import Path
from typing import Optional, Dict, List, Callable
from datetime import datetime
import logging
from dataclasses import dataclass, asdict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.realtime_feed import RealtimeDataFeed, create_datafeed
from signals.gold_strategy import GoldStrategy
from backtesting.engine import Signal as StrategySignal, TradeDirection


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('signal_generator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class ValidatedSignal:
    """
    Validated trading signal ready for publishing.

    This is the output format that will be saved to database,
    sent to Telegram, and displayed in web UI.
    """
    # Metadata
    timestamp: datetime
    symbol: str
    timeframe: str
    strategy_name: str

    # Signal details
    direction: str  # "LONG" or "SHORT"
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float  # 0.0 to 1.0

    # Risk metrics (calculated)
    risk_pips: float
    reward_pips: float
    risk_reward_ratio: float

    # Additional info
    notes: str
    current_price: float

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    def __str__(self) -> str:
        """Human-readable string representation."""
        return (
            f"\n{'='*70}\n"
            f"📊 TRADING SIGNAL - {self.direction}\n"
            f"{'='*70}\n"
            f"Strategy: {self.strategy_name}\n"
            f"Symbol: {self.symbol} | Timeframe: {self.timeframe}\n"
            f"Time: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            f"\n💰 Price Levels:\n"
            f"   Entry: ${self.entry_price:.2f}\n"
            f"   Stop Loss: ${self.stop_loss:.2f}\n"
            f"   Take Profit: ${self.take_profit:.2f}\n"
            f"   Current Price: ${self.current_price:.2f}\n"
            f"\n📈 Risk Management:\n"
            f"   Risk: {self.risk_pips:.1f} pips\n"
            f"   Reward: {self.reward_pips:.1f} pips\n"
            f"   R:R Ratio: 1:{self.risk_reward_ratio:.2f}\n"
            f"   Confidence: {self.confidence*100:.1f}%\n"
            f"\n📝 Notes: {self.notes}\n"
            f"{'='*70}\n"
        )


class SignalValidator:
    """
    Validates signals before publishing to prevent bad trades.

    Validation rules:
    - All price levels must be valid numbers
    - Stop loss must be in correct direction
    - Take profit must be in correct direction
    - R:R ratio must be acceptable (>= 1.5)
    - Entry price must be reasonable (within 5% of current price)
    - No duplicate signals (same direction within 4 hours)
    """

    def __init__(
        self,
        min_rr_ratio: float = 1.5,
        max_entry_deviation: float = 0.05,  # 5%
        duplicate_window_hours: int = 4
    ):
        self.min_rr_ratio = min_rr_ratio
        self.max_entry_deviation = max_entry_deviation
        self.duplicate_window_hours = duplicate_window_hours
        self.recent_signals: List[ValidatedSignal] = []

    def validate(
        self,
        signal: StrategySignal,
        current_price: float,
        symbol: str,
        timeframe: str
    ) -> Optional[ValidatedSignal]:
        """
        Validate a signal from the strategy.

        Args:
            signal: Raw signal from strategy
            current_price: Current market price
            symbol: Trading symbol
            timeframe: Candle timeframe

        Returns:
            ValidatedSignal if valid, None otherwise
        """
        # Check basic validity
        if not self._is_valid_signal(signal):
            logger.warning(f"Invalid signal structure: {signal}")
            return None

        # Calculate risk metrics
        direction_str = "LONG" if signal.direction == TradeDirection.LONG else "SHORT"

        if signal.direction == TradeDirection.LONG:
            risk_pips = (signal.entry_price - signal.stop_loss) * 10
            reward_pips = (signal.take_profit - signal.entry_price) * 10
        else:
            risk_pips = (signal.stop_loss - signal.entry_price) * 10
            reward_pips = (signal.entry_price - signal.take_profit) * 10

        # Validate risk metrics
        if risk_pips <= 0:
            logger.warning(f"Invalid risk: {risk_pips:.2f} pips. Stop loss in wrong direction.")
            return None

        if reward_pips <= 0:
            logger.warning(f"Invalid reward: {reward_pips:.2f} pips. Take profit in wrong direction.")
            return None

        rr_ratio = reward_pips / risk_pips

        if rr_ratio < self.min_rr_ratio:
            logger.warning(
                f"Poor R:R ratio: 1:{rr_ratio:.2f} (minimum: 1:{self.min_rr_ratio}). "
                f"Rejecting signal."
            )
            return None

        # Validate entry price is reasonable
        entry_deviation = abs(signal.entry_price - current_price) / current_price
        if entry_deviation > self.max_entry_deviation:
            logger.warning(
                f"Entry price ${signal.entry_price:.2f} is {entry_deviation*100:.1f}% "
                f"away from current price ${current_price:.2f}. Rejecting signal."
            )
            return None

        # Check for duplicates
        if self._is_duplicate(direction_str, signal.time):
            logger.info(
                f"Duplicate signal detected ({direction_str} within "
                f"{self.duplicate_window_hours}h). Skipping."
            )
            return None

        # Create validated signal
        validated = ValidatedSignal(
            timestamp=pd.Timestamp(signal.time),
            symbol=symbol,
            timeframe=timeframe,
            strategy_name=signal.signal_name,
            direction=direction_str,
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            confidence=signal.confidence,
            risk_pips=risk_pips,
            reward_pips=reward_pips,
            risk_reward_ratio=rr_ratio,
            notes=signal.notes,
            current_price=current_price
        )

        # Add to recent signals
        self.recent_signals.append(validated)

        # Keep only recent signals (last 24 hours)
        cutoff = pd.Timestamp.now(tz=validated.timestamp.tz) - pd.Timedelta(hours=24)
        self.recent_signals = [
            s for s in self.recent_signals
            if s.timestamp > cutoff
        ]

        logger.info(f"✅ Signal validated: {direction_str} @ ${signal.entry_price:.2f}")

        return validated

    def _is_valid_signal(self, signal: StrategySignal) -> bool:
        """Check if signal has all required fields."""
        try:
            assert signal.entry_price > 0
            assert signal.stop_loss > 0
            assert signal.take_profit > 0
            assert signal.direction in [TradeDirection.LONG, TradeDirection.SHORT]
            assert 0 <= signal.confidence <= 1
            return True
        except (AssertionError, AttributeError):
            return False

    def _is_duplicate(self, direction: str, signal_time: datetime) -> bool:
        """Check if similar signal was recently generated."""
        cutoff = pd.Timestamp(signal_time) - pd.Timedelta(hours=self.duplicate_window_hours)

        for recent in self.recent_signals:
            if recent.direction == direction and recent.timestamp > cutoff:
                return True

        return False


class RealtimeSignalGenerator:
    """
    Real-time signal generator service.

    This is the main orchestrator that:
    1. Connects to data feed
    2. Waits for candle closes
    3. Runs strategy analysis
    4. Validates signals
    5. Publishes to subscribers
    """

    def __init__(
        self,
        data_feed: RealtimeDataFeed,
        strategy: Optional[GoldStrategy] = None,
        validator: Optional[SignalValidator] = None,
        lookback_periods: int = 200
    ):
        """
        Initialize signal generator.

        Args:
            data_feed: Data feed instance
            strategy: Trading strategy (default: GoldStrategy with momentum only)
            validator: Signal validator (default: SignalValidator)
            lookback_periods: Number of candles to fetch for indicators
        """
        self.data_feed = data_feed
        self.lookback_periods = lookback_periods

        # Initialize strategy (Momentum Equilibrium only by default)
        if strategy is None:
            self.strategy = GoldStrategy()
            # Disable all rules except momentum_equilibrium
            for rule_name in self.strategy.rules_enabled.keys():
                self.strategy.rules_enabled[rule_name] = False
            self.strategy.rules_enabled['momentum_equilibrium'] = True
            logger.info("✅ Strategy initialized: Momentum Equilibrium only")
        else:
            self.strategy = strategy

        # Initialize validator
        self.validator = validator or SignalValidator()

        # Subscribers for signal publishing
        self.subscribers: List[Callable[[ValidatedSignal], None]] = []

        # State
        self.is_running = False
        self.total_candles_processed = 0
        self.total_signals_generated = 0

    def add_subscriber(self, callback: Callable[[ValidatedSignal], None]):
        """
        Add a subscriber to receive signals.

        Example:
            def save_to_db(signal: ValidatedSignal):
                # Save signal to database
                pass

            generator.add_subscriber(save_to_db)
        """
        self.subscribers.append(callback)

        # Get subscriber name (handle both functions and class instances)
        if hasattr(callback, '__name__'):
            name = callback.__name__
        elif hasattr(callback, '__class__'):
            name = callback.__class__.__name__
        else:
            name = str(callback)

        logger.info(f"Added subscriber: {name}")

    def _publish_signal(self, signal: ValidatedSignal):
        """Publish signal to all subscribers."""
        logger.info(f"📢 Publishing signal to {len(self.subscribers)} subscriber(s)")

        for subscriber in self.subscribers:
            try:
                subscriber(signal)
            except Exception as e:
                logger.error(f"Subscriber {subscriber.__name__} failed: {e}", exc_info=True)

    def generate_signal(self, df: pd.DataFrame) -> Optional[ValidatedSignal]:
        """
        Generate and validate a signal from latest candle data.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            ValidatedSignal if signal generated and validated, None otherwise
        """
        current_idx = len(df) - 1

        # Run strategy evaluation
        logger.debug(f"Evaluating strategy at index {current_idx}")
        signal = self.strategy.evaluate(df, current_idx)

        if signal is None:
            logger.debug("No signal triggered")
            return None

        logger.info(f"🎯 Signal triggered: {signal.signal_name}")

        # Get current price
        current_price = df['close'].iloc[-1]

        # Validate signal
        validated = self.validator.validate(
            signal=signal,
            current_price=current_price,
            symbol=self.data_feed.symbol,
            timeframe=self.data_feed.timeframe
        )

        if validated:
            self.total_signals_generated += 1

        return validated

    def run_once(self) -> Optional[ValidatedSignal]:
        """
        Run signal generation once (fetch latest data and check for signal).

        Returns:
            ValidatedSignal if generated, None otherwise
        """
        if not self.data_feed.is_connected:
            raise ConnectionError("Data feed not connected. Call connect() first.")

        # Fetch latest candles
        logger.debug(f"Fetching latest {self.lookback_periods} candles...")
        df = self.data_feed.get_latest_candles(count=self.lookback_periods)

        if df.empty:
            logger.warning("No data returned from data feed")
            return None

        self.total_candles_processed += 1

        logger.info(
            f"📊 Candle close at {df.index[-1]} | "
            f"Close: ${df['close'].iloc[-1]:.2f}"
        )

        # Generate signal
        signal = self.generate_signal(df)

        if signal:
            # Print signal
            print(signal)

            # Publish to subscribers
            self._publish_signal(signal)

        return signal

    def start(self, max_iterations: Optional[int] = None):
        """
        Start continuous signal generation loop.

        Args:
            max_iterations: Maximum iterations (for testing). None = infinite
        """
        if not self.data_feed.is_connected:
            logger.info("Connecting to data feed...")
            if not self.data_feed.connect():
                raise ConnectionError("Failed to connect to data feed")

        self.is_running = True
        iteration = 0

        logger.info("=" * 70)
        logger.info("🚀 REAL-TIME SIGNAL GENERATOR STARTED")
        logger.info("=" * 70)
        logger.info(f"Symbol: {self.data_feed.symbol}")
        logger.info(f"Timeframe: {self.data_feed.timeframe}")
        logger.info(f"Strategy: Momentum Equilibrium")
        logger.info(f"Subscribers: {len(self.subscribers)}")
        logger.info("=" * 70)

        try:
            while self.is_running:
                # Check iteration limit
                if max_iterations and iteration >= max_iterations:
                    logger.info(f"Reached max iterations ({max_iterations})")
                    break

                iteration += 1

                # Run signal generation
                self.run_once()

                # Wait for next candle close
                logger.info(f"\n⏳ Waiting for next {self.data_feed.timeframe} candle close...")
                self.data_feed.wait_for_candle_close(check_interval=60)

        except KeyboardInterrupt:
            logger.info("\n⏹️  Stopped by user")
        except Exception as e:
            logger.error(f"❌ Fatal error: {e}", exc_info=True)
        finally:
            self.stop()

    def stop(self):
        """Stop signal generation and disconnect."""
        self.is_running = False

        logger.info("\n" + "=" * 70)
        logger.info("📊 SIGNAL GENERATOR STATISTICS")
        logger.info("=" * 70)
        logger.info(f"Total candles processed: {self.total_candles_processed}")
        logger.info(f"Total signals generated: {self.total_signals_generated}")

        if self.total_candles_processed > 0:
            signal_rate = (self.total_signals_generated / self.total_candles_processed) * 100
            logger.info(f"Signal generation rate: {signal_rate:.1f}%")

        logger.info("=" * 70)

        if self.data_feed.is_connected:
            logger.info("Disconnecting from data feed...")
            self.data_feed.disconnect()


# ==================== TEST AND EXAMPLE ====================

if __name__ == "__main__":
    """
    Test the signal generator with Yahoo Finance data.

    This will:
    1. Connect to Yahoo Finance
    2. Fetch XAUUSD 4H candles
    3. Generate signal (if any)
    4. Print signal details
    """
    print("=" * 70)
    print("🧪 TESTING REAL-TIME SIGNAL GENERATOR")
    print("=" * 70)

    # Create data feed
    print("\n1. Creating Yahoo Finance data feed...")
    feed = create_datafeed(feed_type="yahoo", timeframe="4H")

    # Connect
    print("\n2. Connecting...")
    if not feed.connect():
        print("❌ Connection failed!")
        exit(1)

    # Create signal generator
    print("\n3. Creating signal generator...")
    generator = RealtimeSignalGenerator(data_feed=feed)

    # Add a test subscriber
    def print_subscriber(signal: ValidatedSignal):
        """Test subscriber that just prints the signal."""
        logger.info(f"📨 Subscriber received: {signal.direction} @ ${signal.entry_price:.2f}")

    generator.add_subscriber(print_subscriber)

    # Run once
    print("\n4. Running signal generation (once)...")
    signal = generator.run_once()

    if signal:
        print(f"\n✅ Signal generated!")
        print(signal)
    else:
        print("\n⚠️  No signal at this time")
        print("   (This is normal - signals are rare)")

    # Show stats
    print("\n5. Statistics:")
    print(f"   Candles processed: {generator.total_candles_processed}")
    print(f"   Signals generated: {generator.total_signals_generated}")

    # Cleanup
    print("\n6. Cleaning up...")
    generator.stop()

    print("\n" + "=" * 70)
    print("✅ TEST COMPLETE!")
    print("=" * 70)
    print("\nTo run continuously:")
    print("   generator.start()")
    print("\nTo run with limit:")
    print("   generator.start(max_iterations=10)")

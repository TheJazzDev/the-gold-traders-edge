"""
Logger Subscriber

Logs all validated signals to a dedicated file with full details.
"""

import logging
from pathlib import Path
from datetime import datetime


class LoggerSubscriber:
    """
    Subscriber that logs signals to a dedicated file.

    Features:
    - Dedicated signals.log file
    - Full signal details logged
    - Timestamped entries
    - Structured format for easy parsing
    - Rotation support (optional)
    """

    def __init__(self, log_file: str = "signals.log", log_level: int = logging.INFO):
        """
        Initialize logger subscriber.

        Args:
            log_file: Path to log file (default: signals.log)
            log_level: Logging level (default: INFO)
        """
        self.log_file = Path(log_file)

        # Create dedicated logger for signals
        self.logger = logging.getLogger("signals")
        self.logger.setLevel(log_level)

        # Remove existing handlers to avoid duplicates
        self.logger.handlers.clear()

        # Create file handler
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setLevel(log_level)

        # Create formatter with detailed information
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)

        # Add handler
        self.logger.addHandler(file_handler)

        # Also add console handler for immediate feedback
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        self.logger.info(f"✅ LoggerSubscriber initialized: {self.log_file}")

    def __call__(self, signal):
        """
        Receive and log signal.

        This method is called by the signal generator when a new signal is published.

        Args:
            signal: ValidatedSignal instance
        """
        try:
            self.log_signal(signal)
        except Exception as e:
            self.logger.error(f"Failed to log signal: {e}", exc_info=True)

    def log_signal(self, signal):
        """
        Log signal with full details.

        Args:
            signal: ValidatedSignal instance
        """
        # Create separator for readability
        self.logger.info("=" * 70)
        self.logger.info(f"📊 NEW TRADING SIGNAL - {signal.direction}")
        self.logger.info("=" * 70)

        # Log metadata
        self.logger.info(f"Strategy: {signal.strategy_name}")
        self.logger.info(f"Symbol: {signal.symbol}")
        self.logger.info(f"Timeframe: {signal.timeframe}")
        self.logger.info(f"Timestamp: {signal.timestamp.strftime('%Y-%m-%d %H:%M:%S %Z')}")

        # Log price levels
        self.logger.info("")
        self.logger.info("💰 PRICE LEVELS:")
        self.logger.info(f"   Entry Price:    ${signal.entry_price:.2f}")
        self.logger.info(f"   Stop Loss:      ${signal.stop_loss:.2f}")
        self.logger.info(f"   Take Profit:    ${signal.take_profit:.2f}")
        self.logger.info(f"   Current Price:  ${signal.current_price:.2f}")

        # Log risk metrics
        self.logger.info("")
        self.logger.info("📈 RISK MANAGEMENT:")
        self.logger.info(f"   Risk:           {signal.risk_pips:.1f} pips")
        self.logger.info(f"   Reward:         {signal.reward_pips:.1f} pips")
        self.logger.info(f"   R:R Ratio:      1:{signal.risk_reward_ratio:.2f}")
        self.logger.info(f"   Confidence:     {signal.confidence*100:.1f}%")

        # Log notes
        if signal.notes:
            self.logger.info("")
            self.logger.info(f"📝 NOTES: {signal.notes}")

        self.logger.info("=" * 70)
        self.logger.info("")

    def log_event(self, event_type: str, message: str, level: int = logging.INFO):
        """
        Log a custom event.

        Args:
            event_type: Type of event (e.g., "CANDLE_CLOSE", "ERROR")
            message: Event message
            level: Logging level
        """
        self.logger.log(level, f"[{event_type}] {message}")

    def close(self):
        """Close all handlers."""
        for handler in self.logger.handlers:
            handler.close()
        self.logger.handlers.clear()


if __name__ == "__main__":
    """Test logger subscriber."""
    from signals.realtime_generator import ValidatedSignal
    import pandas as pd

    print("=" * 70)
    print("🧪 TESTING LOGGER SUBSCRIBER")
    print("=" * 70)

    # Create subscriber
    print("\n1. Creating logger subscriber...")
    subscriber = LoggerSubscriber(log_file="test_signals.log")

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
        notes="Test signal for logger subscriber",
        current_price=2650.50
    )

    # Log signal
    print("\n3. Logging signal...")
    subscriber.log_signal(test_signal)

    # Log custom event
    print("\n4. Logging custom event...")
    subscriber.log_event("CANDLE_CLOSE", "4H candle closed at $2650.50")

    # Create another signal (SHORT)
    print("\n5. Logging SHORT signal...")
    test_signal_short = ValidatedSignal(
        timestamp=pd.Timestamp.now(),
        symbol="XAUUSD",
        timeframe="4H",
        strategy_name="Momentum Equilibrium",
        direction="SHORT",
        entry_price=2680.00,
        stop_loss=2695.30,
        take_profit=2649.40,
        confidence=0.60,
        risk_pips=153.0,
        reward_pips=306.0,
        risk_reward_ratio=2.0,
        notes="Test SHORT signal",
        current_price=2680.00
    )
    subscriber.log_signal(test_signal_short)

    # Check log file
    print("\n6. Checking log file...")
    log_path = Path("test_signals.log")
    if log_path.exists():
        line_count = len(log_path.read_text().splitlines())
        print(f"   ✅ Log file created: {log_path}")
        print(f"   Lines written: {line_count}")
    else:
        print("   ❌ Log file not found!")

    # Cleanup
    subscriber.close()

    print("\n" + "=" * 70)
    print("✅ LOGGER SUBSCRIBER TEST COMPLETE!")
    print("=" * 70)
    print(f"\nLog file: {log_path.absolute()}")

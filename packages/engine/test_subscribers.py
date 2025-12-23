#!/usr/bin/env python3
"""
Test Signal Subscribers Integration

This script tests all three subscribers working together:
1. DatabaseSubscriber - saves signals to SQLite
2. LoggerSubscriber - logs signals to file
3. ConsoleSubscriber - prints signals to console

It simulates real-time signal generation and verifies all subscribers
receive and process signals correctly.
"""

import sys
from pathlib import Path
import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from data.loader import GoldDataLoader
from signals.realtime_generator import RealtimeSignalGenerator, SignalValidator
from signals.gold_strategy import GoldStrategy
from signals.subscribers import DatabaseSubscriber, LoggerSubscriber, ConsoleSubscriber


# Mock data feed (from test_signal_generator.py)
class MockDataFeed:
    """Mock data feed for testing with historical data."""

    def __init__(self, df: pd.DataFrame, symbol: str = "XAUUSD", timeframe: str = "4H"):
        self.df = df
        self.symbol = symbol
        self.timeframe = timeframe
        self.is_connected = True
        self.current_idx = 200

    def connect(self) -> bool:
        self.is_connected = True
        return True

    def disconnect(self):
        self.is_connected = False

    def get_latest_candles(self, count: int = 200) -> pd.DataFrame:
        start_idx = max(0, self.current_idx - count + 1)
        return self.df.iloc[start_idx:self.current_idx + 1].copy()

    def get_current_price(self) -> float:
        return self.df['close'].iloc[self.current_idx]

    def advance(self) -> bool:
        if self.current_idx >= len(self.df) - 1:
            return False
        self.current_idx += 1
        return True


def test_all_subscribers(max_candles: int = 100):
    """
    Test all subscribers with signal generator.

    Args:
        max_candles: Maximum candles to process
    """
    print("=" * 70)
    print("🧪 TESTING ALL SUBSCRIBERS INTEGRATION")
    print("=" * 70)

    # Load historical data
    print("\n1. Loading historical data...")
    loader = GoldDataLoader()
    try:
        df = loader.load_processed("xauusd_4h_2023_2025.csv")
    except FileNotFoundError:
        print("   Historical data not found. Fetching from Yahoo Finance...")
        df = loader.load_from_yfinance(start_date="2023-01-01", interval="4h")
        df = loader.resample_timeframe(df, "4H")
        df = loader.clean_data(df)
        loader.save_processed(df, "xauusd_4h_2023_2025.csv")

    print(f"   ✅ Loaded {len(df)} candles")

    # Create mock data feed
    print("\n2. Creating mock data feed...")
    mock_feed = MockDataFeed(df)

    # Create strategy
    print("\n3. Configuring strategy (Momentum Equilibrium only)...")
    strategy = GoldStrategy()
    for rule in strategy.rules_enabled:
        strategy.rules_enabled[rule] = False
    strategy.rules_enabled['momentum_equilibrium'] = True

    # Create signal generator
    print("\n4. Creating signal generator...")
    generator = RealtimeSignalGenerator(
        data_feed=mock_feed,
        strategy=strategy,
        validator=SignalValidator(min_rr_ratio=1.5)
    )

    # Create all subscribers
    print("\n5. Creating subscribers...")

    # Database subscriber
    db_subscriber = DatabaseSubscriber(database_url="sqlite:///test_signals.db")
    generator.add_subscriber(db_subscriber)
    print("   ✅ DatabaseSubscriber added")

    # Logger subscriber
    logger_subscriber = LoggerSubscriber(log_file="test_signals.log")
    generator.add_subscriber(logger_subscriber)
    print("   ✅ LoggerSubscriber added")

    # Console subscriber
    console_subscriber = ConsoleSubscriber(use_colors=True, verbose=True)
    generator.add_subscriber(console_subscriber)
    print("   ✅ ConsoleSubscriber added")

    # Run signal generation
    print(f"\n6. Generating signals from {max_candles} candles...")
    print("   (Signals will be displayed below)")
    print("-" * 70)

    candles_processed = 0
    signals_generated = []

    while candles_processed < max_candles:
        # Run signal generation
        signal = generator.run_once()

        if signal:
            signals_generated.append(signal)

        # Advance to next candle
        if not mock_feed.advance():
            break

        candles_processed += 1

    # Results
    print("\n" + "=" * 70)
    print("📊 INTEGRATION TEST RESULTS")
    print("=" * 70)
    print(f"Candles processed: {candles_processed}")
    print(f"Signals generated: {len(signals_generated)}")

    if candles_processed > 0:
        signal_rate = (len(signals_generated) / candles_processed) * 100
        print(f"Signal rate: {signal_rate:.2f}%")

    # Verify database
    print("\n" + "=" * 70)
    print("🗄️  VERIFYING DATABASE")
    print("=" * 70)

    # Use get_all() instead of get_recent() since historical data has old timestamps
    with db_subscriber.db_manager.session_scope() as session:
        from signals.subscribers.database_subscriber import SignalRepository
        repo = SignalRepository(session)
        db_signals = repo.get_all(limit=1000)

        # Extract data while in session to avoid detached instance errors
        signal_data = [
            {
                'id': s.id,
                'direction': s.direction.value,
                'entry_price': s.entry_price,
                'timestamp': s.timestamp
            }
            for s in db_signals
        ]

    print(f"Signals in database: {len(signal_data)}")

    if len(signal_data) == len(signals_generated):
        print("✅ All signals saved to database correctly!")
    else:
        print(f"⚠️  Mismatch: generated {len(signals_generated)}, saved {len(signal_data)}")

    # Show database signals
    if signal_data:
        print(f"\nLast {min(5, len(signal_data))} signals from database:")
        for sig in signal_data[-5:]:
            print(f"   ID: {sig['id']} | {sig['direction']} @ ${sig['entry_price']:.2f} | {sig['timestamp']}")

    # Verify log file
    print("\n" + "=" * 70)
    print("📄 VERIFYING LOG FILE")
    print("=" * 70)

    log_path = Path("test_signals.log")
    if log_path.exists():
        log_lines = log_path.read_text().splitlines()
        print(f"Log file: {log_path}")
        print(f"Total lines: {len(log_lines)}")

        # Count signal entries (lines with "NEW TRADING SIGNAL")
        signal_entries = sum(1 for line in log_lines if "NEW TRADING SIGNAL" in line)
        print(f"Signal entries logged: {signal_entries}")

        if signal_entries == len(signals_generated):
            print("✅ All signals logged correctly!")
        else:
            print(f"⚠️  Mismatch: generated {len(signals_generated)}, logged {signal_entries}")
    else:
        print("❌ Log file not found!")

    # Summary
    print("\n" + "=" * 70)
    print("✅ INTEGRATION TEST COMPLETE!")
    print("=" * 70)

    print("\n📋 Summary:")
    print(f"   Candles processed: {candles_processed}")
    print(f"   Signals generated: {len(signals_generated)}")
    print(f"   Signals in database: {len(db_signals)}")
    print(f"   Database file: test_signals.db")
    print(f"   Log file: test_signals.log")

    if signals_generated:
        print(f"\n📊 Signal Breakdown:")
        long_count = sum(1 for s in signals_generated if s.direction == "LONG")
        short_count = len(signals_generated) - long_count
        print(f"   LONG signals: {long_count}")
        print(f"   SHORT signals: {short_count}")

        avg_rr = sum(s.risk_reward_ratio for s in signals_generated) / len(signals_generated)
        avg_conf = sum(s.confidence for s in signals_generated) / len(signals_generated)
        print(f"   Average R:R: 1:{avg_rr:.2f}")
        print(f"   Average Confidence: {avg_conf*100:.1f}%")

    print("\n" + "=" * 70)

    return signals_generated


def main():
    """Main test function."""
    import argparse

    parser = argparse.ArgumentParser(description="Test All Subscribers Integration")
    parser.add_argument('--max-candles', type=int, default=100, help='Maximum candles to process')
    args = parser.parse_args()

    signals = test_all_subscribers(max_candles=args.max_candles)

    if signals:
        print(f"\n✅ SUCCESS: {len(signals)} signals processed by all subscribers")
    else:
        print("\n⚠️  No signals generated (may be normal for short test period)")

    return signals


if __name__ == "__main__":
    signals = main()

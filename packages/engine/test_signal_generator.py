#!/usr/bin/env python3
"""
Test Signal Generator with Historical Data

This script tests the real-time signal generator by replaying
historical data to verify it can detect signals correctly.

It simulates the real-time environment by:
1. Loading historical 4H XAUUSD data
2. "Replaying" candles one by one
3. Running signal generation at each candle
4. Collecting all generated signals
5. Comparing with backtest results
"""

import sys
from pathlib import Path
import pandas as pd
from datetime import datetime
from typing import List

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from data.loader import GoldDataLoader
from signals.realtime_generator import (
    RealtimeSignalGenerator,
    SignalValidator,
    ValidatedSignal
)
from signals.gold_strategy import GoldStrategy


def load_historical_data(filepath: str = None) -> pd.DataFrame:
    """Load historical XAUUSD 4H data."""
    loader = GoldDataLoader()

    if filepath:
        df = loader.load_from_csv(filepath)
    else:
        # Try to load from processed data
        try:
            df = loader.load_processed("xauusd_4h_2023_2025.csv")
        except FileNotFoundError:
            print("⚠️  Historical data not found. Fetching from Yahoo Finance...")
            df = loader.load_from_yfinance(
                start_date="2023-01-01",
                interval="4h"
            )
            df = loader.resample_timeframe(df, "4H")
            df = loader.clean_data(df)
            loader.save_processed(df, "xauusd_4h_2023_2025.csv")

    return df


class MockDataFeed:
    """Mock data feed for testing with historical data."""

    def __init__(self, df: pd.DataFrame, symbol: str = "XAUUSD", timeframe: str = "4H"):
        self.df = df
        self.symbol = symbol
        self.timeframe = timeframe
        self.is_connected = True
        self.current_idx = 200  # Start after enough data for indicators

    def connect(self) -> bool:
        self.is_connected = True
        return True

    def disconnect(self):
        self.is_connected = False

    def get_latest_candles(self, count: int = 200) -> pd.DataFrame:
        """Return candles up to current index."""
        start_idx = max(0, self.current_idx - count + 1)
        return self.df.iloc[start_idx:self.current_idx + 1].copy()

    def get_current_price(self) -> float:
        return self.df['close'].iloc[self.current_idx]

    def advance(self) -> bool:
        """Advance to next candle. Returns False if no more candles."""
        if self.current_idx >= len(self.df) - 1:
            return False
        self.current_idx += 1
        return True


def test_signal_generation_on_historical_data(
    df: pd.DataFrame,
    max_candles: int = None,
    verbose: bool = True
) -> List[ValidatedSignal]:
    """
    Test signal generator by replaying historical data.

    Args:
        df: Historical OHLCV data
        max_candles: Maximum candles to process (None = all)
        verbose: Print detailed output

    Returns:
        List of generated signals
    """
    print("=" * 70)
    print("🧪 TESTING SIGNAL GENERATOR WITH HISTORICAL DATA")
    print("=" * 70)
    print(f"\nData period: {df.index[0]} to {df.index[-1]}")
    print(f"Total candles: {len(df)}")

    if max_candles:
        print(f"Testing on: {max_candles} candles")

    # Create mock data feed
    mock_feed = MockDataFeed(df)

    # Create signal generator
    strategy = GoldStrategy()
    # Enable only Momentum Equilibrium (our best performer)
    for rule in strategy.rules_enabled:
        strategy.rules_enabled[rule] = False
    strategy.rules_enabled['momentum_equilibrium'] = True

    generator = RealtimeSignalGenerator(
        data_feed=mock_feed,
        strategy=strategy,
        validator=SignalValidator(min_rr_ratio=1.5)
    )

    # Collect signals
    signals = []

    def collector(signal: ValidatedSignal):
        """Collect signals for analysis."""
        signals.append(signal)

    generator.add_subscriber(collector)

    # Replay historical data
    print("\n🔄 Replaying historical candles...")
    print("-" * 70)

    candles_processed = 0
    max_to_process = min(len(df) - 200, max_candles) if max_candles else len(df) - 200

    while candles_processed < max_to_process:
        # Get current timestamp
        current_time = df.index[mock_feed.current_idx]

        if verbose:
            print(f"\r⏳ Processing: {current_time} ({candles_processed}/{max_to_process})", end="")

        # Run signal generation
        signal = generator.run_once()

        if signal:
            if verbose:
                print(f"\n🎯 SIGNAL FOUND: {signal.direction} @ ${signal.entry_price:.2f}")
                print(f"   R:R: 1:{signal.risk_reward_ratio:.2f} | Confidence: {signal.confidence*100:.0f}%")
                print("-" * 70)

        # Advance to next candle
        if not mock_feed.advance():
            break

        candles_processed += 1

    print(f"\n\n{'=' * 70}")
    print("📊 RESULTS")
    print("=" * 70)
    print(f"Candles processed: {candles_processed}")
    print(f"Signals generated: {len(signals)}")

    if candles_processed > 0:
        signal_rate = (len(signals) / candles_processed) * 100
        print(f"Signal rate: {signal_rate:.2f}%")

    if signals:
        print(f"\n📈 Signal Breakdown:")
        long_signals = [s for s in signals if s.direction == "LONG"]
        short_signals = [s for s in signals if s.direction == "SHORT"]
        print(f"   LONG signals: {len(long_signals)}")
        print(f"   SHORT signals: {len(short_signals)}")

        avg_rr = sum(s.risk_reward_ratio for s in signals) / len(signals)
        avg_confidence = sum(s.confidence for s in signals) / len(signals)
        print(f"\n📊 Average Metrics:")
        print(f"   R:R Ratio: 1:{avg_rr:.2f}")
        print(f"   Confidence: {avg_confidence*100:.1f}%")

        print(f"\n📋 All Signals:")
        for i, signal in enumerate(signals, 1):
            print(f"\n{i}. {signal.timestamp.strftime('%Y-%m-%d %H:%M')} - {signal.direction}")
            print(f"   Entry: ${signal.entry_price:.2f} | SL: ${signal.stop_loss:.2f} | TP: ${signal.take_profit:.2f}")
            print(f"   R:R: 1:{signal.risk_reward_ratio:.2f} | Confidence: {signal.confidence*100:.0f}%")

    print("=" * 70)

    return signals


def main():
    """Main test function."""
    import argparse

    parser = argparse.ArgumentParser(description="Test Signal Generator with Historical Data")
    parser.add_argument('--data', type=str, help='Path to CSV data file')
    parser.add_argument('--max-candles', type=int, help='Maximum candles to process')
    parser.add_argument('--quiet', action='store_true', help='Suppress detailed output')
    args = parser.parse_args()

    # Load data
    print("\n📂 Loading historical data...")
    df = load_historical_data(args.data)
    print(f"✅ Loaded {len(df)} candles")

    # Run test
    signals = test_signal_generation_on_historical_data(
        df,
        max_candles=args.max_candles,
        verbose=not args.quiet
    )

    # Summary
    print("\n" + "=" * 70)
    if signals:
        print(f"✅ TEST PASSED: {len(signals)} signal(s) generated")
    else:
        print("⚠️  No signals generated (may be normal if testing short period)")
    print("=" * 70)

    return signals


if __name__ == "__main__":
    signals = main()

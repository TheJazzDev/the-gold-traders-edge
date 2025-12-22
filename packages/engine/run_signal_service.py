#!/usr/bin/env python3
"""
Run Signal Service - CLI Script

Simple command-line interface to start the signal generation service.

Usage:
    python run_signal_service.py                    # Run with default settings
    python run_signal_service.py --datafeed mt5     # Use MT5 data feed
    python run_signal_service.py --test 10          # Run for 10 iterations (testing)
    python run_signal_service.py --config           # Show configuration
"""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from services.signal_service import SignalService, ServiceConfig


def show_config():
    """Display current configuration."""
    config = ServiceConfig()

    print("\n" + "=" * 70)
    print("⚙️  SIGNAL SERVICE CONFIGURATION")
    print("=" * 70)
    print("\n📋 Current Settings:")

    for key, value in config.to_dict().items():
        print(f"   {key:20s}: {value}")

    print("\n" + "=" * 70)
    print("\n💡 To change configuration, set environment variables:")
    print("\nExample:")
    print("   export DATAFEED_TYPE=mt5")
    print("   export TIMEFRAME=1H")
    print("   export MIN_RR_RATIO=2.0")
    print("   export ENABLE_CONSOLE=false")
    print("\nAvailable variables:")
    print("   - DATAFEED_TYPE: yahoo, mt5, metaapi")
    print("   - SYMBOL: XAUUSD, XAGUSD, etc.")
    print("   - TIMEFRAME: 1H, 4H, 1D")
    print("   - DATABASE_URL: SQLite or PostgreSQL URL")
    print("   - ENABLE_DATABASE: true/false")
    print("   - ENABLE_LOGGER: true/false")
    print("   - ENABLE_CONSOLE: true/false")
    print("   - MIN_RR_RATIO: Minimum risk:reward ratio (e.g., 1.5)")
    print("   - HEARTBEAT_INTERVAL: Minutes between status logs (e.g., 5)")
    print("\n" + "=" * 70 + "\n")


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description='Gold Trader\'s Edge - Signal Service',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Run with default settings (Yahoo Finance, 4H, XAUUSD)
  python run_signal_service.py

  # Run with MT5 data feed
  DATAFEED_TYPE=mt5 python run_signal_service.py

  # Run for testing (10 candles)
  python run_signal_service.py --test 10

  # Show current configuration
  python run_signal_service.py --config

  # Disable console output
  ENABLE_CONSOLE=false python run_signal_service.py
        '''
    )

    parser.add_argument(
        '--config', '-c',
        action='store_true',
        help='Show configuration and exit'
    )

    parser.add_argument(
        '--test', '-t',
        type=int,
        metavar='N',
        help='Run for N iterations (for testing)'
    )

    parser.add_argument(
        '--datafeed',
        type=str,
        choices=['yahoo', 'mt5', 'metaapi'],
        help='Override datafeed type'
    )

    parser.add_argument(
        '--symbol',
        type=str,
        help='Override trading symbol (e.g., XAUUSD)'
    )

    parser.add_argument(
        '--timeframe',
        type=str,
        choices=['1H', '4H', '1D'],
        help='Override timeframe'
    )

    args = parser.parse_args()

    # Show config if requested
    if args.config:
        show_config()
        return

    # Apply command-line overrides
    import os
    if args.datafeed:
        os.environ['DATAFEED_TYPE'] = args.datafeed
    if args.symbol:
        os.environ['SYMBOL'] = args.symbol
    if args.timeframe:
        os.environ['TIMEFRAME'] = args.timeframe

    # Create and start service
    print("\n" + "=" * 70)
    print("📊 GOLD TRADER'S EDGE - REAL-TIME SIGNAL SERVICE")
    print("=" * 70)

    if args.test:
        print(f"\n🧪 RUNNING IN TEST MODE ({args.test} iterations)\n")
    else:
        print("\n💡 Press Ctrl+C to stop the service gracefully\n")

    service = SignalService()

    try:
        service.start(max_iterations=args.test)
    except KeyboardInterrupt:
        print("\n\n⏹️  Service stopped by user")
    except Exception as e:
        print(f"\n\n❌ Service failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

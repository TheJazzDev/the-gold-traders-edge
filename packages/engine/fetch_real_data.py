#!/usr/bin/env python3
"""
Fetch Real XAUUSD Data Script
Downloads historical gold price data from Yahoo Finance and saves it for backtesting.

Usage:
    python fetch_real_data.py                           # Default: 4h data from 2015 to now
    python fetch_real_data.py --timeframe 1h            # Fetch 1-hour data
    python fetch_real_data.py --start 2020-01-01        # Custom start date
    python fetch_real_data.py --years 5                 # Last 5 years
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from data.loader import GoldDataLoader


def parse_args():
    parser = argparse.ArgumentParser(description='Fetch Real XAUUSD Data from Yahoo Finance')
    parser.add_argument('--timeframe', type=str, default='4h',
                        help='Timeframe: 1h, 4h, 1d (default: 4h)')
    parser.add_argument('--start', type=str,
                        help='Start date (YYYY-MM-DD). Default: 2015-01-01 or based on --years')
    parser.add_argument('--end', type=str,
                        help='End date (YYYY-MM-DD). Default: today')
    parser.add_argument('--years', type=int,
                        help='Number of years back from today (overrides --start)')
    parser.add_argument('--output', type=str,
                        help='Output filename (auto-generated if not specified)')
    parser.add_argument('--clean', action='store_true',
                        help='Clean and validate data (remove outliers)')
    return parser.parse_args()


def main():
    args = parse_args()

    print("=" * 70)
    print("📈 XAUUSD REAL DATA FETCHER")
    print("=" * 70)

    # Calculate date range
    if args.end:
        end_date = args.end
    else:
        end_date = datetime.now().strftime("%Y-%m-%d")

    if args.years:
        start_date = (datetime.now() - timedelta(days=args.years * 365)).strftime("%Y-%m-%d")
    elif args.start:
        start_date = args.start
    else:
        start_date = "2015-01-01"  # Default: ~10 years of data

    print(f"\n⚙️  Configuration:")
    print(f"   Ticker: GC=F (Gold Futures)")
    print(f"   Timeframe: {args.timeframe}")
    print(f"   Period: {start_date} to {end_date}")

    # Initialize loader
    loader = GoldDataLoader()

    # Map timeframe to yfinance interval
    tf_map = {
        '1m': '1m', '5m': '5m', '15m': '15m', '30m': '30m',
        '1h': '1h', '2h': '2h', '4h': '4h',
        '1d': '1d', '1D': '1d',
        '1wk': '1wk', '1w': '1wk'
    }
    interval = tf_map.get(args.timeframe, args.timeframe)

    # Check Yahoo Finance limitations
    intraday_timeframes = ['1m', '5m', '15m', '30m', '1h', '2h', '4h']
    max_days_intraday = 730  # Yahoo limit for intraday

    date_diff = (datetime.strptime(end_date, "%Y-%m-%d") -
                 datetime.strptime(start_date, "%Y-%m-%d")).days

    if interval in intraday_timeframes and date_diff > max_days_intraday:
        print(f"\n⚠️  Warning: Yahoo Finance limits intraday data to {max_days_intraday} days")
        print(f"   You requested {date_diff} days.")
        print(f"   Adjusting start date to {max_days_intraday} days ago...")
        start_date = (datetime.strptime(end_date, "%Y-%m-%d") -
                     timedelta(days=max_days_intraday)).strftime("%Y-%m-%d")
        print(f"   New start date: {start_date}")

    # Fetch data
    print(f"\n🌐 Fetching data from Yahoo Finance...")
    try:
        df = loader.load_from_yfinance(
            start_date=start_date,
            end_date=end_date,
            interval=interval
        )

        if df.empty:
            print("\n❌ No data returned from Yahoo Finance!")
            print("\nPossible issues:")
            print("  - Timeframe may be too granular for the date range")
            print("  - Yahoo Finance API may be temporarily unavailable")
            print("  - Date range may be invalid")
            sys.exit(1)

        print(f"\n✅ Successfully fetched {len(df)} candles")
        print(f"   Date range: {df.index[0]} to {df.index[-1]}")
        print(f"   Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")

    except ImportError:
        print("\n❌ Error: yfinance not installed!")
        print("\nPlease install it:")
        print("  pip install yfinance")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error fetching data: {e}")
        sys.exit(1)

    # Clean data if requested
    if args.clean:
        print(f"\n🧹 Cleaning data...")
        original_len = len(df)
        df = loader.clean_data(df)
        removed = original_len - len(df)
        if removed > 0:
            print(f"   Removed {removed} invalid candles")
        else:
            print(f"   Data already clean!")

    # Generate output filename
    if args.output:
        filename = args.output
    else:
        # Auto-generate: xauusd_4h_2015_2024.csv
        start_year = datetime.strptime(start_date, "%Y-%m-%d").year
        end_year = datetime.strptime(end_date, "%Y-%m-%d").year
        filename = f"xauusd_{args.timeframe}_{start_year}_{end_year}.csv"

    # Save data
    print(f"\n💾 Saving data...")
    filepath = loader.save_processed(df, filename)

    # Summary
    print("\n" + "=" * 70)
    print("✅ DATA FETCH COMPLETE!")
    print("=" * 70)
    print(f"\n📊 Summary:")
    print(f"   Total Candles: {len(df)}")
    print(f"   File: {filepath}")
    print(f"   File Size: {filepath.stat().st_size / 1024:.1f} KB")

    print(f"\n🚀 Next Steps:")
    print(f"   Run backtest with this data:")
    print(f"   python run_backtest.py --data {filepath}")
    print()

    return df


if __name__ == "__main__":
    main()

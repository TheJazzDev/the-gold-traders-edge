#!/usr/bin/env python3
"""
Fetch historical XAUUSD candles from MetaAPI — a dev-only tool for sourcing
enough intraday history to tune strategies below 1H. Yahoo Finance
(fetch_real_data.py) only gives ~60 days for intraday intervals; MetaAPI
reads directly from the broker's own terminal, which typically retains
much more.

Requires `pip install metaapi-cloud-sdk` (NOT part of packages/engine/requirements.txt
— this is for local tuning data only, not the live service's data feed,
which stays on Yahoo Finance per the Task 14 deployment decision).

Usage:
    # Check how much history is available without downloading/writing anything:
    python fetch_metaapi_history.py --timeframe 15m --discover

    # Fetch the full available range:
    python fetch_metaapi_history.py --timeframe 15m --output data/processed/xauusd_15m_<range>.csv
"""
import os
import sys
import asyncio
import argparse
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd


def validate_candles(candles):
    """Drop candles violating OHLC invariants (high >= max(open,close),
    low <= min(open,close)). Returns (valid_candles, dropped_count)."""
    valid = []
    dropped = 0
    for c in candles:
        if c['high'] >= max(c['open'], c['close']) and c['low'] <= min(c['open'], c['close']):
            valid.append(c)
        else:
            dropped += 1
    return valid, dropped


def candles_to_dataframe(candles):
    """Convert a list of MetaAPI candle dicts (fields: time, open, high,
    low, close, tickVolume) to the OHLCV DataFrame schema
    GoldDataLoader.load_from_csv() already reads: a 'Datetime'-named index
    and lowercase open/high/low/close/volume columns, sorted ascending,
    deduplicated by timestamp."""
    if not candles:
        return pd.DataFrame(
            columns=['open', 'high', 'low', 'close', 'volume'],
            index=pd.DatetimeIndex([], name='Datetime'),
        )
    df = pd.DataFrame(candles)
    df['time'] = pd.to_datetime(df['time'], utc=True)
    df = df.rename(columns={'tickVolume': 'volume'})
    df = df[['time', 'open', 'high', 'low', 'close', 'volume']]
    df = df.drop_duplicates(subset='time').sort_values('time')
    df = df.set_index('time')
    df.index.name = 'Datetime'
    return df


async def fetch_all_candles(account, symbol, timeframe, page_limit=1000):
    """
    Page backward from now via account.get_historical_candles(start_time=...),
    which returns candles strictly before start_time, until the API returns
    an empty page or a page shorter than page_limit (both signal we've hit
    the start of available history). Returns a flat list of raw candle
    dicts — still needs validate_candles()/candles_to_dataframe().
    """
    all_candles = []
    cursor = datetime.now(timezone.utc)
    while True:
        page = await account.get_historical_candles(
            symbol=symbol, timeframe=timeframe, start_time=cursor, limit=page_limit
        )
        if not page:
            break
        all_candles.extend(page)
        if len(page) < page_limit:
            break
        cursor = min(pd.to_datetime(c['time'], utc=True) for c in page).to_pydatetime()
    return all_candles


async def main_async(args):
    from metaapi_cloud_sdk import MetaApi

    token = os.getenv('METAAPI_TOKEN')
    account_id = os.getenv('METAAPI_ACCOUNT_ID')
    if not token or not account_id:
        print("METAAPI_TOKEN and METAAPI_ACCOUNT_ID must be set (see packages/engine/.env)")
        sys.exit(1)

    api = MetaApi(token)
    account = api.metatrader_account_api.get_account(account_id)
    await account.deploy()
    await account.wait_connected()

    candles = await fetch_all_candles(account, args.symbol, args.timeframe)
    if not candles:
        print("No historical candles returned — this account/broker may not "
              "retain history for this symbol/timeframe.")
        sys.exit(1)

    times = pd.to_datetime([c['time'] for c in candles], utc=True)
    days = (times.max() - times.min()).total_seconds() / 86400
    print(f"Fetched {len(candles)} raw candles: {times.min()} to {times.max()} ({days:.1f} days)")

    if args.discover:
        print("(--discover set: not validating/writing a CSV)")
        return

    valid, dropped = validate_candles(candles)
    if dropped:
        print(f"Dropped {dropped} candles failing OHLC validation")
    df = candles_to_dataframe(valid)
    print(f"After validation/dedup: {len(df)} candles, {df.index.min()} to {df.index.max()}")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path)
    print(f"Wrote {output_path}")


def main():
    parser = argparse.ArgumentParser(description='Fetch XAUUSD historical candles from MetaAPI (dev-only)')
    parser.add_argument('--timeframe', required=True, help='MetaAPI timeframe string, e.g. "15m"')
    parser.add_argument('--symbol', default='XAUUSD')
    parser.add_argument('--discover', action='store_true',
                         help='Report available history depth and exit without writing a CSV')
    parser.add_argument('--output', type=str,
                         help='Output CSV path (required unless --discover)')
    args = parser.parse_args()
    if not args.discover and not args.output:
        parser.error('--output is required unless --discover is set')
    asyncio.run(main_async(args))


if __name__ == '__main__':
    main()

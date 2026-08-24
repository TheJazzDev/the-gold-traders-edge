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


if __name__ == '__main__':
    print("This script isn't fully wired up yet — see Task 6 of "
          "docs/superpowers/plans/2026-08-24-15m-strategy-tuning.md")
    sys.exit(1)

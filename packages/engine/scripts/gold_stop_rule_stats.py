#!/usr/bin/env python3
"""
Where should gold's live stop rule sit? The same measurement that set the
ARLB rule (strategy-ledger.md "2026-10-24"), for Order Block Retest.

Runs the committed tuned_configs/1h.json with live's gates, rules and
143-market-hour expiry over the committed CSV plus fresh Yahoo candles,
then reports the losing streaks, drawdown and rolling-window results a
live run should be judged against. Nothing is swept.

Usage (from packages/engine):
    venv/bin/python scripts/gold_stop_rule_stats.py --out gold_trades.json
"""
import argparse
import contextlib
import io
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ENGINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(ENGINE / 'src'))

from backtesting.engine import TradeDirection, TradeStatus  # noqa: E402
from backtesting.live_parity import live_gated_strategy_func, run_on_window  # noqa: E402
from data.loader import GoldDataLoader  # noqa: E402
from data.realtime_feed import YahooFinanceDataFeed  # noqa: E402
from signals.gold_strategy import GoldStrategy  # noqa: E402
import tune_strategy as gold_tuner  # noqa: E402

CSV = ENGINE / 'data/processed/xauusd_1h_2024_2026.csv'
TUNED = ENGINE / 'tuned_configs/1h.json'
YAHOO_CANDLES = 3000  # comfortably more than CSV end -> today
RESOLVED = (TradeStatus.CLOSED_TP, TradeStatus.CLOSED_SL)
WINDOWS = (12, 25, 30)


def _utc_naive(df):
    df = df.copy()
    df.index = pd.to_datetime(df.index, utc=True).tz_localize(None)
    return df[~df.index.duplicated(keep='last')].sort_index()


def load_candles():
    with contextlib.redirect_stdout(io.StringIO()):
        history = _utc_naive(GoldDataLoader().load_from_csv(str(CSV)))
        feed = YahooFinanceDataFeed(symbol='XAUUSD', timeframe='1h', lookback_periods=YAHOO_CANDLES)
        feed.connect()
        fresh = _utc_naive(feed.get_latest_candles(count=YAHOO_CANDLES))
    fresh = fresh[fresh.index > history.index[-1]]
    gap = fresh.index[0] - history.index[-1] if len(fresh) else None
    return pd.concat([history, fresh[history.columns.intersection(fresh.columns)]]), gap


def run_trades(df, tuned):
    strategy = GoldStrategy(config=tuned['config'])
    for name in strategy.rules_enabled:
        strategy.rules_enabled[name] = name in tuned['enabled_rules']
    warmup = gold_tuner.slice_warmup_candles(strategy.config)
    with contextlib.redirect_stdout(io.StringIO()):
        result = run_on_window(df, df.index[warmup], live_gated_strategy_func(strategy),
                               warmup=warmup, expiry_hours=tuned['expiry_hours'])
    rows = []
    for t in result.trades:
        if t.status not in RESOLVED:
            continue
        sign = 1 if t.direction == TradeDirection.LONG else -1
        r = sign * (t.exit_price - t.entry_price) / abs(t.entry_price - t.stop_loss)
        rows.append({'entry': str(t.entry_time), 'exit': str(t.exit_time), 'r': round(float(r), 4)})
    return sorted(rows, key=lambda row: row['exit'])


def streaks(rs):
    found, current = [], 0
    for r in rs:
        if r < 0:
            current += 1
        else:
            if current:
                found.append(current)
            current = 0
    if current:
        found.append(current)
    return found


def max_drawdown(rs):
    curve = np.cumsum(rs)
    return float((np.maximum.accumulate(np.concatenate([[0.0], curve]))[1:] - curve).max())


def report(rows, label):
    rs = [row['r'] for row in rows]
    if not rs:
        return
    wins = sum(r > 0 for r in rs)
    found = streaks(rs)
    print(f'\n{label}: {len(rs)} trades, WR {wins / len(rs):.1%}, net {sum(rs):+.1f}R, '
          f'max streak {max(found)}, max drawdown {max_drawdown(rs):.1f}R')
    print('  streaks >= 8:', sorted((s for s in found if s >= 8), reverse=True))
    for size in WINDOWS:
        if len(rs) < size:
            continue
        nets = np.convolve(rs, np.ones(size), 'valid')
        low = (np.percentile(nets, 1), np.percentile(nets, 5), np.percentile(nets, 50))
        print(f'  {size}-trade windows: p1 {low[0]:+.1f}R, p5 {low[1]:+.1f}R, '
              f'median {low[2]:+.1f}R, worst {nets.min():+.1f}R')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', default=None)
    args = parser.parse_args()

    tuned = json.loads(TUNED.read_text())
    train_end = pd.Timestamp(tuned['data_range']['train_end']).tz_localize(None)
    df, gap = load_candles()
    print(f'Candles: {len(df)}, {df.index[0]} -> {df.index[-1]} (stitch gap {gap})')

    rows = run_trades(df, tuned)
    csv_end = str(pd.read_csv(CSV, usecols=[0]).iloc[-1, 0])
    report(rows, 'All')
    report([r for r in rows if pd.Timestamp(r['entry']) < train_end], 'Train')
    report([r for r in rows if pd.Timestamp(r['entry']) >= train_end], 'Test + fresh')
    report([r for r in rows if r['entry'] >= '2026-09-04'], 'Live period (from 2026-09-04)')
    report([r for r in rows if r['entry'] >= '2026-10-03'], 'Since parity fix (from 2026-10-03)')
    print(f'\nCSV ends {csv_end}')

    if args.out:
        Path(args.out).write_text(json.dumps(rows, indent=1))


if __name__ == '__main__':
    main()

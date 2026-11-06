#!/usr/bin/env python3
"""
Can the live strategies make money after trading costs, and how much?

Replays each live worker's committed config with live's gates and expiry over
its CSV plus fresh Yahoo candles, then charges a round-trip cost per trade.
Nothing is swept. Out-of-sample means entries after that config's train_end.

Costs are charged as cost / stop distance in R. That slightly understates
them: a real spread also moves stops and targets. Overnight swap isn't charged.

Usage (from packages/engine):
    venv/bin/python scripts/profit_expectation.py --trades trades.json
    venv/bin/python scripts/profit_expectation.py --trades trades.json --reuse
"""
import argparse
import contextlib
import io
import json
import sys
from multiprocessing import Pool
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
from signals.forex_session_strategy import ForexSessionStrategy  # noqa: E402
from signals.gold_strategy import GoldStrategy  # noqa: E402
import tune_forex_session_strategy as forex_tuner  # noqa: E402
import tune_strategy as gold_tuner  # noqa: E402

MARKETS = {
    'XAUUSD': ('data/processed/xauusd_1h_2024_2026.csv', 'tuned_configs/1h.json'),
    'EURUSD': ('data/processed/eurusd_1h_2023_2026.csv', 'tuned_configs/eurusd_1h.json'),
    'GBPUSD': ('data/processed/gbpusd_1h_2023_2026.csv', 'tuned_configs/gbpusd_1h.json'),
}
# Round-trip spread + commission + slippage, in price units.
COSTS = {
    'none': {'XAUUSD': 0.0, 'EURUSD': 0.0, 'GBPUSD': 0.0},
    'low': {'XAUUSD': 0.30, 'EURUSD': 0.00007, 'GBPUSD': 0.00010},
    'mid': {'XAUUSD': 0.50, 'EURUSD': 0.00012, 'GBPUSD': 0.00018},
    'high': {'XAUUSD': 1.00, 'EURUSD': 0.00020, 'GBPUSD': 0.00030},
}
BOOKS = {'all': ('XAUUSD', 'EURUSD', 'GBPUSD'), 'arlb': ('EURUSD', 'GBPUSD'), 'gold': ('XAUUSD',)}
RESOLVED = (TradeStatus.CLOSED_TP, TradeStatus.CLOSED_SL)
YAHOO_CANDLES = 3000
RNG = np.random.default_rng(20261106)


def _utc_naive(df):
    df = df.copy()
    df.index = pd.to_datetime(df.index, utc=True).tz_localize(None)
    return df[~df.index.duplicated(keep='last')].sort_index()


def replay(symbol):
    csv, config_file = MARKETS[symbol]
    tuned = json.loads((ENGINE / config_file).read_text())
    with contextlib.redirect_stdout(io.StringIO()):
        history = _utc_naive(GoldDataLoader().load_from_csv(str(ENGINE / csv)))
        feed = YahooFinanceDataFeed(symbol=symbol, timeframe='1h', lookback_periods=YAHOO_CANDLES)
        feed.connect()
        fresh = _utc_naive(feed.get_latest_candles(count=YAHOO_CANDLES))
    fresh = fresh[fresh.index > history.index[-1]]
    df = pd.concat([history, fresh[history.columns.intersection(fresh.columns)]])

    if symbol == 'XAUUSD':
        strategy = GoldStrategy(config=tuned['config'])
        for name in strategy.rules_enabled:
            strategy.rules_enabled[name] = name in tuned['enabled_rules']
        warmup = gold_tuner.slice_warmup_candles(strategy.config)
    else:
        strategy = ForexSessionStrategy(config=tuned['config'])
        warmup = forex_tuner.slice_warmup_candles(strategy.config)

    with contextlib.redirect_stdout(io.StringIO()):
        result = run_on_window(df, df.index[warmup], live_gated_strategy_func(strategy),
                               warmup=warmup, expiry_hours=tuned['expiry_hours'])

    train_end = pd.Timestamp(tuned['data_range']['train_end']).tz_localize(None)
    rows = []
    for t in result.trades:
        if t.status not in RESOLVED:
            continue
        sign = 1 if t.direction == TradeDirection.LONG else -1
        risk = abs(t.entry_price - t.stop_loss)
        rows.append({'symbol': symbol, 'entry': str(t.entry_time), 'exit': str(t.exit_time),
                     'r': float(sign * (t.exit_price - t.entry_price) / risk), 'risk': float(risk),
                     'oos': bool(t.entry_time >= train_end)})
    return rows


def frame(rows, cost):
    df = pd.DataFrame(rows)
    df['exit'] = pd.to_datetime(df['exit'])
    df['net'] = df['r'] - df['symbol'].map(COSTS[cost]) / df['risk']
    return df


def expectancy_ci(values):
    picks = RNG.integers(0, len(values), size=(5000, len(values)))
    means = values[picks].mean(axis=1)
    return np.percentile(means, 2.5), np.percentile(means, 97.5)


def profit_factor(values):
    loss = -values[values < 0].sum()
    return values[values > 0].sum() / loss if loss else float('inf')


def line(df, label):
    values = df['net'].to_numpy()
    low, high = expectancy_ci(values)
    weeks = max((df['exit'].max() - df['exit'].min()).days / 7, 1)
    print(f'  {label:<22} n={len(df):>3} WR {(values > 0).mean():.1%} PF {profit_factor(values):.2f} '
          f'{values.mean():+.3f}R/trade (95% {low:+.3f}..{high:+.3f}) '
          f'{values.sum():+.1f}R {len(df) / weeks:.1f}/wk')


def simulate_year(df, runs=5000):
    """Resample whole weeks, so same-day EURUSD/GBPUSD moves stay together."""
    start = df['exit'].min().normalize()
    span = int((df['exit'].max() - start).days / 7) + 1
    weekly = np.zeros(span)
    np.add.at(weekly, ((df['exit'] - start).dt.days // 7).to_numpy(), df['net'].to_numpy())
    paths = weekly[RNG.integers(0, span, size=(runs, 52))]
    curve = paths.cumsum(axis=1)
    peaks = np.maximum.accumulate(np.concatenate([np.zeros((runs, 1)), curve], axis=1), axis=1)[:, 1:]
    return curve[:, -1], (peaks - curve).max(axis=1), weekly.mean()


def book_report(rows, cost):
    df = frame(rows, cost)
    print(f'\n=== Cost: {cost} ===')
    for name, symbols in BOOKS.items():
        book = df[df['symbol'].isin(symbols)]
        line(book[book['oos']], f'{name} out-of-sample')
        line(book, f'{name} full')
    for name, symbols in BOOKS.items():
        book = df[df['symbol'].isin(symbols) & df['oos']]
        year, drawdown, weekly = simulate_year(book)
        print(f'  {name} 1-year sim (OOS): median {np.median(year):+.1f}R, '
              f'p5 {np.percentile(year, 5):+.1f}R, p95 {np.percentile(year, 95):+.1f}R, '
              f'losing year {np.mean(year < 0):.0%}, median DD {np.median(drawdown):.1f}R, '
              f'p95 DD {np.percentile(drawdown, 95):.1f}R, {weekly:+.2f}R/wk')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--trades', required=True)
    parser.add_argument('--reuse', action='store_true')
    args = parser.parse_args()

    path = Path(args.trades)
    if args.reuse:
        rows = json.loads(path.read_text())
    else:
        with Pool(3) as pool:
            rows = sum(pool.map(replay, MARKETS), [])
        path.write_text(json.dumps(rows))

    for cost in COSTS:
        book_report(rows, cost)


if __name__ == '__main__':
    main()

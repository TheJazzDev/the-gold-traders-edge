#!/usr/bin/env python3
"""
Would USDJPY or AUDUSD add anything to the live book?

Runs ARLB on each pair with the exact EURUSD config and live's gates. Nothing
is tuned, and the pairs were chosen before any result was seen. Yahoo's 1h
history is shorter than the saved CSVs, so every book is cut to the new pairs'
start date. Test means entries after EURUSD's own train_end.

A pair passes only if, at mid costs on the test slice:
  1. its net R is positive,
  2. fewer than 30% of its trades share an entry day and USD direction with an
     EURUSD or GBPUSD trade (GBPUSD itself is 44%),
  3. adding it raises the book's net R / max drawdown.

Usage (from packages/engine):
    venv/bin/python scripts/new_pair_test.py --trades trades.json [--reuse]
"""
import argparse
import contextlib
import io
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

ENGINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(ENGINE / 'src'))
sys.path.insert(0, str(ENGINE / 'scripts'))

import profit_expectation as base  # noqa: E402
from backtesting.engine import TradeDirection  # noqa: E402
from backtesting.live_parity import live_gated_strategy_func, run_on_window  # noqa: E402
from signals.forex_session_strategy import ForexSessionStrategy  # noqa: E402
import tune_forex_session_strategy as forex_tuner  # noqa: E402

NEW_PAIRS = {'USDJPY': 'USDJPY=X', 'AUDUSD': 'AUDUSD=X'}
# Round-trip cost in price units. EURUSD-like pips: JPY pip is 0.01.
NEW_COSTS = {
    'none': {'USDJPY': 0.0, 'AUDUSD': 0.0},
    'low': {'USDJPY': 0.010, 'AUDUSD': 0.00009},
    'mid': {'USDJPY': 0.016, 'AUDUSD': 0.00014},
    'high': {'USDJPY': 0.025, 'AUDUSD': 0.00024},
}
# +1 when the trade is long USD. USDJPY is the only pair with USD as the base.
USD_SIDE = {'XAUUSD': -1, 'EURUSD': -1, 'GBPUSD': -1, 'AUDUSD': -1, 'USDJPY': 1}
MAX_OVERLAP = 0.30
LIVE_BOOK = ('XAUUSD', 'EURUSD', 'GBPUSD')


def fetch(ticker):
    raw = yf.Ticker(ticker).history(period='730d', interval='1h', auto_adjust=False)
    df = raw.rename(columns=str.lower)[['open', 'high', 'low', 'close', 'volume']]
    return base._utc_naive(df)


def replay_new(symbol, ticker, train_end):
    tuned = json.loads((ENGINE / 'tuned_configs/eurusd_1h.json').read_text())
    df = fetch(ticker)
    strategy = ForexSessionStrategy(config=tuned['config'])
    warmup = forex_tuner.slice_warmup_candles(strategy.config)
    with contextlib.redirect_stdout(io.StringIO()):
        result = run_on_window(df, df.index[warmup], live_gated_strategy_func(strategy),
                               warmup=warmup, expiry_hours=tuned['expiry_hours'])
    rows = []
    for t in result.trades:
        if t.status not in base.RESOLVED:
            continue
        sign = 1 if t.direction == TradeDirection.LONG else -1
        risk = abs(t.entry_price - t.stop_loss)
        rows.append({'symbol': symbol, 'entry': str(t.entry_time), 'exit': str(t.exit_time),
                     'r': float(sign * (t.exit_price - t.entry_price) / risk), 'risk': float(risk),
                     'direction': sign, 'oos': bool(t.entry_time >= train_end)})
    print(f'{symbol}: {len(df)} candles {df.index[0]} .. {df.index[-1]}, {len(rows)} trades', flush=True)
    return rows


def load(path, reuse):
    if reuse:
        return json.loads(path.read_text())
    tuned = json.loads((ENGINE / 'tuned_configs/eurusd_1h.json').read_text())
    train_end = pd.Timestamp(tuned['data_range']['train_end']).tz_localize(None)
    rows = sum((base.replay(s) for s in LIVE_BOOK), [])
    for symbol, ticker in NEW_PAIRS.items():
        rows += replay_new(symbol, ticker, train_end)
    path.write_text(json.dumps(rows))
    return rows


def net_frame(rows, cost):
    df = pd.DataFrame(rows)
    costs = {**base.COSTS[cost], **NEW_COSTS.get(cost, {})}
    df['entry'] = pd.to_datetime(df['entry'])
    df['exit'] = pd.to_datetime(df['exit'])
    df['net'] = df['r'] - df['symbol'].map(costs) / df['risk']
    df['usd'] = df['direction'] * df['symbol'].map(USD_SIDE)
    df['day'] = df['entry'].dt.normalize()
    return df


def max_drawdown(df):
    curve = df.sort_values('exit')['net'].cumsum().to_numpy()
    return float((np.maximum.accumulate(np.concatenate([[0.0], curve]))[1:] - curve).max())


def overlap(df, symbol):
    """Share of `symbol` trades with a same-day, same-USD-side EUR/GBP trade,
    and how often those pairs of trades ended on the same side of zero."""
    pair = df[df['symbol'] == symbol]
    other = df[df['symbol'].isin(('EURUSD', 'GBPUSD'))]
    joined = pair.merge(other, on=['day', 'usd'], suffixes=('', '_o'))
    shared = joined.drop_duplicates('entry')
    same = ((joined['net'] > 0) == (joined['net_o'] > 0)).mean() if len(joined) else float('nan')
    return len(shared) / len(pair) if len(pair) else 0.0, same, len(joined)


def book_line(label, df):
    net = df['net'].sum()
    drawdown = max_drawdown(df)
    ratio = net / drawdown if drawdown else float('inf')
    print(f'  {label:<24} n={len(df):>3} {net:+6.1f}R DD {drawdown:4.1f}R ratio {ratio:5.2f}')
    return ratio


def report(rows):
    start = net_frame(rows, 'mid').query("symbol in @NEW_PAIRS")['entry'].min()
    for cost in ('none', 'low', 'mid', 'high'):
        df = net_frame(rows, cost)
        df = df[df['entry'] >= start]
        print(f'\n=== Cost: {cost} ===')
        for symbol in (*NEW_PAIRS, 'EURUSD', 'GBPUSD'):
            for label, part in (('train', df[~df['oos']]), ('test', df[df['oos']])):
                base.line(part[part['symbol'] == symbol], f'{symbol} {label}')

    df = net_frame(rows, 'mid')
    df = df[df['entry'] >= start]
    test = df[df['oos']]
    print('\n=== Mid-cost book, test slice ===')
    live_ratio = book_line('live book', test[test['symbol'].isin(LIVE_BOOK)])
    print('=== Mid-cost book, train slice ===')
    book_line('live book', df[~df['oos'] & df['symbol'].isin(LIVE_BOOK)])

    print('\n=== Verdict ===')
    for symbol in NEW_PAIRS:
        share, same, pairs = overlap(test, symbol)
        added = test[test['symbol'].isin((*LIVE_BOOK, symbol))]
        ratio = book_line(f'live + {symbol}', added)
        book_line(f'live + {symbol} (train)', df[~df['oos'] & df['symbol'].isin((*LIVE_BOOK, symbol))])
        net = test.loc[test['symbol'] == symbol, 'net'].sum()
        checks = (net > 0, share < MAX_OVERLAP, ratio > live_ratio)
        print(f'  {symbol}: test net {net:+.1f}R; overlap {share:.0%} ({pairs} pairs, same result {same:.0%}); '
              f'ratio {ratio:.2f} vs {live_ratio:.2f}; {"PASS" if all(checks) else "FAIL"} {checks}')

    print('\n=== 1-year sim, mid cost, test slice ===')
    groups = {'live': LIVE_BOOK, **{f'live+{s}': (*LIVE_BOOK, s) for s in NEW_PAIRS},
              'live+both': (*LIVE_BOOK, *NEW_PAIRS)}
    for name, symbols in groups.items():
        year, drawdown, weekly = base.simulate_year(test[test['symbol'].isin(symbols)].copy())
        print(f'  {name:<12} median {np.median(year):+.1f}R, p5 {np.percentile(year, 5):+.1f}R, '
              f'losing {np.mean(year < 0):.0%}, p95 DD {np.percentile(drawdown, 95):.1f}R, {weekly:+.2f}R/wk')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--trades', required=True)
    parser.add_argument('--reuse', action='store_true')
    args = parser.parse_args()
    report(load(Path(args.trades), args.reuse))


if __name__ == '__main__':
    main()

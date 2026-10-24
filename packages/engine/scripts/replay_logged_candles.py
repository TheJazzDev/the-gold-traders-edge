#!/usr/bin/env python3
"""
Re-run the live strategy on the exact candles live evaluated (the CANDLES
log lines, see signals/candle_log.py), side by side with today's Yahoo
history for the same candle, and print where the inputs differ.

Usage (from packages/engine):
    railway logs --service the-gold-traders-edge \
        --since 2026-10-15T08:10:00Z --until 2026-10-15T08:20:00Z --lines 3000 > /tmp/live.log
    venv/bin/python scripts/replay_logged_candles.py /tmp/live.log --symbol XAUUSD

Older deployments' logs need the deployment id (`railway deployment list`)
as the first argument to `railway logs`.
"""
import argparse
import contextlib
import io
import json
import sys
from pathlib import Path

ENGINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(ENGINE / 'src'))

from backtesting.live_parity import live_gated_strategy_func  # noqa: E402
from data.realtime_feed import YahooFinanceDataFeed  # noqa: E402
from signals.candle_log import CANDLE_LOG_PREFIX, parse_candle_log  # noqa: E402
from signals.forex_session_strategy import ForexSessionStrategy  # noqa: E402
from signals.gold_strategy import GoldStrategy  # noqa: E402

WORKERS = {'XAUUSD': (GoldStrategy, '1h.json'),
           'GBPUSD': (ForexSessionStrategy, 'gbpusd_1h.json'),
           'EURUSD': (ForexSessionStrategy, 'eurusd_1h.json')}


def _strategy_func(symbol):
    strategy_class, config_file = WORKERS[symbol]
    tuned = json.loads((ENGINE / 'tuned_configs' / config_file).read_text())
    strategy = strategy_class(config=tuned['config'])
    if strategy_class is GoldStrategy:
        for name in strategy.rules_enabled:
            strategy.rules_enabled[name] = name == 'order_block_retest'
    return live_gated_strategy_func(strategy)


def _describe(signal):
    if signal is None:
        return 'no signal'
    return f"{signal.direction.name} entry {signal.entry_price:.5f} SL {signal.stop_loss:.5f}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('log_file')
    parser.add_argument('--symbol', default='XAUUSD', choices=sorted(WORKERS))
    args = parser.parse_args()

    frames = {}
    for line in Path(args.log_file).read_text().splitlines():
        if CANDLE_LOG_PREFIX not in line:
            continue
        symbol, _, df = parse_candle_log(line)
        if symbol == args.symbol:
            frames[df.index[-1]] = df  # the log prints each line twice; keep one
    if not frames:
        sys.exit(f"no {args.symbol} CANDLES lines in {args.log_file}")

    feed = YahooFinanceDataFeed(symbol=args.symbol, timeframe='1h', lookback_periods=2000)
    with contextlib.redirect_stdout(io.StringIO()):
        feed.connect()
        today = feed.get_latest_candles(count=2000)

    func = _strategy_func(args.symbol)
    for candle, live_df in sorted(frames.items()):
        with contextlib.redirect_stdout(io.StringIO()):
            live_signal = func(live_df, len(live_df) - 1)
        print(f"\n{candle}  live input → {_describe(live_signal)}")
        if candle not in today.index:
            print('  not in today\'s Yahoo history')
            continue
        today_df = today.loc[live_df.index[0]:candle]
        with contextlib.redirect_stdout(io.StringIO()):
            today_signal = func(today_df, len(today_df) - 1)
        print(f"  today's Yahoo → {_describe(today_signal)}")
        common = live_df.index.intersection(today_df.index)
        diff = (live_df.loc[common, ['open', 'high', 'low', 'close']]
                - today_df.loc[common, ['open', 'high', 'low', 'close']]).abs()
        changed = diff[diff.max(axis=1) > 1e-6]
        missing = len(live_df) - len(common)
        print(f"  candles revised since: {len(changed)}" + (f", missing today: {missing}" if missing else ''))
        for ts, row in changed.tail(10).iterrows():
            print(f"    {ts}  " + "  ".join(f"{c} Δ{row[c]:.5f}" for c in row.index if row[c] > 1e-6))


if __name__ == '__main__':
    main()

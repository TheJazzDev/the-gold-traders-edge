#!/usr/bin/env python3
"""
Replay the last N days through the backtest with live's configs, gates and
expiry, and compare trade by trade with what production published — the
same check the weekly report runs (services/weekly_parity.py), for any
window, from your machine.

Live signals and settings come from the production API; candles from the
same Yahoo feed live uses.

Usage (from packages/engine):
    venv/bin/python scripts/live_parity_replay.py --days 28
"""
import argparse
import contextlib
import io
import json
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

ENGINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(ENGINE / 'src'))

from data.realtime_feed import YahooFinanceDataFeed  # noqa: E402
from services.weekly_parity import ParityTarget, build_weekly_parity_text  # noqa: E402
from signals.forex_session_strategy import ForexSessionStrategy  # noqa: E402
from signals.gold_strategy import GoldStrategy  # noqa: E402

API = 'https://the-gold-traders-edge-production.up.railway.app'
WORKERS = [('XAUUSD', GoldStrategy, '1h.json'),
           ('GBPUSD', ForexSessionStrategy, 'gbpusd_1h.json'),
           ('EURUSD', ForexSessionStrategy, 'eurusd_1h.json')]


def _get(path):
    with urllib.request.urlopen(API + path, timeout=30) as resp:
        return json.load(resp)


def _targets(settings):
    targets = []
    for symbol, strategy_class, config_file in WORKERS:
        tuned = json.loads((ENGINE / 'tuned_configs' / config_file).read_text())
        strategy = strategy_class(config=tuned['config'])
        for name in strategy.rules_enabled:
            if strategy_class is GoldStrategy:
                strategy.rules_enabled[name] = name in settings['enabled_strategies']
            else:
                strategy.rules_enabled[name] = symbol in settings['enabled_forex_symbols']
        # Same lookback live derives in TimeframeWorker._run.
        gate = strategy.config.get('trend_lookback') or (
            strategy.config.get('lookback_candles', 0) + strategy.config.get('atr_period', 0))
        targets.append(ParityTarget(
            symbol=symbol, timeframe='1h', strategy=strategy,
            min_rr=float(settings['min_rr_ratio']), min_confidence=float(settings['min_confidence']),
            expiry_hours=tuned.get('expiry_hours', 48.0), warmup=max(200, gate + 50)))
    return targets


def _live_signals():
    rows = _get('/v1/signals/?limit=1000')['signals']
    return [SimpleNamespace(**{**r, 'timestamp': datetime.fromisoformat(r['timestamp'])}) for r in rows]


def _fetch(target, count):
    feed = YahooFinanceDataFeed(symbol=target.symbol, timeframe=target.timeframe, lookback_periods=count)
    with contextlib.redirect_stdout(io.StringIO()):
        feed.connect()
    return feed.get_latest_candles(count=count)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--days', type=int, default=7)
    args = parser.parse_args()

    settings = {s['key']: s['typed_value'] for s in _get('/v1/settings/')}
    with contextlib.redirect_stdout(io.StringIO()):
        text = build_weekly_parity_text(_targets(settings), _live_signals(), _fetch, days=args.days)
    print(text)


if __name__ == '__main__':
    main()

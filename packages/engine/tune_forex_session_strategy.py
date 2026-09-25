#!/usr/bin/env python3
"""
Train/test validation for ForexSessionStrategy — deliberately does NOT do a
parameter sweep. The gold research this session found that a full-dataset
sweep followed by picking the best-looking combo is a multiple-comparisons
trap: two of three new gold strategies looked strong after a sweep and
collapsed the moment a real held-out test set was checked (see
docs/superpowers/specs/strategy-ledger.md's methodology note). The one that
skipped the sweep and went straight to a real train/test split on sensible
default parameters reached its (also negative, in that case) conclusion
faster and more honestly.

Asian Range London Breakout already went through exactly that process as a
standalone prototype before being implemented as a real class — this script
formalizes that same validation (real 70/30 chronological split, default
parameters, both train and test reported) into a reusable pipeline and a
tuned_configs-style output artifact, without re-introducing a sweep.

Usage:
    python tune_forex_session_strategy.py --data data/processed/gbpusd_1h.csv --symbol GBPUSD
"""
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from data.loader import GoldDataLoader
from signals.forex_session_strategy import ForexSessionStrategy
from analysis.trend_gate import warmup_candles
from backtesting.engine import BacktestEngine
from backtesting.live_parity import (
    PRODUCTION_MIN_CONFIDENCE, PRODUCTION_MIN_RR, live_gated_strategy_func,
    resolved_stats, run_on_window,
)

MIN_TRAIN_TRADES = 15
MIN_TEST_TRADES = 5


def split_train_test(df, train_frac=0.7):
    split_idx = int(len(df) * train_frac)
    return df.iloc[:split_idx], df.iloc[split_idx:]


def slice_warmup_candles(config):
    """History before the test slice — the strategy's own gate, plus the
    trend gate's EMA window when it's on (live fetches the same)."""
    needed = config['lookback_candles'] + config['atr_period']
    if config.get('htf_trend_filter'):
        needed = max(needed, warmup_candles(config['trend_ema_period']))
    return needed + 50


def run_backtest(df, config, start=None):
    """Score only the trades live would publish (backtesting/live_parity.py).
    With `start`, earlier candles of `df` are warm-up history only."""
    strategy_func = live_gated_strategy_func(ForexSessionStrategy(config=config))
    if start is None:
        engine = BacktestEngine(initial_balance=10000, position_size_pct=2.0)
        result = engine.run(df, strategy_func, max_open_trades=1)
    else:
        result = run_on_window(df, start, strategy_func, warmup=slice_warmup_candles(config))
    return resolved_stats(result)


def passes_pf_gate(stats, min_trades):
    return stats['profit_factor'] > 1.0 and stats['total_trades'] >= min_trades


def main():
    parser = argparse.ArgumentParser(description='Validate ForexSessionStrategy on real train/test data')
    parser.add_argument('--data', type=str, required=True, help='Path to OHLCV CSV')
    parser.add_argument('--symbol', type=str, required=True, help='e.g. GBPUSD')
    parser.add_argument('--output', type=str, default=None)
    parser.add_argument('--train-frac', type=float, default=0.7)
    parser.add_argument('--htf-trend-filter', action='store_true',
                        help='Validate (and write) the config with the HTF trend gate on')
    args = parser.parse_args()

    output_path = args.output or str(
        Path(__file__).parent / 'tuned_configs' / f'{args.symbol.lower()}_1h.json'
    )

    loader = GoldDataLoader()
    df = loader.load_from_csv(args.data)
    train_df, test_df = split_train_test(df, train_frac=args.train_frac)

    print(f"Train: {len(train_df)} candles ({train_df.index[0]} to {train_df.index[-1]})")
    print(f"Test:  {len(test_df)} candles ({test_df.index[0]} to {test_df.index[-1]})")

    config = {**ForexSessionStrategy.DEFAULT_CONFIG, 'htf_trend_filter': args.htf_trend_filter}
    train_stats = run_backtest(train_df, config)
    test_stats = run_backtest(df, config, start=test_df.index[0])

    passed_train = passes_pf_gate(train_stats, MIN_TRAIN_TRADES)
    passed_test = passes_pf_gate(test_stats, MIN_TEST_TRADES)

    print(f"train: PF={train_stats['profit_factor']:.2f} trades={train_stats['total_trades']} "
          f"-> {'candidate' if passed_train else 'rejected'}")
    print(f"test:  PF={test_stats['profit_factor']:.2f} trades={test_stats['total_trades']} "
          f"-> {'ENABLED' if passed_train and passed_test else 'DISABLED'}")

    output = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'symbol': args.symbol,
        'timeframe': '1h',
        'strategy_class': 'ForexSessionStrategy',
        'data_range': {
            'start': str(df.index[0]),
            'end': str(df.index[-1]),
            'train_end': str(train_df.index[-1]),
        },
        'config': config,
        'live_gates': {
            'min_rr_ratio': PRODUCTION_MIN_RR,
            'min_confidence': PRODUCTION_MIN_CONFIDENCE,
            'max_open_trades': 1,
            'test_slice_warmup': 'strategy sees prior candles as history; trades only from train_end onward',
        },
        'enabled': passed_train and passed_test,
        'train': train_stats,
        'test': test_stats,
        'note': (
            "Default (untuned) parameters, deliberately not swept — see "
            "docs/superpowers/specs/2026-09-09-gbpusd-asian-range-breakout-design.md "
            "and strategy-ledger.md's methodology note on why a sweep was skipped."
        ),
    }

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\n✅ Wrote {output_path}")


if __name__ == '__main__':
    main()

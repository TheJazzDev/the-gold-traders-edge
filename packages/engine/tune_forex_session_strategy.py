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
from signals.forex_session_strategy import ForexSessionStrategy, create_strategy_function
from signals.realtime_generator import SignalValidator
from backtesting.engine import BacktestEngine, TradeStatus

PRODUCTION_MIN_RR = 1.5
MIN_TRAIN_TRADES = 15
MIN_TEST_TRADES = 5


def split_train_test(df, train_frac=0.7):
    split_idx = int(len(df) * train_frac)
    return df.iloc[:split_idx], df.iloc[split_idx:]


def _production_valid_strategy_func(strategy):
    """Matches tune_strategy.py's own gate — only score trades production
    would actually publish (risk>0, reward>0, rr >= PRODUCTION_MIN_RR)."""
    def strategy_func(df, idx):
        signal = strategy.evaluate(df, idx)
        if signal is None:
            return None
        risk_reward = SignalValidator.compute_risk_reward(signal)
        if risk_reward is None or not SignalValidator.meets_min_rr(risk_reward[2], PRODUCTION_MIN_RR):
            return None
        return signal
    return strategy_func


def resolved_stats(result):
    """Computed over resolved (CLOSED_TP/CLOSED_SL) trades only — excludes
    CLOSED_MANUAL force-closes, matching tune_strategy.py's own reasoning."""
    resolved = [t for t in result.trades if t.status in (TradeStatus.CLOSED_TP, TradeStatus.CLOSED_SL)]
    total_trades = len(resolved)
    if total_trades == 0:
        return {'profit_factor': 0.0, 'total_trades': 0, 'win_rate': 0.0, 'net_profit_pct': 0.0}
    winning = [t for t in resolved if t.pnl > 0]
    losing = [t for t in resolved if t.pnl <= 0]
    total_profit = sum(t.pnl for t in winning) if winning else 0
    total_loss = abs(sum(t.pnl for t in losing)) if losing else 0
    return {
        'profit_factor': total_profit / total_loss if total_loss > 0 else float('inf'),
        'total_trades': total_trades,
        'win_rate': len(winning) / total_trades * 100,
        'net_profit_pct': sum(t.pnl for t in resolved) / result.initial_balance * 100,
    }


def run_backtest(df, config):
    strategy = ForexSessionStrategy(config=config)
    strategy_func = _production_valid_strategy_func(strategy)
    engine = BacktestEngine(initial_balance=10000, position_size_pct=2.0)
    result = engine.run(df, strategy_func, max_open_trades=1)
    return resolved_stats(result)


def passes_pf_gate(stats, min_trades):
    return stats['profit_factor'] > 1.0 and stats['total_trades'] >= min_trades


def main():
    parser = argparse.ArgumentParser(description='Validate ForexSessionStrategy on real train/test data')
    parser.add_argument('--data', type=str, required=True, help='Path to OHLCV CSV')
    parser.add_argument('--symbol', type=str, required=True, help='e.g. GBPUSD')
    parser.add_argument('--output', type=str, default=None)
    parser.add_argument('--train-frac', type=float, default=0.7)
    args = parser.parse_args()

    output_path = args.output or str(
        Path(__file__).parent / 'tuned_configs' / f'{args.symbol.lower()}_1h.json'
    )

    loader = GoldDataLoader()
    df = loader.load_from_csv(args.data)
    train_df, test_df = split_train_test(df, train_frac=args.train_frac)

    print(f"Train: {len(train_df)} candles ({train_df.index[0]} to {train_df.index[-1]})")
    print(f"Test:  {len(test_df)} candles ({test_df.index[0]} to {test_df.index[-1]})")

    config = dict(ForexSessionStrategy.DEFAULT_CONFIG)
    train_stats = run_backtest(train_df, config)
    test_stats = run_backtest(test_df, config)

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

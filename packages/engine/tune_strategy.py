#!/usr/bin/env python3
"""
Grid-search tuning and train/test validation of GoldStrategy for the 1H
timeframe, using real historical data.

The 4H-tuned defaults were carried over unchanged when 1H support was
added, and were never re-validated on 1H's own price behavior. This script:

1. Splits real 1H OHLCV data chronologically 70/30 (train/test).
2. For each of the 5 rules, independently: starts from 1H-equivalent
   rescaled defaults (4x the 4H candle-count lookbacks, since 1H candles
   are 1/4 the duration of 4H candles), then does a one-pass coordinate
   search (vary one parameter at a time, keep whichever value improves
   train-slice profit factor) around that starting point.
3. Builds one shared config by taking the per-parameter median across all
   rules that passed a training-data profit-factor bar, then re-validates
   EVERY candidate rule against that final shared config on the held-out
   test slice (since in production all rules run with one shared config
   object) — a rule only ships enabled if it's still profitable on the
   test slice under the *final* shared config, not just its own
   individually-tuned one.
4. Computes an expiry window from the 95th percentile of trade durations
   (in hours) across all enabled rules' test-slice trades.

Usage:
    python tune_strategy.py --data data/processed/xauusd_1h_2024_2026.csv
"""
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from data.loader import GoldDataLoader
from signals.gold_strategy import GoldStrategy, create_strategy_function
from backtesting.engine import BacktestEngine, TradeStatus

RULES = [
    'momentum_equilibrium',
    'london_session_breakout',
    'golden_fibonacci',
    'ath_retest',
    'order_block_retest',
]

# 1H-equivalent starting points: candle-count lookbacks from the 4H-tuned
# DEFAULT_CONFIG in gold_strategy.py, scaled 4x (1H candles cover 1/4 the
# real time of 4H candles). Ratio/percentage params are left unscaled.
BASE_1H_CONFIG = {
    'fib_tolerance': 0.015,
    'swing_lookback': 20,
    'swing_min_strength': 2,
    'trend_lookback': 200,
    'strong_momentum_threshold': 0.02,
    'atr_period': 56,
    'default_rr_ratio': 2.0,
    'sl_buffer_atr': 0.3,
    'ema_fast': 36,
    'ema_slow': 84,
    'rsi_period': 56,
    'rsi_overbought': 70,
    'rsi_oversold': 30,
}

SEARCH_GRID = {
    'fib_tolerance': [0.010, 0.015, 0.020],
    'swing_lookback': [14, 20, 28],
    'trend_lookback': [140, 200, 260],
    'atr_period': [40, 56, 72],
    'default_rr_ratio': [1.5, 2.0, 2.5],
}

MIN_TRAIN_TRADES = 15
MIN_TEST_TRADES = 5


def split_train_test(df, train_frac=0.7):
    """Chronological split — train is the older `train_frac` of candles."""
    split_idx = int(len(df) * train_frac)
    return df.iloc[:split_idx], df.iloc[split_idx:]


def run_isolated_backtest(df, rule_name, config):
    """Run a backtest with only `rule_name` enabled. Returns (profit_factor, total_trades, result)."""
    strategy = GoldStrategy(config=config)
    for name in strategy.rules_enabled:
        strategy.rules_enabled[name] = False
    strategy.rules_enabled[rule_name] = True

    strategy_func = create_strategy_function(strategy)
    engine = BacktestEngine(initial_balance=10000, position_size_pct=2.0)
    result = engine.run(df, strategy_func, max_open_trades=1)
    return result.profit_factor, result.total_trades, result


def run_combined_backtest(df, rule_names, config):
    """Run a backtest with all of `rule_names` enabled together, one shared config."""
    strategy = GoldStrategy(config=config)
    for name in strategy.rules_enabled:
        strategy.rules_enabled[name] = name in rule_names

    strategy_func = create_strategy_function(strategy)
    engine = BacktestEngine(initial_balance=10000, position_size_pct=2.0)
    return engine.run(df, strategy_func, max_open_trades=1)


def tune_rule(train_df, rule_name):
    """One-pass coordinate search: vary one parameter at a time from the baseline."""
    current = dict(BASE_1H_CONFIG)
    best_pf, best_trades, _ = run_isolated_backtest(train_df, rule_name, current)
    if best_trades < MIN_TRAIN_TRADES:
        best_pf = 0.0

    for param, values in SEARCH_GRID.items():
        best_value_for_param = current[param]
        best_pf_for_param = best_pf
        for value in values:
            trial = dict(current)
            trial[param] = value
            pf, trades, _ = run_isolated_backtest(train_df, rule_name, trial)
            if trades >= MIN_TRAIN_TRADES and pf > best_pf_for_param:
                best_pf_for_param = pf
                best_value_for_param = value
        current[param] = best_value_for_param
        best_pf = best_pf_for_param

    return current


def validate_rule(df, rule_name, config):
    """Run `config` isolated to `rule_name` on `df`, returning (stats, trade_durations_hours)."""
    pf, trades, result = run_isolated_backtest(df, rule_name, config)
    closed = [t for t in result.trades if t.status != TradeStatus.OPEN]
    durations_hours = [
        (t.exit_time - t.entry_time).total_seconds() / 3600
        for t in closed if t.exit_time is not None
    ]
    stats = {
        'profit_factor': pf,
        'total_trades': trades,
        'win_rate': result.win_rate,
        'net_profit_pct': ((result.final_balance / result.initial_balance) - 1) * 100,
    }
    return stats, durations_hours


def passes_pf_gate(stats, min_trades):
    """A rule 'passes' a profitability gate if PF > 1.0 with enough trades to trust it."""
    return stats['profit_factor'] > 1.0 and stats['total_trades'] >= min_trades


def percentile(values, pct):
    """Linear-interpolation percentile, matching numpy's default method."""
    if not values:
        return 0.0
    ordered = sorted(values)
    k = (len(ordered) - 1) * (pct / 100)
    f = int(k)
    c = min(f + 1, len(ordered) - 1)
    if f == c:
        return ordered[f]
    return ordered[f] + (ordered[c] - ordered[f]) * (k - f)


def main():
    parser = argparse.ArgumentParser(description='Tune and validate GoldStrategy for 1H')
    parser.add_argument('--data', type=str, required=True, help='Path to 1H OHLCV CSV')
    parser.add_argument('--output', type=str, default='tuned_configs/1h.json')
    parser.add_argument('--train-frac', type=float, default=0.7)
    args = parser.parse_args()

    loader = GoldDataLoader()
    df = loader.load_from_csv(args.data)
    train_df, test_df = split_train_test(df, train_frac=args.train_frac)

    print(f"Train: {len(train_df)} candles ({train_df.index[0]} to {train_df.index[-1]})")
    print(f"Test:  {len(test_df)} candles ({test_df.index[0]} to {test_df.index[-1]})")

    validation = {}
    candidate_rules = []
    tuned_config_by_rule = {}

    for rule_name in RULES:
        print(f"\n=== Tuning {rule_name} ===")
        tuned_config = tune_rule(train_df, rule_name)
        tuned_config_by_rule[rule_name] = tuned_config

        train_stats, _ = validate_rule(train_df, rule_name, tuned_config)
        individual_test_stats, _ = validate_rule(test_df, rule_name, tuned_config)

        validation[rule_name] = {
            'train': train_stats,
            'test_individually_tuned': individual_test_stats,
            'config': tuned_config,
        }

        # Candidacy is gated on TRAIN-slice stats only. test_df is never used
        # to decide which rules feed the shared config — it stays untouched
        # until the final held-out validation below, so it's only used once.
        passed_individually = passes_pf_gate(train_stats, MIN_TRAIN_TRADES)
        print(
            f"  train: PF={train_stats['profit_factor']:.2f} trades={train_stats['total_trades']} "
            f"-> {'candidate' if passed_individually else 'rejected'}"
        )
        print(
            f"  test (own config, reporting only): PF={individual_test_stats['profit_factor']:.2f} "
            f"trades={individual_test_stats['total_trades']}"
        )
        if passed_individually:
            candidate_rules.append(rule_name)

    if candidate_rules:
        final_config = {}
        for param in BASE_1H_CONFIG:
            values = sorted(tuned_config_by_rule[r][param] for r in candidate_rules)
            final_config[param] = values[len(values) // 2]  # median
    else:
        final_config = dict(BASE_1H_CONFIG)

    # Re-validate every candidate under the FINAL shared config, since
    # production runs all enabled rules with one GoldStrategy config object.
    print("\n=== Re-validating candidates under the final shared config ===")
    enabled_rules = []
    all_test_durations = []
    final_validation = {}
    for rule_name in candidate_rules:
        stats, durations = validate_rule(test_df, rule_name, final_config)
        final_validation[rule_name] = stats
        passed = passes_pf_gate(stats, MIN_TEST_TRADES)
        print(f"  {rule_name}: PF={stats['profit_factor']:.2f} trades={stats['total_trades']} -> {'ENABLED' if passed else 'DISABLED'}")
        if passed:
            enabled_rules.append(rule_name)
            all_test_durations.extend(durations)

    expiry_hours = max(1, int(percentile(all_test_durations, 95)) + 1) if all_test_durations else 48

    combined_result = run_combined_backtest(test_df, enabled_rules, final_config) if enabled_rules else None

    output = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'symbol': 'XAUUSD',
        'timeframe': '1h',
        'data_range': {
            'start': str(df.index[0]),
            'end': str(df.index[-1]),
            'train_end': str(train_df.index[-1]),
        },
        'config': final_config,
        'enabled_rules': enabled_rules,
        'expiry_hours': expiry_hours,
        'per_rule_validation': validation,
        'final_shared_config_validation': final_validation,
        'combined_test_slice_result': {
            'total_trades': combined_result.total_trades,
            'win_rate': combined_result.win_rate,
            'profit_factor': combined_result.profit_factor,
            'net_profit_pct': ((combined_result.final_balance / combined_result.initial_balance) - 1) * 100,
        } if combined_result else None,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\n✅ Wrote {output_path}")
    print(f"Enabled rules: {enabled_rules}")
    print(f"Expiry: {expiry_hours}h")


if __name__ == '__main__':
    main()

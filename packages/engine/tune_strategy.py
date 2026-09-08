#!/usr/bin/env python3
"""
Grid-search tuning and train/test validation of GoldStrategy for any
timeframe, using real historical data.

The 4H-tuned defaults were carried over unchanged when other timeframes
were added, and were never re-validated on those timeframes' own price
behavior. This script generalizes the original 1H-only approach (same
train/test split, coordinate search, shared-config gating, and expiry
calculation) to any timeframe by scaling the 4H baseline config and search
grid to the target timeframe's own candle duration:

1. Splits the real OHLCV data for the target timeframe chronologically
   70/30 (train/test).
2. For each of the 5 rules, independently: starts from a timeframe-scaled
   baseline (the 4H candle-count lookbacks rescaled by 240/target_minutes,
   since a finer timeframe's candles cover less real time each), then does
   a one-pass coordinate search (vary one parameter at a time, keep
   whichever value improves train-slice profit factor) around that
   starting point.
3. Builds one shared config by taking the per-parameter median across all
   rules that passed a training-data profit-factor bar, then re-validates
   EVERY candidate rule against that final shared config on the held-out
   test slice (since in production all rules run with one shared config
   object) — a rule only ships enabled if it's still profitable on the
   test slice under the *final* shared config, not just its own
   individually-tuned one.
4. Computes an expiry window from the 95th percentile of trade durations
   (in hours) across all enabled rules' test-slice trades.

Note: only 1h (byte-identical regression against the committed
tuned_configs/1h.json) and 15m (a real tuning run) have actually been
validated end-to-end. The other timeframes (5m, 30m, 4h, 1d) are supported
by the scaling model but have not yet been run — see TIMEFRAME_MINUTES.

Usage:
    python tune_strategy.py --data data/processed/xauusd_1h_2024_2026.csv --timeframe 1h
"""
import sys
import json
import math
import argparse
import statistics
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from data.loader import GoldDataLoader
from signals.gold_strategy import GoldStrategy
from signals.realtime_generator import SignalValidator
from backtesting.engine import BacktestEngine, TradeStatus

# Matches SignalValidator(min_rr_ratio=1.5) in run_multi_timeframe_service.py.
# Tuning must score the same trade population production would actually
# publish, not whatever GoldStrategy raw-emits before that filter runs.
PRODUCTION_MIN_RR = 1.5

RULES = [
    'momentum_equilibrium',
    'london_session_breakout',
    'golden_fibonacci',
    'ath_retest',
    'order_block_retest',
    'volatility_squeeze_breakout',
    'fib_golden_zone_confluence',
]

# Params whose natural unit is "how many candles" — the same real-time
# window needs proportionally more candles on a finer timeframe. Everything
# else (ratios, percentages, thresholds) is timeframe-independent.
CANDLE_COUNT_PARAMS = {
    'swing_lookback', 'trend_lookback', 'atr_period', 'ema_fast', 'ema_slow',
    'rsi_period', 'squeeze_lookback', 'liquidity_grab_lookback',
}

# The 13 original params tune_strategy.py tunes, plus 3 for
# volatility_squeeze_breakout and 2 for fib_golden_zone_confluence (see
# docs/superpowers/specs/2026-09-08-volatility-squeeze-breakout-design.md
# and docs/superpowers/specs/strategy-ledger.md).
# GoldStrategy.DEFAULT_CONFIG also has consolidation_min_candles/
# consolidation_max_range_atr, which aren't part of the tuned set (rules
# just inherit GoldStrategy's own defaults for those).
TUNABLE_PARAMS = [
    'fib_tolerance', 'swing_lookback', 'swing_min_strength', 'trend_lookback',
    'strong_momentum_threshold', 'atr_period', 'default_rr_ratio', 'sl_buffer_atr',
    'ema_fast', 'ema_slow', 'rsi_period', 'rsi_overbought', 'rsi_oversold',
    'squeeze_lookback', 'squeeze_atr_ratio', 'breakout_buffer_atr',
    'liquidity_grab_lookback', 'fib_confluence_min_rr',
]


def scale_baseline_config(base_config, from_minutes, to_minutes):
    """
    Scale a config's candle-count params (lookback windows measured in
    bars) by from_minutes/to_minutes — a finer timeframe needs
    proportionally more candles to cover the same real-time window.
    Ratio/percentage/threshold params pass through unscaled.
    """
    scale = from_minutes / to_minutes
    scaled = {}
    for param in TUNABLE_PARAMS:
        value = base_config[param]
        # Floor candle-count params at 2 candles so scaling up to a coarser
        # timeframe (e.g. 4H -> 1D) can never collapse a lookback to 0 or 1.
        scaled[param] = max(2, round(value * scale)) if param in CANDLE_COUNT_PARAMS else value
    return scaled


# 1H-equivalent starting point, matching the original hand-scaled values
# exactly (see TestScaleBaselineConfig.test_reproduces_the_original_1h_baseline_exactly).
BASE_1H_CONFIG = scale_baseline_config(GoldStrategy.DEFAULT_CONFIG, from_minutes=240, to_minutes=60)

# Candle-count params' search neighborhood is multiplicative factors around
# that timeframe's scaled baseline value, not absolute candle counts — this
# reproduces the original hand-picked 1H grid exactly (see
# TestBuildSearchGrid.test_reproduces_the_original_1h_grid_exactly) while
# generalizing to any timeframe.
CANDLE_COUNT_GRID_FACTORS = {
    'swing_lookback': [0.7, 1.0, 1.4],
    'trend_lookback': [0.7, 1.0, 1.3],
    'atr_period': [40 / 56, 1.0, 72 / 56],
}

# volatility_squeeze_breakout's and fib_golden_zone_confluence's own
# candle-count params — kept separate from CANDLE_COUNT_GRID_FACTORS
# (rather than added to it) so build_search_grid can append them AFTER the
# original 5 grid keys below, leaving their mutual order — and the pinned
# 1H regression fixture — untouched.
SQUEEZE_LOOKBACK_GRID_FACTORS = [0.7, 1.0, 1.4]
LIQUIDITY_GRAB_LOOKBACK_GRID_FACTORS = [0.5, 1.0, 1.5]

# Ratio/percentage params are timeframe-independent — same absolute
# candidates regardless of timeframe.
RATIO_PARAM_GRID = {
    'fib_tolerance': [0.010, 0.015, 0.020],
    'default_rr_ratio': [1.5, 2.0, 2.5],
    'squeeze_atr_ratio': [0.5, 0.7, 0.9],
    'breakout_buffer_atr': [0.1, 0.2, 0.3],
    # Standard Fibonacci spacing gives a raw 38.2%->61.8% vs 61.8%->78.6%
    # reward:risk around 1.4 (see strategy-ledger.md) — 2.0 (the plan's own
    # stated minimum) may reject almost every real signal; this grid
    # includes lower candidates specifically to find out.
    'fib_confluence_min_rr': [1.2, 1.5, 2.0],
}


def build_search_grid(base_config):
    """
    Combine the candle-count factor grid (scaled off base_config's
    already-timeframe-scaled values) with the timeframe-independent ratio
    param grid, preserving the original SEARCH_GRID literal's key order
    exactly (fib_tolerance, swing_lookback, trend_lookback, atr_period,
    default_rr_ratio). tune_rule's coordinate search is order-sensitive —
    each param is tuned against whatever earlier params in the iteration
    have already been updated — so a different key order can change the
    final tuned result even though dict *content* equality looks identical.

    volatility_squeeze_breakout's 3 params (squeeze_lookback,
    squeeze_atr_ratio, breakout_buffer_atr) are appended at the end, after
    default_rr_ratio — every other rule ignores them entirely (they don't
    appear in those rules' logic), so their position can't affect those
    rules' tuned result; appending keeps the original 5's relative order,
    and the regression fixture pinned to it, exactly as before.
    """
    grid = {'fib_tolerance': RATIO_PARAM_GRID['fib_tolerance']}
    for param, factors in CANDLE_COUNT_GRID_FACTORS.items():
        grid[param] = sorted({round(base_config[param] * f) for f in factors})
        if len(grid[param]) < 2:
            print(f"⚠️  Search grid for '{param}' collapsed to a single value {grid[param]} — "
                  f"this parameter's coordinate search is a no-op for this timeframe.")
    grid['default_rr_ratio'] = RATIO_PARAM_GRID['default_rr_ratio']

    grid['squeeze_lookback'] = sorted({round(base_config['squeeze_lookback'] * f) for f in SQUEEZE_LOOKBACK_GRID_FACTORS})
    if len(grid['squeeze_lookback']) < 2:
        print("⚠️  Search grid for 'squeeze_lookback' collapsed to a single value "
              f"{grid['squeeze_lookback']} — this parameter's coordinate search is a no-op for this timeframe.")
    grid['squeeze_atr_ratio'] = RATIO_PARAM_GRID['squeeze_atr_ratio']
    grid['breakout_buffer_atr'] = RATIO_PARAM_GRID['breakout_buffer_atr']

    grid['liquidity_grab_lookback'] = sorted({
        round(base_config['liquidity_grab_lookback'] * f) for f in LIQUIDITY_GRAB_LOOKBACK_GRID_FACTORS
    })
    if len(grid['liquidity_grab_lookback']) < 2:
        print("⚠️  Search grid for 'liquidity_grab_lookback' collapsed to a single value "
              f"{grid['liquidity_grab_lookback']} — this parameter's coordinate search is a no-op for this timeframe.")
    grid['fib_confluence_min_rr'] = RATIO_PARAM_GRID['fib_confluence_min_rr']
    return grid

MIN_TRAIN_TRADES = 15
MIN_TEST_TRADES = 5

# All six timeframes are selectable, but only 1h and 15m have been
# validated end-to-end (see module docstring). The others are supported by
# the scaling model in scale_baseline_config/build_search_grid but not yet
# run — watch for the search-grid-collapsed warning above on those.
TIMEFRAME_MINUTES = {
    '5m': 5, '15m': 15, '30m': 30, '1h': 60, '4h': 240, '1d': 1440,
}


def default_output_path(timeframe):
    # Anchored to this script's own location (not cwd), matching how
    # run_multi_timeframe_service.py resolves tuned configs via
    # Path(__file__).parent — otherwise running this from another directory
    # would silently write configs the live service never looks for.
    return str(Path(__file__).parent / 'tuned_configs' / f'{timeframe}.json')


def split_train_test(df, train_frac=0.7):
    """Chronological split — train is the older `train_frac` of candles."""
    split_idx = int(len(df) * train_frac)
    return df.iloc[:split_idx], df.iloc[split_idx:]


def _production_valid_strategy_func(strategy):
    """
    Wraps GoldStrategy.evaluate so the backtest only ever sees signals
    SignalValidator would actually publish to production (risk>0, reward>0,
    rr >= PRODUCTION_MIN_RR). Without this, tuning selects rules and configs
    against a trade population production can never place.
    """
    def strategy_func(df, idx):
        signal = strategy.evaluate(df, idx)
        if signal is None:
            return None
        risk_reward = SignalValidator.compute_risk_reward(signal)
        if risk_reward is None or not SignalValidator.meets_min_rr(risk_reward[2], PRODUCTION_MIN_RR):
            return None
        return signal
    return strategy_func


def _resolved_stats(result):
    """
    profit_factor/total_trades/win_rate/net_profit_pct computed over
    RESOLVED (CLOSED_TP/CLOSED_SL) trades only — excludes CLOSED_MANUAL
    force-closes (an open position marked to market at the end of the data
    slice). A single such trade at the tail of a slice can flip a rule's
    PF gate from FAIL to PASS on an unresolved mark-to-market credit rather
    than a real win; BacktestResult.calculate_metrics() doesn't make this
    distinction, so it's recomputed here instead of trusting
    result.profit_factor/result.total_trades directly.
    """
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


def run_isolated_backtest(df, rule_name, config):
    """Run a backtest with only `rule_name` enabled. Returns (profit_factor, total_trades, result),
    computed over resolved trades only — see _resolved_stats."""
    strategy = GoldStrategy(config=config)
    for name in strategy.rules_enabled:
        strategy.rules_enabled[name] = False
    strategy.rules_enabled[rule_name] = True

    strategy_func = _production_valid_strategy_func(strategy)
    engine = BacktestEngine(initial_balance=10000, position_size_pct=2.0)
    result = engine.run(df, strategy_func, max_open_trades=1)
    stats = _resolved_stats(result)
    return stats['profit_factor'], stats['total_trades'], result


def run_combined_backtest(df, rule_names, config):
    """Run a backtest with all of `rule_names` enabled together, one shared config."""
    strategy = GoldStrategy(config=config)
    for name in strategy.rules_enabled:
        strategy.rules_enabled[name] = name in rule_names

    strategy_func = _production_valid_strategy_func(strategy)
    engine = BacktestEngine(initial_balance=10000, position_size_pct=2.0)
    return engine.run(df, strategy_func, max_open_trades=1)


def tune_rule(train_df, rule_name, base_config, search_grid):
    """One-pass coordinate search: vary one parameter at a time from the baseline."""
    current = dict(base_config)
    best_pf, best_trades, _ = run_isolated_backtest(train_df, rule_name, current)
    if best_trades < MIN_TRAIN_TRADES:
        best_pf = 0.0

    for param, values in search_grid.items():
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
    """Run `config` isolated to `rule_name` on `df`, returning (stats, trade_durations_hours).
    Both are computed over resolved (CLOSED_TP/CLOSED_SL) trades only — a force-closed trade's
    duration is truncated by the data slice ending, not by the trade actually resolving, so it
    shouldn't calibrate the expiry window either."""
    _, _, result = run_isolated_backtest(df, rule_name, config)
    resolved = [t for t in result.trades if t.status in (TradeStatus.CLOSED_TP, TradeStatus.CLOSED_SL)]
    durations_hours = [
        (t.exit_time - t.entry_time).total_seconds() / 3600
        for t in resolved if t.exit_time is not None
    ]
    stats = _resolved_stats(result)
    return stats, durations_hours


def passes_pf_gate(stats, min_trades):
    """A rule 'passes' a profitability gate if PF > 1.0 with enough trades to trust it."""
    return stats['profit_factor'] > 1.0 and stats['total_trades'] >= min_trades


def json_safe(value):
    """
    Recursively replace non-finite floats (e.g. an infinite profit factor
    from a rule with zero losing trades) with a finite sentinel, so the
    output is valid RFC-8259 JSON. Python's json.dump happily writes a bare
    `Infinity` token, which Python's own json.load tolerates but `JSON.parse`,
    `jq`, and most other parsers reject outright.
    """
    if isinstance(value, float) and not math.isfinite(value):
        return math.copysign(1e9, value)
    if isinstance(value, dict):
        return {k: json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    return value


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
    parser = argparse.ArgumentParser(description='Tune and validate GoldStrategy for a given timeframe')
    parser.add_argument('--data', type=str, required=True, help='Path to OHLCV CSV for the target timeframe')
    parser.add_argument('--timeframe', type=str, required=True, choices=sorted(TIMEFRAME_MINUTES),
                         help='Target timeframe, e.g. "1h" or "15m"')
    parser.add_argument('--output', type=str, default=None,
                         help='Output path (default: tuned_configs/<timeframe>.json)')
    parser.add_argument('--train-frac', type=float, default=0.7)
    args = parser.parse_args()

    output_path_str = args.output or default_output_path(args.timeframe)

    base_config = scale_baseline_config(
        GoldStrategy.DEFAULT_CONFIG, from_minutes=240, to_minutes=TIMEFRAME_MINUTES[args.timeframe]
    )
    search_grid = build_search_grid(base_config)

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
        tuned_config = tune_rule(train_df, rule_name, base_config, search_grid)
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
        for param in base_config:
            values = [tuned_config_by_rule[r][param] for r in candidate_rules]
            # median_low (not an interpolated median) so an even-length list
            # always resolves to a value some candidate rule actually chose,
            # rather than a number in between that nothing was tuned around.
            final_config[param] = statistics.median_low(values)
    else:
        final_config = dict(base_config)

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
        'timeframe': args.timeframe,
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
        'combined_test_slice_result': _resolved_stats(combined_result) if combined_result else None,
    }

    output_path = Path(output_path_str)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(json_safe(output), f, indent=2, default=str, allow_nan=False)

    print(f"\n✅ Wrote {output_path}")
    print(f"Enabled rules: {enabled_rules}")
    print(f"Expiry: {expiry_hours}h")


if __name__ == '__main__':
    main()

# 15-Minute Strategy Tuning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend real-data strategy tuning (currently 1H-only) to the 15-minute timeframe, sourcing enough history from MetaAPI (Yahoo Finance only gives ~60 days for intraday data), and validate the result with the same adversarial-review rigor used for 1H before anything ships.

**Architecture:** Generalize `tune_strategy.py` in place (don't fork it) so the already-hardened shared logic (RR-boundary tolerance, force-close exclusion, median-low, JSON safety) stays as one copy. Add a new dev-only `fetch_metaapi_history.py` script to pull 15m history into the same CSV schema the existing pipeline already reads. Run the generalized script against the new data, then two independent adversarial-review passes, exactly like Task 11 of the 1H work.

**Tech Stack:** Python 3.11, pandas, `metaapi-cloud-sdk` (new, dev-only — not added to `packages/engine/requirements.txt`), pytest, existing `GoldStrategy`/`BacktestEngine`/`SignalValidator` classes (unchanged).

**Spec:** `docs/superpowers/specs/2026-08-24-15m-strategy-tuning-design.md`

## Global Constraints

- `metaapi-cloud-sdk` is installed manually into the local venv for this work only. It must NOT be added to `packages/engine/requirements.txt` (that file drives the Docker build for the live service, which stays on `DATA_FEED_TYPE=yahoo` per the Task 14 decision).
- `GoldStrategy`'s take-profit calculation (`entry ± risk × default_rr_ratio`) is not changed in this work. 50-100 pips is an outcome to evaluate the tuned result against, not a new mode to build.
- Generalizing `tune_strategy.py` must not change its already-reviewed 1H behavior — every generalization step that touches shared logic has an explicit regression check against the currently-committed `tuned_configs/1h.json`.
- Same validation bar as the 1H work: two independent adversarial-review agent passes before `tuned_configs/15m.json` is trusted or committed. Do not skip this because the mechanism is now "proven" — the mechanism being sound doesn't mean any given run's output is trustworthy without checking.
- Enabling `'15m'` in `run_multi_timeframe_service.py`'s `TIMEFRAMES` list is explicitly **out of scope** for this plan — that's a deliberate follow-up decision made after reviewing the tuned result.

---

### Task 1: Generalize the tuning baseline (`scale_baseline_config`)

**Files:**
- Modify: `packages/engine/tune_strategy.py:56-73` (replace the hardcoded `BASE_1H_CONFIG` literal)
- Test: `packages/engine/tests/test_tune_strategy.py`

**Interfaces:**
- Produces: `scale_baseline_config(base_config: dict, from_minutes: int, to_minutes: int) -> dict`, `CANDLE_COUNT_PARAMS: set[str]`, `TUNABLE_PARAMS: list[str]`, `BASE_1H_CONFIG: dict` (now computed, not literal — same name and value, so nothing importing it breaks).

- [ ] **Step 1: Write the failing tests**

Add to `packages/engine/tests/test_tune_strategy.py` (add `from signals.gold_strategy import GoldStrategy` near the existing imports if not already present — it already is, per the current file):

```python
from tune_strategy import scale_baseline_config


class TestScaleBaselineConfig:
    """Regression coverage: scaling GoldStrategy.DEFAULT_CONFIG (4H) by the
    same 4x factor used for the original hand-written BASE_1H_CONFIG must
    reproduce it exactly, so generalizing tune_strategy.py to other
    timeframes doesn't silently change the already-reviewed 1H behavior."""

    EXPECTED_1H_BASELINE = {
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

    def test_reproduces_the_original_1h_baseline_exactly(self):
        scaled = scale_baseline_config(GoldStrategy.DEFAULT_CONFIG, from_minutes=240, to_minutes=60)
        assert scaled == self.EXPECTED_1H_BASELINE

    def test_candle_count_params_scale_by_the_timeframe_ratio(self):
        scaled = scale_baseline_config(GoldStrategy.DEFAULT_CONFIG, from_minutes=240, to_minutes=15)
        # 240/15 = 16x
        assert scaled['swing_lookback'] == 5 * 16
        assert scaled['trend_lookback'] == 50 * 16
        assert scaled['atr_period'] == 14 * 16
        assert scaled['ema_fast'] == 9 * 16
        assert scaled['ema_slow'] == 21 * 16
        assert scaled['rsi_period'] == 14 * 16

    def test_ratio_params_pass_through_unscaled(self):
        scaled = scale_baseline_config(GoldStrategy.DEFAULT_CONFIG, from_minutes=240, to_minutes=15)
        assert scaled['fib_tolerance'] == 0.015
        assert scaled['default_rr_ratio'] == 2.0
        assert scaled['sl_buffer_atr'] == 0.3
        assert scaled['rsi_overbought'] == 70
        assert scaled['rsi_oversold'] == 30
        assert scaled['swing_min_strength'] == 2
        assert scaled['strong_momentum_threshold'] == 0.02
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/engine && source venv/bin/activate && python -m pytest tests/test_tune_strategy.py::TestScaleBaselineConfig -v`
Expected: FAIL — `ImportError: cannot import name 'scale_baseline_config'`

- [ ] **Step 3: Implement `scale_baseline_config`**

In `packages/engine/tune_strategy.py`, replace:

```python
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
```

with:

```python
# Params whose natural unit is "how many candles" — the same real-time
# window needs proportionally more candles on a finer timeframe. Everything
# else (ratios, percentages, thresholds) is timeframe-independent.
CANDLE_COUNT_PARAMS = {'swing_lookback', 'trend_lookback', 'atr_period', 'ema_fast', 'ema_slow', 'rsi_period'}

# The 13 params tune_strategy.py tunes. GoldStrategy.DEFAULT_CONFIG also has
# consolidation_min_candles/consolidation_max_range_atr, which aren't part
# of the tuned set (rules just inherit GoldStrategy's own defaults for those).
TUNABLE_PARAMS = [
    'fib_tolerance', 'swing_lookback', 'swing_min_strength', 'trend_lookback',
    'strong_momentum_threshold', 'atr_period', 'default_rr_ratio', 'sl_buffer_atr',
    'ema_fast', 'ema_slow', 'rsi_period', 'rsi_overbought', 'rsi_oversold',
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
        scaled[param] = round(value * scale) if param in CANDLE_COUNT_PARAMS else value
    return scaled


# 1H-equivalent starting point, matching the original hand-scaled values
# exactly (see TestScaleBaselineConfig.test_reproduces_the_original_1h_baseline_exactly).
BASE_1H_CONFIG = scale_baseline_config(GoldStrategy.DEFAULT_CONFIG, from_minutes=240, to_minutes=60)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/engine && source venv/bin/activate && python -m pytest tests/test_tune_strategy.py -v`
Expected: all pass, including the pre-existing tests (confirms `BASE_1H_CONFIG` still has the same value everything else expects).

- [ ] **Step 5: Commit**

```bash
cd packages/engine
git add tune_strategy.py tests/test_tune_strategy.py
git commit -m "refactor: generalize tune_strategy.py's baseline config to scale_baseline_config"
```

---

### Task 2: Generalize the search grid (`build_search_grid`)

**Files:**
- Modify: `packages/engine/tune_strategy.py:75-81` (replace the hardcoded `SEARCH_GRID` literal), `tune_strategy.py:166-186` (`tune_rule` signature)
- Test: `packages/engine/tests/test_tune_strategy.py`

**Interfaces:**
- Consumes: `scale_baseline_config`, `BASE_1H_CONFIG` (Task 1)
- Produces: `build_search_grid(base_config: dict) -> dict`, `tune_rule(train_df, rule_name, base_config, search_grid) -> dict` (signature changed — was `tune_rule(train_df, rule_name)`)

- [ ] **Step 1: Write the failing tests**

Add to `packages/engine/tests/test_tune_strategy.py`:

```python
from tune_strategy import build_search_grid


class TestBuildSearchGrid:
    """Regression coverage: the candle-count search neighborhood is now
    expressed as multiplicative factors around the (already-scaled)
    baseline value rather than hardcoded absolute candle counts, so it
    generalizes to any timeframe. For 1H this must reproduce the original
    hand-picked SEARCH_GRID exactly."""

    EXPECTED_1H_GRID = {
        'fib_tolerance': [0.010, 0.015, 0.020],
        'swing_lookback': [14, 20, 28],
        'trend_lookback': [140, 200, 260],
        'atr_period': [40, 56, 72],
        'default_rr_ratio': [1.5, 2.0, 2.5],
    }

    def test_reproduces_the_original_1h_grid_exactly(self):
        grid = build_search_grid(BASE_1H_CONFIG)
        assert grid == self.EXPECTED_1H_GRID

    def test_ratio_param_grid_is_timeframe_independent(self):
        base_15m = scale_baseline_config(GoldStrategy.DEFAULT_CONFIG, from_minutes=240, to_minutes=15)
        grid = build_search_grid(base_15m)
        assert grid['fib_tolerance'] == [0.010, 0.015, 0.020]
        assert grid['default_rr_ratio'] == [1.5, 2.0, 2.5]

    def test_candle_count_grid_scales_with_the_baseline(self):
        base_15m = scale_baseline_config(GoldStrategy.DEFAULT_CONFIG, from_minutes=240, to_minutes=15)
        grid = build_search_grid(base_15m)
        # swing_lookback baseline at 15m = 5*16 = 80; factors [0.7, 1.0, 1.4]
        assert grid['swing_lookback'] == sorted({round(80 * f) for f in (0.7, 1.0, 1.4)})
```

(`scale_baseline_config`, `BASE_1H_CONFIG`, and `GoldStrategy` are already imported from Task 1's test additions.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/engine && source venv/bin/activate && python -m pytest tests/test_tune_strategy.py::TestBuildSearchGrid -v`
Expected: FAIL — `ImportError: cannot import name 'build_search_grid'`

- [ ] **Step 3: Implement `build_search_grid` and refactor `tune_rule`**

In `packages/engine/tune_strategy.py`, replace:

```python
SEARCH_GRID = {
    'fib_tolerance': [0.010, 0.015, 0.020],
    'swing_lookback': [14, 20, 28],
    'trend_lookback': [140, 200, 260],
    'atr_period': [40, 56, 72],
    'default_rr_ratio': [1.5, 2.0, 2.5],
}
```

with:

```python
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

# Ratio/percentage params are timeframe-independent — same absolute
# candidates regardless of timeframe.
RATIO_PARAM_GRID = {
    'fib_tolerance': [0.010, 0.015, 0.020],
    'default_rr_ratio': [1.5, 2.0, 2.5],
}


def build_search_grid(base_config):
    """Combine the candle-count factor grid (scaled off base_config's
    already-timeframe-scaled values) with the timeframe-independent ratio
    param grid."""
    grid = dict(RATIO_PARAM_GRID)
    for param, factors in CANDLE_COUNT_GRID_FACTORS.items():
        grid[param] = sorted({round(base_config[param] * f) for f in factors})
    return grid
```

Then replace the `tune_rule` function:

```python
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
```

with:

```python
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
```

`tune_rule`'s only caller is in `main()` (`tuned_config = tune_rule(train_df, rule_name)`), updated in Task 3.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/engine && source venv/bin/activate && python -m pytest tests/test_tune_strategy.py -v`
Expected: `TestBuildSearchGrid` passes. `main()`'s call to `tune_rule` is still the old 2-arg form at this point, so don't run the full script end-to-end yet — that's fixed in Task 3. Confirm no other test calls `tune_rule` directly (grep `tests/test_tune_strategy.py` for `tune_rule(` — none currently do, per the existing file).

- [ ] **Step 5: Commit**

```bash
cd packages/engine
git add tune_strategy.py tests/test_tune_strategy.py
git commit -m "refactor: generalize tune_strategy.py's search grid to build_search_grid"
```

---

### Task 3: Add `--timeframe` CLI support and wire it through `main()`

**Files:**
- Modify: `packages/engine/tune_strategy.py:239-341` (`main()`)
- Test: `packages/engine/tests/test_tune_strategy.py`

**Interfaces:**
- Consumes: `scale_baseline_config`, `build_search_grid`, `tune_rule(train_df, rule_name, base_config, search_grid)` (Tasks 1-2)
- Produces: `TIMEFRAME_MINUTES: dict`, `default_output_path(timeframe: str) -> str`

- [ ] **Step 1: Write the failing tests**

Add to `packages/engine/tests/test_tune_strategy.py`:

```python
from tune_strategy import TIMEFRAME_MINUTES, default_output_path


class TestTimeframeDefaults:
    def test_default_output_path_uses_timeframe(self):
        assert default_output_path('15m') == 'tuned_configs/15m.json'
        assert default_output_path('1h') == 'tuned_configs/1h.json'

    def test_timeframe_minutes_covers_all_supported_timeframes(self):
        assert TIMEFRAME_MINUTES == {'5m': 5, '15m': 15, '30m': 30, '1h': 60, '4h': 240, '1d': 1440}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/engine && source venv/bin/activate && python -m pytest tests/test_tune_strategy.py::TestTimeframeDefaults -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Add `TIMEFRAME_MINUTES`/`default_output_path` and rewrite `main()`**

In `packages/engine/tune_strategy.py`, add near the top-level constants (after `MIN_TRAIN_TRADES`/`MIN_TEST_TRADES`):

```python
TIMEFRAME_MINUTES = {
    '5m': 5, '15m': 15, '30m': 30, '1h': 60, '4h': 240, '1d': 1440,
}


def default_output_path(timeframe):
    return f'tuned_configs/{timeframe}.json'
```

Replace the entire `main()` function:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/engine && source venv/bin/activate && python -m pytest tests/ -v --ignore=tests/test_api.py`
Expected: all pass except the 2 pre-existing unrelated `test_strategy.py` failures (stale rule names).

- [ ] **Step 5: Commit**

```bash
cd packages/engine
git add tune_strategy.py tests/test_tune_strategy.py
git commit -m "feat: add --timeframe flag to tune_strategy.py, generalizing it beyond 1H"
```

---

### Task 4: Regression-check the generalized script against the existing 1H result

This task has no unit tests of its own — it's a direct verification that Tasks 1-3 didn't change the already-reviewed, already-shipped 1H behavior.

**Files:** none (verification only)

- [ ] **Step 1: Re-run tuning for 1H with the new CLI**

Run:
```bash
cd packages/engine
source venv/bin/activate
python tune_strategy.py --data data/processed/xauusd_1h_2024_2026.csv --timeframe 1h --output /tmp/regression_1h.json
```

- [ ] **Step 2: Diff against the committed 1H config**

Run:
```bash
cd packages/engine
python3 -c "
import json
with open('/tmp/regression_1h.json') as f:
    new = json.load(f)
with open('tuned_configs/1h.json') as f:
    old = json.load(f)
new.pop('generated_at', None)
old.pop('generated_at', None)
assert new == old, 'MISMATCH — generalizing tune_strategy.py changed the 1H result'
print('OK — byte-identical to the committed 1H config (ignoring generated_at)')
"
```
Expected: `OK — byte-identical...`. If this fails, STOP — do not proceed to Task 5 until the mismatch is understood and fixed (compare the diverging fields directly, most likely a `TUNABLE_PARAMS`/`CANDLE_COUNT_PARAMS`/`CANDLE_COUNT_GRID_FACTORS` typo from Tasks 1-2).

---

### Task 5: `fetch_metaapi_history.py` — candle validation and DataFrame conversion

**Files:**
- Create: `packages/engine/fetch_metaapi_history.py`
- Test: `packages/engine/tests/test_fetch_metaapi_history.py`

**Interfaces:**
- Produces: `validate_candles(candles: list[dict]) -> tuple[list[dict], int]`, `candles_to_dataframe(candles: list[dict]) -> pd.DataFrame`

- [ ] **Step 1: Write the failing tests**

Create `packages/engine/tests/test_fetch_metaapi_history.py`:

```python
"""Tests for fetch_metaapi_history.py's pure data-transformation functions.
No real MetaAPI network calls in this file — see test_fetch_metaapi_history.py's
TestFetchAllCandles for the mocked-client pagination tests."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fetch_metaapi_history import validate_candles, candles_to_dataframe


def _candle(time, open_, high, low, close, volume=100):
    return {'time': time, 'open': open_, 'high': high, 'low': low, 'close': close, 'tickVolume': volume}


class TestValidateCandles:
    def test_keeps_valid_ohlc(self):
        candles = [_candle('2026-01-01T00:00:00.000Z', 2000.0, 2005.0, 1998.0, 2002.0)]
        valid, dropped = validate_candles(candles)
        assert valid == candles
        assert dropped == 0

    def test_drops_high_below_open_or_close(self):
        candles = [_candle('2026-01-01T00:00:00.000Z', 2000.0, 1999.0, 1998.0, 2002.0)]
        valid, dropped = validate_candles(candles)
        assert valid == []
        assert dropped == 1

    def test_drops_low_above_open_or_close(self):
        candles = [_candle('2026-01-01T00:00:00.000Z', 2000.0, 2005.0, 2001.0, 1999.0)]
        valid, dropped = validate_candles(candles)
        assert valid == []
        assert dropped == 1


class TestCandlesToDataframe:
    def test_produces_the_expected_schema(self):
        candles = [
            _candle('2026-01-01T01:00:00.000Z', 2001.0, 2006.0, 1999.0, 2003.0, volume=150),
            _candle('2026-01-01T00:00:00.000Z', 2000.0, 2005.0, 1998.0, 2002.0, volume=100),
        ]
        df = candles_to_dataframe(candles)
        assert list(df.columns) == ['open', 'high', 'low', 'close', 'volume']
        assert df.index.name == 'Datetime'
        assert df.index[0] < df.index[1]  # sorted ascending despite descending input
        assert df.iloc[0]['volume'] == 100

    def test_drops_duplicate_timestamps(self):
        candles = [
            _candle('2026-01-01T00:00:00.000Z', 2000.0, 2005.0, 1998.0, 2002.0),
            _candle('2026-01-01T00:00:00.000Z', 2000.0, 2005.0, 1998.0, 2002.0),
        ]
        df = candles_to_dataframe(candles)
        assert len(df) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/engine && source venv/bin/activate && python -m pytest tests/test_fetch_metaapi_history.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'fetch_metaapi_history'`

- [ ] **Step 3: Create `fetch_metaapi_history.py` with the pure functions**

Create `packages/engine/fetch_metaapi_history.py`:

```python
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
```

(The `if __name__ == '__main__':` block is a placeholder specifically for this task's intermediate state — Task 6 replaces it with the real CLI entry point. This is expected and not a plan violation: the task is deliberately split so the pure, testable transformation functions land and are reviewable before the async network/CLI code is added on top.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/engine && source venv/bin/activate && python -m pytest tests/test_fetch_metaapi_history.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
cd packages/engine
git add fetch_metaapi_history.py tests/test_fetch_metaapi_history.py
git commit -m "feat: add fetch_metaapi_history.py candle validation and DataFrame conversion"
```

---

### Task 6: `fetch_metaapi_history.py` — pagination and CLI

**Files:**
- Modify: `packages/engine/fetch_metaapi_history.py` (replace the placeholder `__main__` block)
- Test: `packages/engine/tests/test_fetch_metaapi_history.py`

**Interfaces:**
- Consumes: `validate_candles`, `candles_to_dataframe` (Task 5)
- Produces: `fetch_all_candles(account, symbol, timeframe, page_limit=1000) -> list[dict]` (async), `main_async(args)` (async), `main()`

- [ ] **Step 1: Write the failing tests**

Add to `packages/engine/tests/test_fetch_metaapi_history.py`:

```python
import asyncio
from unittest.mock import AsyncMock

from fetch_metaapi_history import fetch_all_candles


class TestFetchAllCandles:
    """No real MetaAPI network calls — `account` is an AsyncMock standing in
    for the SDK's MetatraderAccount, whose get_historical_candles() is a
    coroutine per the SDK's documented usage
    (await account.get_historical_candles(symbol=..., timeframe=..., start_time=..., limit=...))."""

    def test_pages_backward_until_a_short_page(self):
        account = AsyncMock()
        full_page = [
            _candle(f'2026-01-01T{h:02d}:00:00.000Z', 2000.0, 2005.0, 1998.0, 2002.0)
            for h in range(23, -1, -1)  # 24 candles — exactly one full page
        ]
        short_page = full_page[:5]
        account.get_historical_candles.side_effect = [full_page, short_page, []]

        candles = asyncio.run(fetch_all_candles(account, 'XAUUSD', '15m', page_limit=24))

        assert len(candles) == 24 + 5
        # stops after the short page (< page_limit signals end of history) —
        # never makes the third call
        assert account.get_historical_candles.call_count == 2

    def test_stops_immediately_on_empty_first_page(self):
        account = AsyncMock()
        account.get_historical_candles.side_effect = [[]]

        candles = asyncio.run(fetch_all_candles(account, 'XAUUSD', '15m', page_limit=1000))

        assert candles == []
        assert account.get_historical_candles.call_count == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/engine && source venv/bin/activate && python -m pytest tests/test_fetch_metaapi_history.py::TestFetchAllCandles -v`
Expected: FAIL — `ImportError: cannot import name 'fetch_all_candles'`

- [ ] **Step 3: Implement pagination and the CLI**

In `packages/engine/fetch_metaapi_history.py`, replace the placeholder `if __name__ == '__main__':` block at the end with:

```python
async def fetch_all_candles(account, symbol, timeframe, page_limit=1000):
    """
    Page backward from now via account.get_historical_candles(start_time=...),
    which returns candles strictly before start_time, until the API returns
    an empty page or a page shorter than page_limit (both signal we've hit
    the start of available history). Returns a flat list of raw candle
    dicts — still needs validate_candles()/candles_to_dataframe().
    """
    all_candles = []
    cursor = datetime.now(timezone.utc)
    while True:
        page = await account.get_historical_candles(
            symbol=symbol, timeframe=timeframe, start_time=cursor, limit=page_limit
        )
        if not page:
            break
        all_candles.extend(page)
        if len(page) < page_limit:
            break
        cursor = min(pd.to_datetime(c['time'], utc=True) for c in page).to_pydatetime()
    return all_candles


async def main_async(args):
    from metaapi_cloud_sdk import MetaApi

    token = os.getenv('METAAPI_TOKEN')
    account_id = os.getenv('METAAPI_ACCOUNT_ID')
    if not token or not account_id:
        print("METAAPI_TOKEN and METAAPI_ACCOUNT_ID must be set (see packages/engine/.env)")
        sys.exit(1)

    api = MetaApi(token)
    account = api.metatrader_account_api.get_account(account_id)
    await account.deploy()
    await account.wait_connected()

    candles = await fetch_all_candles(account, args.symbol, args.timeframe)
    if not candles:
        print("No historical candles returned — this account/broker may not "
              "retain history for this symbol/timeframe.")
        sys.exit(1)

    times = pd.to_datetime([c['time'] for c in candles], utc=True)
    days = (times.max() - times.min()).total_seconds() / 86400
    print(f"Fetched {len(candles)} raw candles: {times.min()} to {times.max()} ({days:.1f} days)")

    if args.discover:
        print("(--discover set: not validating/writing a CSV)")
        return

    valid, dropped = validate_candles(candles)
    if dropped:
        print(f"Dropped {dropped} candles failing OHLC validation")
    df = candles_to_dataframe(valid)
    print(f"After validation/dedup: {len(df)} candles, {df.index.min()} to {df.index.max()}")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path)
    print(f"Wrote {output_path}")


def main():
    parser = argparse.ArgumentParser(description='Fetch XAUUSD historical candles from MetaAPI (dev-only)')
    parser.add_argument('--timeframe', required=True, help='MetaAPI timeframe string, e.g. "15m"')
    parser.add_argument('--symbol', default='XAUUSD')
    parser.add_argument('--discover', action='store_true',
                         help='Report available history depth and exit without writing a CSV')
    parser.add_argument('--output', type=str,
                         help='Output CSV path (required unless --discover)')
    args = parser.parse_args()
    if not args.discover and not args.output:
        parser.error('--output is required unless --discover is set')
    asyncio.run(main_async(args))


if __name__ == '__main__':
    main()
```

Note on the SDK calls in `main_async` (`account.deploy()`, `account.wait_connected()`, `account.get_historical_candles(...)`): these are written per the SDK's documented async usage (`await account.get_historical_candles(symbol=..., timeframe=..., start_time=..., limit=...)`, per MetaAPI's Python SDK examples). `MetaAPIDataFeed.connect()` in `src/data/realtime_feed.py` calls the same kind of methods *without* `await` — since `metaapi-cloud-sdk` was never actually installed until now (the Task 14 finding), that existing code has likely never run successfully and its missing-`await` bug was never caught. If any exact method name/signature here doesn't match what the installed SDK actually exposes, check the installed package's source (`python -c "import metaapi_cloud_sdk; print(metaapi_cloud_sdk.__file__)"` then read the `MetatraderAccount`/`MetaApi` class source directly) rather than guessing — this is normal integration work against a real external SDK, not a plan gap.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/engine && source venv/bin/activate && python -m pytest tests/test_fetch_metaapi_history.py -v`
Expected: PASS (7 tests total: 5 from Task 5, 2 new)

- [ ] **Step 5: Run the full test suite**

Run: `cd packages/engine && source venv/bin/activate && python -m pytest tests/ -v --ignore=tests/test_api.py`
Expected: all pass except the 2 pre-existing unrelated `test_strategy.py` failures.

- [ ] **Step 6: Commit**

```bash
cd packages/engine
git add fetch_metaapi_history.py tests/test_fetch_metaapi_history.py
git commit -m "feat: add MetaAPI historical-candle pagination and CLI to fetch_metaapi_history.py"
```

---

### Task 7: Install the SDK and discover actual 15m history depth

This task has no unit tests of its own — it's the real-account discovery step the spec requires before trusting any tuning run, and it determines whether the rest of this plan can proceed as written.

**Files:** none (installation + one real API call)

**Interfaces:**
- Consumes: `fetch_metaapi_history.py --discover` (Task 6), `METAAPI_TOKEN`/`METAAPI_ACCOUNT_ID` already present in `packages/engine/.env`.

- [ ] **Step 1: Install the dev-only dependency**

Run: `cd packages/engine && source venv/bin/activate && pip install metaapi-cloud-sdk`

Do **not** add this to `requirements.txt` (see Global Constraints).

- [ ] **Step 2: Run the discovery check**

Run:
```bash
cd packages/engine
source venv/bin/activate
set -a && source .env && set +a  # loads METAAPI_TOKEN/METAAPI_ACCOUNT_ID into the shell
python fetch_metaapi_history.py --timeframe 15m --discover
```

- [ ] **Step 3: Evaluate the reported depth and report back before proceeding**

Compare the reported day count against the 1H work's 24-month (~730-day) window. Report the actual number back before continuing to Task 8:
- If depth is comparably deep (multiple hundreds of days or more): proceed to Task 8.
- If depth is thin (roughly comparable to or worse than Yahoo's ~60 days): **STOP.** Per the spec's accepted risk, this invalidates the "MetaAPI gives us enough history" premise this whole plan is built on — report the actual number to the user and discuss before spending more effort, rather than proceeding to tune on data too thin to trust (same principle as Task 11 Step 4's "don't ship an untrustworthy result silently" in the 1H work).

---

### Task 8: Fetch the full 15m history

**Files:** none (data fetch — the output CSV is gitignored, matching the existing 1H/4H CSVs in `data/processed/`)

**Interfaces:**
- Consumes: `fetch_metaapi_history.py` (Task 6), a go-ahead from Task 7's discovery check.

- [ ] **Step 1: Fetch and write the CSV**

Run (adjust the date range in the filename to whatever Task 7 actually reported):
```bash
cd packages/engine
source venv/bin/activate
set -a && source .env && set +a
python fetch_metaapi_history.py --timeframe 15m --output data/processed/xauusd_15m_<start>_<end>.csv
```

- [ ] **Step 2: Sanity-check the written file**

Run:
```bash
cd packages/engine
python3 -c "
import sys; sys.path.insert(0, 'src')
from data.loader import GoldDataLoader
df = GoldDataLoader().load_from_csv('data/processed/xauusd_15m_<start>_<end>.csv')
print(f'{len(df)} candles, {df.index.min()} to {df.index.max()}')
print(df.columns.tolist())
assert list(df.columns) == ['open', 'high', 'low', 'close', 'volume']
assert df.index.is_monotonic_increasing
print('OK')
"
```
Expected: `OK`, confirming `GoldDataLoader.load_from_csv()` (unchanged) reads the MetaAPI-sourced file exactly like it reads the Yahoo-sourced ones.

---

### Task 9: Run 15m tuning with adversarial review

Mirrors Task 11 of the 1H work exactly — same rigor, same reason (real capital is the eventual target). This task has no unit tests of its own.

**Files:**
- Output: `packages/engine/tuned_configs/15m.json`

**Interfaces:**
- Consumes: `tune_strategy.py --timeframe 15m` (Tasks 1-4), `data/processed/xauusd_15m_<start>_<end>.csv` (Task 8)

- [ ] **Step 1: Dispatch the tuning execution agent**

Use the Agent tool with `model: opus`, `effort: high`, and this prompt (fill in the exact data filename from Task 8):

> Run `packages/engine/tune_strategy.py --data packages/engine/data/processed/<exact filename from Task 8> --timeframe 15m` from the `packages/engine` directory using the venv at `packages/engine/venv` (activate it first). Report: the full stdout, the resulting `tuned_configs/15m.json` contents, and your own written assessment of overfitting risk — specifically: (a) does the train/test split look free of any leakage (test dates strictly after train dates, with no overlap), (b) is `MIN_TRAIN_TRADES`/`MIN_TEST_TRADES` being enforced correctly (a rule with too few trades in either slice should not ship enabled), (c) does the final shared-config re-validation in the script's output show any candidate rule that passed individually but failed under the shared config (if so, confirm it was correctly excluded from `enabled_rules`), (d) anything statistically suspicious, and (e) specifically report the typical take-profit distance in pips for whatever rule(s) end up enabled — the user's stated goal is a strategy that nets roughly 50-100 pips consistently, and this tuning run doesn't optimize for that number directly (see the design spec's decision log), so it needs to be checked after the fact.

- [ ] **Step 2: Dispatch the adversarial review agent**

Use the Agent tool with `model: opus`, `effort: high`, and this prompt (fill in the actual `tuned_configs/15m.json` produced by Step 1, pasted inline or by file path):

> Independently review `packages/engine/tuned_configs/15m.json` and the script that produced it (`packages/engine/tune_strategy.py --timeframe 15m`) for correctness, without trusting the first agent's self-assessment. Specifically: (1) Re-derive the reported profit factor and trade count for at least 2 of the 5 rules from scratch by running `python tune_strategy.py --data <path> --timeframe 15m --output /tmp/reverify_15m.json` yourself and diffing the result against the original — the numbers must match exactly (deterministic script, same input). (2) Check `split_train_test` for date-range leakage. (3) Check `tune_rule`'s coordinate search for lookahead bias. (4) Check whether `final_config`'s median-based construction produced a config no individual rule was actually tuned around, and if so, whether the final shared-config re-validation step still shows real profitability for every rule in `enabled_rules`. (5) Specifically stress-test whatever rule(s) ship enabled the way the 1H work's second review round did: trace individual trades, check for `CLOSED_MANUAL` force-close artifacts inflating the profit factor, check for any rule whose edge is concentrated in one or two outlier trades. Report PASS/FAIL with specifics for each of these five checks, and flag anything else suspicious.

- [ ] **Step 3: Resolve any disagreement**

If either agent flags a real problem, fix `tune_strategy.py` and/or `fetch_metaapi_history.py` accordingly, re-run both steps above, and do not proceed until both agents agree the output is trustworthy — same as the 1H work, which took 3 rounds. Record what was found and fixed (if anything) in the commit message for this task.

- [ ] **Step 4: Confirm the output file is complete**

Run:
```bash
cd packages/engine
python3 -c "
import json
with open('tuned_configs/15m.json') as f:
    data = json.load(f)
assert 'config' in data and isinstance(data['config'], dict)
assert 'enabled_rules' in data and isinstance(data['enabled_rules'], list)
assert 'expiry_hours' in data and isinstance(data['expiry_hours'], (int, float))
print('enabled_rules:', data['enabled_rules'])
print('expiry_hours:', data['expiry_hours'])
print('OK')
"
```
Expected: `OK`. If `enabled_rules` is empty, stop and discuss with the user before treating this as a finished result — same principle as the 1H work's equivalent check.

- [ ] **Step 5: Commit**

```bash
cd packages/engine
git add tuned_configs/15m.json
git commit -m "feat: add validated 15m strategy config from real-data tuning"
```

---

### Task 10: Report back

Not a code task — synthesize and present the result.

- [ ] **Step 1: Report to the user**

Cover: which rule(s) survived (if any) and their PF/trade-count across train/individual-test/shared-config, the resulting `expiry_hours`, and — the specific thing this whole effort was checking — the typical take-profit distance in pips for whatever's enabled, so it's clear whether the 50-100 pip target actually materialized. Note explicitly that `run_multi_timeframe_service.py`'s `TIMEFRAMES` list is unchanged — enabling 15m live is a separate decision, not done as part of this plan.

# GBPUSD/EURUSD Worker Wiring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generalize the live multi-timeframe signal service from a single hardcoded instrument (XAUUSD/GoldStrategy) to `(symbol, strategy_class, timeframe)` as the unit of parallelism, so GBPUSD and EURUSD run live on `ForexSessionStrategy` alongside gold — shipped with their strategy rule disabled (zero signals) until explicitly approved.

**Architecture:** A new `WorkerSpec` dataclass replaces the flat `TIMEFRAMES` list; `TimeframeWorker` is parameterized by a spec instead of hardcoding XAUUSD/GoldStrategy; every place that keyed shared state (`last_processed_candle`, `worker_heartbeat`) by bare timeframe is rekeyed to `worker_id = "SYMBOL:timeframe"`; a new `enabled_forex_symbols` setting gates the forex workers' single rule without touching the existing `enabled_strategies` setting gold's live admin UI already depends on.

**Tech Stack:** Python 3.11 (engine + API), pytest, SQLAlchemy, FastAPI.

**Spec:** `docs/superpowers/specs/2026-09-09-gbpusd-eurusd-worker-wiring-design.md`

## Global Constraints

- **Don't break gold.** `XAUUSD`/`GoldStrategy`/`order_block_retest` behavior must be byte-identical after this change — every task that touches shared code includes a gold-regression test.
- **Ship live-but-disabled.** GBPUSD/EURUSD worker threads run for real (data feed, settings refresh, heartbeat, restart-protection) but their strategy rule stays off (`enabled_forex_symbols` defaults to `[]`) — zero signals, zero Telegram messages, zero DB rows until a human explicitly enables a symbol.
- **TDD.** Every task: write the failing test, watch it fail, implement, watch it pass, commit.
- **No shape change to `enabled_strategies`.** `apps/web/app/controls/page.tsx:58` PUTs it as a flat `string[]` from a live admin toggle — it must keep that exact shape and meaning.

---

### Task 1: `WorkerSpec` + `TimeframeWorker` constructor/properties

**Files:**
- Modify: `packages/engine/run_multi_timeframe_service.py:1-113` (imports, `TIMEFRAMES` constant, `TimeframeWorker.__init__`)
- Modify: `packages/engine/tests/test_worker_restart.py` (constructor call sites)
- Test: `packages/engine/tests/test_worker_spec.py` (new)

**Interfaces:**
- Produces: `WorkerSpec` (dataclass: `symbol: str`, `strategy_class: type`, `timeframe: str`, `tuned_config_filename: str`); `XAUUSD_1H_SPEC`, `GBPUSD_1H_SPEC`, `EURUSD_1H_SPEC` module-level constants; `WORKER_SPECS: List[WorkerSpec]`; `TimeframeWorker(spec: WorkerSpec, database_url: str, shared_dedup_subscriber, telegram_subscriber=None, enable_trading=False, mt5_config=None)`; `TimeframeWorker.worker_id` (property, `f"{spec.symbol}:{spec.timeframe}"`), `.symbol` (property), `.timeframe` (property, kept for backward-compat attribute access elsewhere in the file).

- [ ] **Step 1: Write the failing test**

Create `packages/engine/tests/test_worker_spec.py`:

```python
"""Tests for WorkerSpec and TimeframeWorker's spec-driven construction."""
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import run_multi_timeframe_service as svc_module
from signals.gold_strategy import GoldStrategy
from signals.forex_session_strategy import ForexSessionStrategy


class TestWorkerSpecs:
    def test_worker_specs_has_three_entries(self):
        assert len(svc_module.WORKER_SPECS) == 3

    def test_xauusd_spec_uses_gold_strategy(self):
        spec = svc_module.XAUUSD_1H_SPEC
        assert spec.symbol == 'XAUUSD'
        assert spec.strategy_class is GoldStrategy
        assert spec.timeframe == '1h'
        assert spec.tuned_config_filename == '1h.json'

    def test_gbpusd_spec_uses_forex_session_strategy(self):
        spec = svc_module.GBPUSD_1H_SPEC
        assert spec.symbol == 'GBPUSD'
        assert spec.strategy_class is ForexSessionStrategy
        assert spec.timeframe == '1h'
        assert spec.tuned_config_filename == 'gbpusd_1h.json'

    def test_eurusd_spec_uses_forex_session_strategy(self):
        spec = svc_module.EURUSD_1H_SPEC
        assert spec.symbol == 'EURUSD'
        assert spec.strategy_class is ForexSessionStrategy
        assert spec.timeframe == '1h'
        assert spec.tuned_config_filename == 'eurusd_1h.json'

    def test_worker_specs_contains_all_three_in_order(self):
        assert svc_module.WORKER_SPECS == [
            svc_module.XAUUSD_1H_SPEC,
            svc_module.GBPUSD_1H_SPEC,
            svc_module.EURUSD_1H_SPEC,
        ]


class TestTimeframeWorkerSpecProperties:
    def _worker(self, spec):
        return svc_module.TimeframeWorker(
            spec=spec,
            database_url='sqlite:///:memory:',
            shared_dedup_subscriber=MagicMock(),
        )

    def test_worker_id_combines_symbol_and_timeframe(self):
        worker = self._worker(svc_module.GBPUSD_1H_SPEC)
        assert worker.worker_id == 'GBPUSD:1h'

    def test_symbol_property_reflects_spec(self):
        worker = self._worker(svc_module.EURUSD_1H_SPEC)
        assert worker.symbol == 'EURUSD'

    def test_timeframe_property_reflects_spec(self):
        worker = self._worker(svc_module.XAUUSD_1H_SPEC)
        assert worker.timeframe == '1h'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/engine && ./venv/bin/python3 -m pytest tests/test_worker_spec.py -v`
Expected: FAIL — `AttributeError: module 'run_multi_timeframe_service' has no attribute 'WORKER_SPECS'` (and `TimeframeWorker.__init__() got an unexpected keyword argument 'spec'`).

- [ ] **Step 3: Implement `WorkerSpec` and update `TimeframeWorker`**

In `packages/engine/run_multi_timeframe_service.py`, replace:

```python
# Only 1H has been re-tuned and validated against real market data
# (see docs/superpowers/specs/2026-08-22-signal-validation-and-outcome-tracking-design.md).
# The other timeframes are left available in the code but not run live
# until each is independently validated the same way.
TIMEFRAMES = ['1h']

# Only order_block_retest survived shared-config, out-of-sample validation.
# Every other rule tried (5 legacy + 3 new hypotheses) was ruled out and
# its code deleted — see docs/superpowers/specs/strategy-ledger.md.
PROFITABLE_RULES = [
    'order_block_retest',
]
```

with:

```python
from dataclasses import dataclass
from signals.forex_session_strategy import ForexSessionStrategy


@dataclass(frozen=True)
class WorkerSpec:
    """One (symbol, strategy_class, timeframe) worker to run live. See
    docs/superpowers/specs/2026-09-09-gbpusd-eurusd-worker-wiring-design.md."""
    symbol: str
    strategy_class: type
    timeframe: str
    tuned_config_filename: str


# Only 1H has been re-tuned and validated against real market data for gold
# (see docs/superpowers/specs/2026-08-22-signal-validation-and-outcome-tracking-design.md)
# and for GBPUSD/EURUSD (see
# docs/superpowers/specs/2026-09-09-gbpusd-asian-range-breakout-design.md).
# GBPUSD/EURUSD ship with their rule disabled by default (see
# enabled_forex_symbols in settings_models.py) — the worker runs live for
# real, but generates zero signals until explicitly enabled.
XAUUSD_1H_SPEC = WorkerSpec(symbol='XAUUSD', strategy_class=GoldStrategy, timeframe='1h', tuned_config_filename='1h.json')
GBPUSD_1H_SPEC = WorkerSpec(symbol='GBPUSD', strategy_class=ForexSessionStrategy, timeframe='1h', tuned_config_filename='gbpusd_1h.json')
EURUSD_1H_SPEC = WorkerSpec(symbol='EURUSD', strategy_class=ForexSessionStrategy, timeframe='1h', tuned_config_filename='eurusd_1h.json')

WORKER_SPECS = [XAUUSD_1H_SPEC, GBPUSD_1H_SPEC, EURUSD_1H_SPEC]

# Only order_block_retest survived shared-config, out-of-sample validation
# on gold. Every other rule tried (5 legacy + 3 new hypotheses) was ruled
# out and its code deleted — see docs/superpowers/specs/strategy-ledger.md.
PROFITABLE_RULES = [
    'order_block_retest',
]
```

Replace the `TimeframeWorker.__init__` signature and body:

```python
    def __init__(
        self,
        timeframe: str,
        database_url: str,
        shared_dedup_subscriber,  # SHARED across all workers
        telegram_subscriber=None,
        enable_trading: bool = False,
        mt5_config: MT5Config = None
    ):
        """
        Initialize timeframe worker.

        Args:
            timeframe: Timeframe to monitor (e.g., '5m', '1h', '4h')
            database_url: Database connection URL
            shared_dedup_subscriber: Shared deduplication subscriber (same instance for all workers)
            telegram_subscriber: Shared Telegram subscriber, used here to notify on
                signal close (TP/SL/expiry) — separate from its role inside
                shared_dedup_subscriber, which notifies on signal creation
            enable_trading: Whether to enable auto-trading via MT5Subscriber
            mt5_config: MT5 configuration (required if enable_trading=True)
        """
        self.timeframe = timeframe
        self.database_url = database_url
```

with:

```python
    def __init__(
        self,
        spec: WorkerSpec,
        database_url: str,
        shared_dedup_subscriber,  # SHARED across all workers
        telegram_subscriber=None,
        enable_trading: bool = False,
        mt5_config: MT5Config = None
    ):
        """
        Initialize an instrument worker.

        Args:
            spec: WorkerSpec — symbol, strategy class, timeframe, tuned
                config filename for this worker
            database_url: Database connection URL
            shared_dedup_subscriber: Shared deduplication subscriber (same instance for all workers)
            telegram_subscriber: Shared Telegram subscriber, used here to notify on
                signal close (TP/SL/expiry) — separate from its role inside
                shared_dedup_subscriber, which notifies on signal creation
            enable_trading: Whether to enable auto-trading via MT5Subscriber
            mt5_config: MT5 configuration (required if enable_trading=True)
        """
        self.spec = spec
        self.database_url = database_url
```

Add properties right after `__init__` (before `start`):

```python
    @property
    def symbol(self) -> str:
        return self.spec.symbol

    @property
    def timeframe(self) -> str:
        return self.spec.timeframe

    @property
    def worker_id(self) -> str:
        return f"{self.spec.symbol}:{self.spec.timeframe}"
```

Remove the old `self.timeframe = timeframe` line's later duplicate reliance — `self.timeframe` is now a read-only property, so any other place in `__init__` that referenced `self.timeframe` needs no change since assignment only happened once, already removed above.

- [ ] **Step 4: Update `test_worker_restart.py`'s call sites**

In `packages/engine/tests/test_worker_restart.py`, replace:

```python
def _worker():
    return TimeframeWorker(
        timeframe='1h',
        database_url='sqlite:///:memory:',
        shared_dedup_subscriber=MagicMock(),
    )
```

with:

```python
def _worker():
    return TimeframeWorker(
        spec=svc_module.XAUUSD_1H_SPEC,
        database_url='sqlite:///:memory:',
        shared_dedup_subscriber=MagicMock(),
    )
```

And replace the second inline construction (inside `test_is_running_becomes_false_when_generator_start_raises`):

```python
        worker = TimeframeWorker(
            timeframe='1h',
            database_url=f"sqlite:///{tmp_path / 'db.sqlite'}",
            shared_dedup_subscriber=MagicMock(),
        )
```

with:

```python
        worker = TimeframeWorker(
            spec=svc_module.XAUUSD_1H_SPEC,
            database_url=f"sqlite:///{tmp_path / 'db.sqlite'}",
            shared_dedup_subscriber=MagicMock(),
        )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd packages/engine && ./venv/bin/python3 -m pytest tests/test_worker_spec.py tests/test_worker_restart.py -v`
Expected: PASS (all tests in both files).

- [ ] **Step 6: Commit**

```bash
git add packages/engine/run_multi_timeframe_service.py packages/engine/tests/test_worker_spec.py packages/engine/tests/test_worker_restart.py
git commit -m "feat: add WorkerSpec and make TimeframeWorker spec-driven"
```

---

### Task 2: `TimeframeWorker._run()` dispatches on `spec.symbol`/`spec.strategy_class`/`spec.tuned_config_filename`

**Files:**
- Modify: `packages/engine/run_multi_timeframe_service.py:168-301` (`TimeframeWorker._run`)
- Modify: `packages/engine/tests/test_timeframe_worker_lookback.py` (constructor + tuned config filename)
- Modify: `packages/engine/tests/test_settings_driven_rules.py` (constructor + tuned config filename helpers)
- Test: `packages/engine/tests/test_forex_worker_dispatch.py` (new)

**Interfaces:**
- Consumes: `WorkerSpec`, `XAUUSD_1H_SPEC`, `GBPUSD_1H_SPEC` from Task 1.
- Produces: `TimeframeWorker._run()` now calls `create_datafeed(symbol=self.spec.symbol, ...)`, instantiates `self.spec.strategy_class(...)`, loads `tuned_configs/{self.spec.tuned_config_filename}`, tolerates a tuned config without `enabled_rules`/`expiry_hours`, and sizes `lookback_periods` without assuming every strategy's config has a `trend_lookback` key.

- [ ] **Step 1: Write the failing test**

Create `packages/engine/tests/test_forex_worker_dispatch.py`:

```python
"""Regression coverage: TimeframeWorker._run() must dispatch on the
WorkerSpec's symbol/strategy_class instead of hardcoding XAUUSD/GoldStrategy,
and must tolerate GBPUSD/EURUSD's tuned config shape (no enabled_rules or
expiry_hours keys — confirmed by inspection, see
docs/superpowers/specs/2026-09-09-gbpusd-eurusd-worker-wiring-design.md)."""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import run_multi_timeframe_service as svc_module
from signals.forex_session_strategy import ForexSessionStrategy


def make_worker(spec, tmp_path):
    worker = svc_module.TimeframeWorker.__new__(svc_module.TimeframeWorker)
    worker.spec = spec
    worker.database_url = f"sqlite:///{tmp_path / 'settings.db'}"
    worker.shared_dedup_subscriber = MagicMock()
    worker.telegram_subscriber = MagicMock()
    worker.enable_trading = False
    worker.mt5_config = None
    return worker


class TestForexWorkerDispatch:
    def test_gbpusd_worker_creates_datafeed_for_gbpusd_not_gold(self, tmp_path, monkeypatch):
        monkeypatch.setattr(svc_module, "__file__", str(tmp_path / "run_multi_timeframe_service.py"))
        worker = make_worker(svc_module.GBPUSD_1H_SPEC, tmp_path)
        fake_generator = MagicMock()

        with patch.object(svc_module, "create_datafeed") as mock_create_feed, \
             patch.object(svc_module, "RealtimeSignalGenerator", return_value=fake_generator) as mock_generator_cls, \
             patch.object(svc_module, "SignalOutcomeTracker") as mock_tracker_cls:
            worker._run()

        assert mock_create_feed.call_args.kwargs["symbol"] == "GBPUSD"
        assert mock_tracker_cls.call_args.kwargs["symbol"] == "GBPUSD"
        assert isinstance(mock_generator_cls.call_args.kwargs["strategy"], ForexSessionStrategy)

    def test_gbpusd_tuned_config_without_enabled_rules_does_not_raise(self, tmp_path, monkeypatch):
        """gbpusd_1h.json has no `enabled_rules` key (unlike gold's 1h.json)
        — the loader must not KeyError."""
        monkeypatch.setattr(svc_module, "__file__", str(tmp_path / "run_multi_timeframe_service.py"))
        tuned_dir = tmp_path / "tuned_configs"
        tuned_dir.mkdir()
        (tuned_dir / "gbpusd_1h.json").write_text(json.dumps({
            "config": ForexSessionStrategy.DEFAULT_CONFIG,
            "enabled": True,
            "train": {"profit_factor": 1.1},
            "test": {"profit_factor": 1.58},
        }))
        worker = make_worker(svc_module.GBPUSD_1H_SPEC, tmp_path)
        fake_generator = MagicMock()

        with patch.object(svc_module, "create_datafeed"), \
             patch.object(svc_module, "RealtimeSignalGenerator", return_value=fake_generator), \
             patch.object(svc_module, "SignalOutcomeTracker") as mock_tracker_cls:
            worker._run()

        # No KeyError raised (test passing at all is the primary assertion);
        # also confirm the 48.0-hour fallback expiry was used.
        assert mock_tracker_cls.call_args.kwargs["expiry_hours"] == 48.0

    def test_gbpusd_tuned_config_without_enabled_rules_leaves_rule_at_constructor_default(self, tmp_path, monkeypatch):
        monkeypatch.setattr(svc_module, "__file__", str(tmp_path / "run_multi_timeframe_service.py"))
        tuned_dir = tmp_path / "tuned_configs"
        tuned_dir.mkdir()
        (tuned_dir / "gbpusd_1h.json").write_text(json.dumps({
            "config": ForexSessionStrategy.DEFAULT_CONFIG,
            "enabled": True,
            "train": {"profit_factor": 1.1},
            "test": {"profit_factor": 1.58},
        }))
        worker = make_worker(svc_module.GBPUSD_1H_SPEC, tmp_path)
        fake_generator = MagicMock()

        with patch.object(svc_module, "create_datafeed"), \
             patch.object(svc_module, "RealtimeSignalGenerator", return_value=fake_generator) as mock_generator_cls, \
             patch.object(svc_module, "SignalOutcomeTracker"):
            worker._run()

        strategy = mock_generator_cls.call_args.kwargs["strategy"]
        # ForexSessionStrategy's own constructor default is True — no
        # enabled_rules in the tuned config to override it with.
        assert strategy.rules_enabled == {"asian_range_london_breakout": True}

    def test_xauusd_worker_still_loads_1h_json_by_filename(self, tmp_path, monkeypatch):
        """Regression: tuned config path must come from
        spec.tuned_config_filename, not f'{timeframe}.json' derivation."""
        from signals.gold_strategy import GoldStrategy
        monkeypatch.setattr(svc_module, "__file__", str(tmp_path / "run_multi_timeframe_service.py"))
        tuned_dir = tmp_path / "tuned_configs"
        tuned_dir.mkdir()
        (tuned_dir / "1h.json").write_text(json.dumps({
            "config": {**GoldStrategy.DEFAULT_CONFIG, "trend_lookback": 200},
            "enabled_rules": ["order_block_retest"],
            "expiry_hours": 143,
        }))
        worker = make_worker(svc_module.XAUUSD_1H_SPEC, tmp_path)
        fake_generator = MagicMock()

        with patch.object(svc_module, "create_datafeed"), \
             patch.object(svc_module, "RealtimeSignalGenerator", return_value=fake_generator), \
             patch.object(svc_module, "SignalOutcomeTracker") as mock_tracker_cls:
            worker._run()

        assert mock_tracker_cls.call_args.kwargs["expiry_hours"] == 143

    def test_gbpusd_lookback_periods_does_not_crash_on_missing_trend_lookback(self, tmp_path, monkeypatch):
        """ForexSessionStrategy.config has no trend_lookback key at all (its
        own gate is lookback_candles + atr_period) — the existing
        lookback_periods calculation assumed every strategy has
        trend_lookback and would KeyError here without the fix."""
        monkeypatch.setattr(svc_module, "__file__", str(tmp_path / "run_multi_timeframe_service.py"))
        worker = make_worker(svc_module.GBPUSD_1H_SPEC, tmp_path)  # no tuned_configs dir — untuned default branch
        fake_generator = MagicMock()

        with patch.object(svc_module, "create_datafeed") as mock_create_feed, \
             patch.object(svc_module, "RealtimeSignalGenerator", return_value=fake_generator) as mock_generator_cls, \
             patch.object(svc_module, "SignalOutcomeTracker"):
            worker._run()  # must not raise KeyError

        # lookback_candles=12 + atr_period=14 + 50 = 76, floored to 200 by max(200, ...).
        assert mock_create_feed.call_args.kwargs["lookback_periods"] == 200
        assert mock_generator_cls.call_args.kwargs["lookback_periods"] == 200
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/engine && ./venv/bin/python3 -m pytest tests/test_forex_worker_dispatch.py -v`
Expected: FAIL — `KeyError: 'trend_lookback'` (every test in this file constructs a `ForexSessionStrategy` worker and calls `_run()`, which hits the unfixed `strategy.config['trend_lookback']` lookup immediately) alongside `AttributeError`/`KeyError: 'enabled_rules'` mismatches once that's fixed.

- [ ] **Step 3: Implement the dispatch and shape-tolerant loader**

In `packages/engine/run_multi_timeframe_service.py`, replace the tuned-config loading block:

```python
            # Load the tuned config for this timeframe if one exists;
            # otherwise fall back to defaults (no other timeframe has a
            # tuned config yet — see TIMEFRAMES above). Done before creating
            # the data feed/generator because both need lookback_periods
            # derived from the config actually in use (see below).
            tuned_config_path = Path(__file__).parent / 'tuned_configs' / f'{self.timeframe}.json'
            if tuned_config_path.exists():
                with open(tuned_config_path) as f:
                    tuned = json.load(f)
                strategy = GoldStrategy(config=tuned['config'])
                for name in strategy.rules_enabled:
                    strategy.rules_enabled[name] = name in tuned['enabled_rules']
                expiry_hours = tuned['expiry_hours']
                logger.info(f"   [{self.timeframe}] Loaded tuned config from {tuned_config_path}")
            else:
                strategy = GoldStrategy()
                expiry_hours = 48.0
                logger.warning(f"   [{self.timeframe}] No tuned config found at {tuned_config_path}, using untuned defaults")
```

with:

```python
            # Load the tuned config for this worker if one exists; otherwise
            # fall back to defaults. Done before creating the data
            # feed/generator because both need lookback_periods derived
            # from the config actually in use (see below).
            #
            # Config shape varies: gold's tuned_configs/1h.json has
            # `enabled_rules` (a multi-rule strategy's initial rule
            # selection) and `expiry_hours`; GBPUSD/EURUSD's tuned configs
            # (written by tune_forex_session_strategy.py) have neither —
            # ForexSessionStrategy has exactly one rule, and its live
            # enabled/disabled state comes entirely from the
            # enabled_forex_symbols DB setting via refresh_settings() below,
            # not from the tuned config file. See
            # docs/superpowers/specs/2026-09-09-gbpusd-eurusd-worker-wiring-design.md.
            tuned_config_path = Path(__file__).parent / 'tuned_configs' / self.spec.tuned_config_filename
            if tuned_config_path.exists():
                with open(tuned_config_path) as f:
                    tuned = json.load(f)
                strategy = self.spec.strategy_class(config=tuned['config'])
                if 'enabled_rules' in tuned:
                    for name in strategy.rules_enabled:
                        strategy.rules_enabled[name] = name in tuned['enabled_rules']
                expiry_hours = tuned.get('expiry_hours', 48.0)
                logger.info(f"   [{self.worker_id}] Loaded tuned config from {tuned_config_path}")
            else:
                strategy = self.spec.strategy_class()
                expiry_hours = 48.0
                logger.warning(f"   [{self.worker_id}] No tuned config found at {tuned_config_path}, using untuned defaults")
```

`lookback_periods` sizing must also branch on config shape — confirmed by
reading `ForexSessionStrategy.evaluate()`: its own gate is
`current_idx < config['lookback_candles'] + config['atr_period']`, and its
config has no `trend_lookback` key at all, so the existing
`strategy.config['trend_lookback']` lookup would `KeyError` immediately for
every GBPUSD/EURUSD worker start, tuned config or not. Replace:

```python
            # GoldStrategy.evaluate() refuses to evaluate any rule until
            # current_idx >= max(config['trend_lookback'], 60) (silently
            # returns None, no log, no exception). The data feed/generator
            # both default lookback_periods to 200 candles, which is a
            # no-op with the untuned default config (trend_lookback=50) but
            # is exactly equal to the 1h tuned config's trend_lookback=200 —
            # current_idx then maxes out at 199, permanently below the gate,
            # so no signal could ever fire. Size the fetch comfortably above
            # whatever the active config actually requires.
            lookback_periods = max(200, strategy.config['trend_lookback'] + 50)
```

with:

```python
            # GoldStrategy.evaluate() refuses to evaluate any rule until
            # current_idx >= max(config['trend_lookback'], 60) (silently
            # returns None, no log, no exception). The data feed/generator
            # both default lookback_periods to 200 candles, which is a
            # no-op with the untuned default config (trend_lookback=50) but
            # is exactly equal to the 1h tuned config's trend_lookback=200 —
            # current_idx then maxes out at 199, permanently below the gate,
            # so no signal could ever fire. Size the fetch comfortably above
            # whatever the active config actually requires.
            #
            # ForexSessionStrategy has no trend_lookback key at all — its
            # own gate is lookback_candles + atr_period (26 by default), a
            # much smaller window. Branch on which key the config actually
            # has rather than assuming gold's shape.
            if 'trend_lookback' in strategy.config:
                min_gate = strategy.config['trend_lookback']
            else:
                min_gate = strategy.config.get('lookback_candles', 0) + strategy.config.get('atr_period', 0)
            lookback_periods = max(200, min_gate + 50)
```

Replace the `create_datafeed(...)` call:

```python
            data_feed = create_datafeed(
                feed_type=datafeed_type,
                symbol='XAUUSD',
                timeframe=self.timeframe,
                lookback_periods=lookback_periods
            )
```

with:

```python
            data_feed = create_datafeed(
                feed_type=datafeed_type,
                symbol=self.spec.symbol,
                timeframe=self.timeframe,
                lookback_periods=lookback_periods
            )
```

Replace the `SignalOutcomeTracker(...)` call:

```python
            outcome_tracker = SignalOutcomeTracker(
                database_url=self.database_url,
                symbol='XAUUSD',
                timeframe=self.timeframe,
                expiry_hours=expiry_hours,
                telegram_subscriber=self.telegram_subscriber,
            )
```

with:

```python
            outcome_tracker = SignalOutcomeTracker(
                database_url=self.database_url,
                symbol=self.spec.symbol,
                timeframe=self.timeframe,
                expiry_hours=expiry_hours,
                telegram_subscriber=self.telegram_subscriber,
            )
```

Every other log line inside `_run()` that currently reads `f"   [{self.timeframe}] ..."` stays as-is (still accurate — it's the timeframe of this worker), except the two replaced above which are more useful worker-scoped.

- [ ] **Step 4: Update `test_timeframe_worker_lookback.py`**

Replace its `make_worker` helper:

```python
def make_worker(timeframe="1h"):
    worker = svc_module.TimeframeWorker.__new__(svc_module.TimeframeWorker)
    worker.timeframe = timeframe
    worker.database_url = "sqlite:///:memory:"
    worker.shared_dedup_subscriber = MagicMock()
    worker.telegram_subscriber = MagicMock()
    worker.enable_trading = False
    worker.mt5_config = None
    return worker
```

with:

```python
def make_worker(spec=None):
    spec = spec or svc_module.XAUUSD_1H_SPEC
    worker = svc_module.TimeframeWorker.__new__(svc_module.TimeframeWorker)
    worker.spec = spec
    worker.database_url = "sqlite:///:memory:"
    worker.shared_dedup_subscriber = MagicMock()
    worker.telegram_subscriber = MagicMock()
    worker.enable_trading = False
    worker.mt5_config = None
    return worker
```

Update its two call sites: `worker = make_worker("1h")` → `worker = make_worker()` (default is `XAUUSD_1H_SPEC`, whose `tuned_config_filename` is `'1h.json'`, matching what the test writes to `tuned_dir / "1h.json"`); `worker = make_worker("4h")` → this test relies on a timeframe with no tuned config file at all (`tuned_configs/4h.json` doesn't exist) to hit the untuned-default branch. Since `WORKER_SPECS` has no 4h spec, construct one inline: `worker = make_worker(svc_module.WorkerSpec(symbol='XAUUSD', strategy_class=svc_module.GoldStrategy, timeframe='4h', tuned_config_filename='4h.json'))`.

- [ ] **Step 5: Update `test_settings_driven_rules.py`'s tuned-config-writing helpers**

Replace both occurrences of:

```python
    (tuned_dir / f"{worker.timeframe}.json").write_text(json.dumps({
```

with:

```python
    (tuned_dir / worker.spec.tuned_config_filename).write_text(json.dumps({
```

(This file's `make_worker` helper is updated in Task 4 below, which also touches this file — do not duplicate that change here, only the two `tuned_dir / ...` lines.)

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd packages/engine && ./venv/bin/python3 -m pytest tests/test_forex_worker_dispatch.py tests/test_timeframe_worker_lookback.py -v`
Expected: PASS. (`test_settings_driven_rules.py` still fails at this point — its `make_worker` helper isn't updated until Task 4; that's expected and fixed there.)

- [ ] **Step 7: Commit**

```bash
git add packages/engine/run_multi_timeframe_service.py packages/engine/tests/test_forex_worker_dispatch.py packages/engine/tests/test_timeframe_worker_lookback.py packages/engine/tests/test_settings_driven_rules.py
git commit -m "feat: dispatch TimeframeWorker._run() on the worker spec, tolerate forex tuned config/lookback shape"
```

---

### Task 3: Rekey `last_processed_candle` to `worker_id`, add seed migration

**Files:**
- Modify: `packages/engine/run_multi_timeframe_service.py` (`get_last_processed_candle`/`save_last_processed_candle` closures in `_run`)
- Modify: `packages/engine/src/database/settings_models.py` (new `last_processed_candle_by_worker` setting, deprecate old one)
- Modify: `packages/engine/src/database/settings_repository.py` (`initialize_defaults`)
- Modify: `packages/engine/tests/test_settings_driven_rules.py` (`make_worker` helper, `test_keyed_by_timeframe_independently`)
- Test: `packages/engine/tests/test_last_processed_candle_by_worker.py` (new)

**Interfaces:**
- Consumes: `WorkerSpec`, `TimeframeWorker.worker_id` from Task 1.
- Produces: settings key `last_processed_candle_by_worker` (JSON dict, `{worker_id: iso_timestamp}`); `SettingsRepository.initialize_defaults()` seeds it from the old `last_processed_candle_by_timeframe["1h"]` once.

- [ ] **Step 1: Write the failing tests**

Create `packages/engine/tests/test_last_processed_candle_by_worker.py`:

```python
"""Regression coverage: last_processed_candle must be keyed by worker_id
(symbol:timeframe), not bare timeframe — two workers sharing a timeframe
string (e.g. XAUUSD:1h and GBPUSD:1h) must not corrupt each other's
restart-duplicate-signal protection. See the 2026-09-08 duplicate-signal
incident and docs/superpowers/specs/2026-09-09-gbpusd-eurusd-worker-wiring-design.md."""
import json
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import run_multi_timeframe_service as svc_module
from signals.gold_strategy import GoldStrategy
from signals.forex_session_strategy import ForexSessionStrategy
from database.connection import DatabaseManager
from database.models import Base
from database.settings_repository import SettingsRepository


def make_worker(spec, tmp_path):
    worker = svc_module.TimeframeWorker.__new__(svc_module.TimeframeWorker)
    worker.spec = spec
    worker.database_url = f"sqlite:///{tmp_path / 'settings.db'}"
    worker.shared_dedup_subscriber = MagicMock()
    worker.telegram_subscriber = MagicMock()
    worker.enable_trading = False
    worker.mt5_config = None
    return worker


def run_and_capture_candle_kwargs(worker, tmp_path):
    tuned_dir = tmp_path / "tuned_configs"
    tuned_dir.mkdir(exist_ok=True)
    if worker.spec.strategy_class is GoldStrategy:
        config = {**GoldStrategy.DEFAULT_CONFIG, "trend_lookback": 200}
        extra = {"enabled_rules": ["order_block_retest"], "expiry_hours": 143}
    else:
        config = ForexSessionStrategy.DEFAULT_CONFIG
        extra = {}
    (tuned_dir / worker.spec.tuned_config_filename).write_text(json.dumps({"config": config, **extra}))

    with patch.object(svc_module, "__file__", str(tmp_path / "run_multi_timeframe_service.py")), \
         patch.object(svc_module, "create_datafeed"), \
         patch.object(svc_module, "RealtimeSignalGenerator") as mock_generator_cls, \
         patch.object(svc_module, "SignalOutcomeTracker"):
        worker._run()

    kwargs = mock_generator_cls.call_args.kwargs
    return kwargs["last_processed_candle_getter"], kwargs["last_processed_candle_setter"]


class TestLastProcessedCandleKeyedByWorkerId:
    def test_same_timeframe_different_symbols_do_not_collide(self, tmp_path):
        gold_worker = make_worker(svc_module.XAUUSD_1H_SPEC, tmp_path)
        gold_get, gold_set = run_and_capture_candle_kwargs(gold_worker, tmp_path)
        gold_set(datetime(2026, 9, 8, 18, 0, 0))

        gbp_worker = make_worker(svc_module.GBPUSD_1H_SPEC, tmp_path)
        gbp_get, gbp_set = run_and_capture_candle_kwargs(gbp_worker, tmp_path)

        # GBPUSD:1h must not see XAUUSD:1h's recorded candle.
        assert gbp_get() is None
        assert gold_get() == datetime(2026, 9, 8, 18, 0, 0)

        gbp_set(datetime(2026, 9, 9, 7, 0, 0))
        # And setting GBPUSD's must not disturb gold's.
        assert gold_get() == datetime(2026, 9, 8, 18, 0, 0)
        assert gbp_get() == datetime(2026, 9, 9, 7, 0, 0)


class TestLastProcessedCandleSeedMigration:
    def _seed_old_setting(self, db_url, timeframe_value):
        db_manager = DatabaseManager(db_url)
        with db_manager.session_scope() as session:
            Base.metadata.create_all(bind=session.get_bind())
            repo = SettingsRepository(session)
            repo.initialize_defaults()
            setting = repo.get_setting('last_processed_candle_by_timeframe')
            setting.set_typed_value({'1h': timeframe_value})
            session.commit()

    def test_seeds_xauusd_1h_from_old_bare_timeframe_key(self, tmp_path):
        db_url = f"sqlite:///{tmp_path / 'migrate.db'}"
        self._seed_old_setting(db_url, '2026-09-08T18:00:00')

        db_manager = DatabaseManager(db_url)
        with db_manager.session_scope() as session:
            # A fresh SettingsRepository (simulating the next process
            # startup) re-running initialize_defaults() must perform the
            # seed migration.
            repo = SettingsRepository(session)
            repo.initialize_defaults()
            by_worker = repo.get('last_processed_candle_by_worker', default={})

        assert by_worker == {'XAUUSD:1h': '2026-09-08T18:00:00'}

    def test_does_not_reset_once_real_worker_data_exists(self, tmp_path):
        db_url = f"sqlite:///{tmp_path / 'migrate2.db'}"
        self._seed_old_setting(db_url, '2026-09-08T18:00:00')

        db_manager = DatabaseManager(db_url)
        with db_manager.session_scope() as session:
            repo = SettingsRepository(session)
            repo.initialize_defaults()  # first run performs the seed
            setting = repo.get_setting('last_processed_candle_by_worker')
            setting.set_typed_value({'XAUUSD:1h': '2026-09-09T07:00:00'})  # real data written since
            session.commit()

        with db_manager.session_scope() as session:
            repo = SettingsRepository(session)
            repo.initialize_defaults()  # second run must not clobber it
            by_worker = repo.get('last_processed_candle_by_worker', default={})

        assert by_worker == {'XAUUSD:1h': '2026-09-09T07:00:00'}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/engine && ./venv/bin/python3 -m pytest tests/test_last_processed_candle_by_worker.py -v`
Expected: FAIL — `KeyError: 'last_processed_candle_getter'` mismatches or `AssertionError` (setting `last_processed_candle_by_worker` doesn't exist yet).

- [ ] **Step 3: Add the new setting to `settings_models.py`**

In `packages/engine/src/database/settings_models.py`, find:

```python
    {
        'key': 'last_processed_candle_by_timeframe',
        'category': SettingCategory.SYSTEM,
        'value': '{}',
        'value_type': 'json',
        'default_value': '{}',
        'description': (
            "Internal: JSON map of timeframe -> ISO timestamp of the last "
            "candle actually evaluated for signals. Persisted so a worker "
            "restarted mid-candle (e.g. by a deploy) never re-evaluates and "
            "re-signals on a candle it already processed — see the "
            "2026-09-08 duplicate-signal incident in "
            "docs/superpowers/specs/strategy-ledger.md."
        ),
        'editable': False,
        'requires_restart': False,
    },
]
```

Replace with:

```python
    {
        'key': 'last_processed_candle_by_timeframe',
        'category': SettingCategory.SYSTEM,
        'value': '{}',
        'value_type': 'json',
        'default_value': '{}',
        'description': (
            "Deprecated: superseded by last_processed_candle_by_worker "
            "(keyed by \"SYMBOL:timeframe\" instead of bare timeframe, "
            "since two workers can share a timeframe string once more than "
            "one symbol runs live). Left in place, unread by any worker, "
            "only as the source for a one-time seed migration — see "
            "docs/superpowers/specs/2026-09-09-gbpusd-eurusd-worker-wiring-design.md."
        ),
        'editable': False,
        'requires_restart': False,
    },
    {
        'key': 'last_processed_candle_by_worker',
        'category': SettingCategory.SYSTEM,
        'value': '{}',
        'value_type': 'json',
        'default_value': '{}',
        'description': (
            "Internal: JSON map of \"SYMBOL:timeframe\" -> ISO timestamp of "
            "the last candle actually evaluated for signals. Persisted so a "
            "worker restarted mid-candle (e.g. by a deploy) never "
            "re-evaluates and re-signals on a candle it already processed "
            "— see the 2026-09-08 duplicate-signal incident in "
            "docs/superpowers/specs/strategy-ledger.md. Keyed by worker_id "
            "rather than bare timeframe so two workers on the same "
            "timeframe (e.g. XAUUSD:1h and GBPUSD:1h) don't collide."
        ),
        'editable': False,
        'requires_restart': False,
    },
]
```

- [ ] **Step 4: Add the seed migration to `settings_repository.py`**

In `packages/engine/src/database/settings_repository.py`, replace the end of `initialize_defaults`:

```python
        self.session.commit()
        logger.info(f"✅ Settings initialized ({len(DEFAULT_SETTINGS)} total)")
```

with:

```python
        self._migrate_last_processed_candle_by_worker()

        self.session.commit()
        logger.info(f"✅ Settings initialized ({len(DEFAULT_SETTINGS)} total)")

    def _migrate_last_processed_candle_by_worker(self):
        """
        One-time seed: if last_processed_candle_by_worker has never been
        written to (still its default {}) and the deprecated
        last_processed_candle_by_timeframe has a '1h' entry (gold's
        pre-migration data), seed XAUUSD:1h from it — preserves gold's
        restart-duplicate-signal protection across this deploy. A no-op
        forever after, once real per-worker data exists. See
        docs/superpowers/specs/2026-09-09-gbpusd-eurusd-worker-wiring-design.md.
        """
        by_worker_setting = self.session.query(Setting).filter_by(key='last_processed_candle_by_worker').first()
        old_setting = self.session.query(Setting).filter_by(key='last_processed_candle_by_timeframe').first()
        if not by_worker_setting or not old_setting:
            return

        by_worker = by_worker_setting.get_typed_value() or {}
        if by_worker:
            return  # already has real data — never overwrite

        old_value = old_setting.get_typed_value() or {}
        old_1h = old_value.get('1h')
        if old_1h:
            by_worker_setting.set_typed_value({'XAUUSD:1h': old_1h})
```

- [ ] **Step 5: Rekey the closures in `run_multi_timeframe_service.py`**

Replace:

```python
            def get_last_processed_candle():
                db_manager = DatabaseManager(self.database_url)
                with db_manager.session_scope() as session:
                    Base.metadata.create_all(bind=session.get_bind())
                    repo = SettingsRepository(session)
                    repo.initialize_defaults()
                    by_timeframe = repo.get('last_processed_candle_by_timeframe', default={}) or {}
                raw = by_timeframe.get(self.timeframe)
                return datetime.fromisoformat(raw) if raw else None

            def save_last_processed_candle(candle_time: datetime):
                db_manager = DatabaseManager(self.database_url)
                with db_manager.session_scope() as session:
                    Base.metadata.create_all(bind=session.get_bind())
                    repo = SettingsRepository(session)
                    repo.initialize_defaults()
                    setting = repo.get_setting('last_processed_candle_by_timeframe')
                    if setting:
                        by_timeframe = setting.get_typed_value() or {}
                        by_timeframe[self.timeframe] = candle_time.isoformat()
                        setting.set_typed_value(by_timeframe)
```

with:

```python
            def get_last_processed_candle():
                db_manager = DatabaseManager(self.database_url)
                with db_manager.session_scope() as session:
                    Base.metadata.create_all(bind=session.get_bind())
                    repo = SettingsRepository(session)
                    repo.initialize_defaults()
                    by_worker = repo.get('last_processed_candle_by_worker', default={}) or {}
                raw = by_worker.get(self.worker_id)
                return datetime.fromisoformat(raw) if raw else None

            def save_last_processed_candle(candle_time: datetime):
                db_manager = DatabaseManager(self.database_url)
                with db_manager.session_scope() as session:
                    Base.metadata.create_all(bind=session.get_bind())
                    repo = SettingsRepository(session)
                    repo.initialize_defaults()
                    setting = repo.get_setting('last_processed_candle_by_worker')
                    if setting:
                        by_worker = setting.get_typed_value() or {}
                        by_worker[self.worker_id] = candle_time.isoformat()
                        setting.set_typed_value(by_worker)
```

- [ ] **Step 6: Update `test_settings_driven_rules.py`**

Replace its `make_worker` helper:

```python
def make_worker(tmp_path, timeframe="1h"):
    worker = svc_module.TimeframeWorker.__new__(svc_module.TimeframeWorker)
    worker.timeframe = timeframe
    worker.database_url = f"sqlite:///{tmp_path / 'settings.db'}"
    worker.shared_dedup_subscriber = MagicMock()
    worker.telegram_subscriber = MagicMock()
    worker.enable_trading = False
    worker.mt5_config = None
    return worker
```

with:

```python
def make_worker(tmp_path, spec=None):
    spec = spec or svc_module.XAUUSD_1H_SPEC
    worker = svc_module.TimeframeWorker.__new__(svc_module.TimeframeWorker)
    worker.spec = spec
    worker.database_url = f"sqlite:///{tmp_path / 'settings.db'}"
    worker.shared_dedup_subscriber = MagicMock()
    worker.telegram_subscriber = MagicMock()
    worker.enable_trading = False
    worker.mt5_config = None
    return worker
```

Replace `test_keyed_by_timeframe_independently`:

```python
    def test_keyed_by_timeframe_independently(self, tmp_path):
        worker_1h = make_worker(tmp_path, timeframe="1h")
        kwargs_1h = run_worker_and_capture_all_kwargs(worker_1h, tmp_path)
        kwargs_1h["last_processed_candle_setter"](datetime(2026, 9, 8, 18, 0, 0))

        worker_15m = make_worker(tmp_path, timeframe="15m")
        kwargs_15m = run_worker_and_capture_all_kwargs(worker_15m, tmp_path)

        # A different timeframe's worker must not see 1h's recorded candle.
        assert kwargs_15m["last_processed_candle_getter"]() is None
```

with:

```python
    def test_keyed_by_worker_id_independently(self, tmp_path):
        worker_1h = make_worker(tmp_path, svc_module.WorkerSpec(
            symbol='XAUUSD', strategy_class=GoldStrategy, timeframe='1h', tuned_config_filename='1h.json'))
        kwargs_1h = run_worker_and_capture_all_kwargs(worker_1h, tmp_path)
        kwargs_1h["last_processed_candle_setter"](datetime(2026, 9, 8, 18, 0, 0))

        worker_15m = make_worker(tmp_path, svc_module.WorkerSpec(
            symbol='XAUUSD', strategy_class=GoldStrategy, timeframe='15m', tuned_config_filename='15m.json'))
        kwargs_15m = run_worker_and_capture_all_kwargs(worker_15m, tmp_path)

        # A different timeframe's worker must not see 1h's recorded candle.
        assert kwargs_15m["last_processed_candle_getter"]() is None
```

(`worker.timeframe` is used elsewhere in this file only inside the two `tuned_dir / worker.spec.tuned_config_filename` lines already fixed in Task 2 Step 5 — no other reference remains.)

- [ ] **Step 7: Run all affected tests to verify they pass**

Run: `cd packages/engine && ./venv/bin/python3 -m pytest tests/test_last_processed_candle_by_worker.py tests/test_settings_driven_rules.py tests/test_settings_metadata_sync.py -v`
Expected: PASS (all).

- [ ] **Step 8: Commit**

```bash
git add packages/engine/run_multi_timeframe_service.py packages/engine/src/database/settings_models.py packages/engine/src/database/settings_repository.py packages/engine/tests/test_last_processed_candle_by_worker.py packages/engine/tests/test_settings_driven_rules.py
git commit -m "fix: key last_processed_candle by worker_id, not bare timeframe"
```

---

### Task 4: `enabled_forex_symbols` setting + per-strategy `refresh_settings()` branching

**Files:**
- Modify: `packages/engine/src/database/settings_models.py` (new setting)
- Modify: `packages/engine/run_multi_timeframe_service.py` (`refresh_settings` closure in `_run`)
- Modify: `packages/engine/tests/test_settings_driven_rules.py` (new test class)

**Interfaces:**
- Consumes: `WorkerSpec.strategy_class`, `GoldStrategy`, `ForexSessionStrategy`.
- Produces: settings key `enabled_forex_symbols` (JSON list of symbol strings, default `[]`); `refresh_settings()` branches — gold's worker reads `enabled_strategies` exactly as before, a forex worker reads `enabled_forex_symbols`.

- [ ] **Step 1: Write the failing tests**

Append to `packages/engine/tests/test_settings_driven_rules.py` (new class, add near the bottom, after `TestLastProcessedCandlePersistence`):

```python
class TestForexSymbolEnabling:
    """Coverage for enabled_forex_symbols — a separate setting from
    enabled_strategies (which must keep its exact current shape/meaning,
    since apps/web's live admin toggle depends on it — see
    docs/superpowers/specs/2026-09-09-gbpusd-eurusd-worker-wiring-design.md)."""

    def _forex_worker(self, tmp_path, spec):
        worker = svc_module.TimeframeWorker.__new__(svc_module.TimeframeWorker)
        worker.spec = spec
        worker.database_url = f"sqlite:///{tmp_path / 'settings.db'}"
        worker.shared_dedup_subscriber = MagicMock()
        worker.telegram_subscriber = MagicMock()
        worker.enable_trading = False
        worker.mt5_config = None
        return worker

    def _run_and_capture_hook(self, worker, tmp_path):
        from signals.forex_session_strategy import ForexSessionStrategy
        tuned_dir = tmp_path / "tuned_configs"
        tuned_dir.mkdir(exist_ok=True)
        (tuned_dir / worker.spec.tuned_config_filename).write_text(
            json.dumps({"config": ForexSessionStrategy.DEFAULT_CONFIG})
        )
        with patch.object(svc_module, "__file__", str(tmp_path / "run_multi_timeframe_service.py")), \
             patch.object(svc_module, "create_datafeed"), \
             patch.object(svc_module, "RealtimeSignalGenerator") as mock_generator_cls, \
             patch.object(svc_module, "SignalOutcomeTracker"):
            worker._run()
        kwargs = mock_generator_cls.call_args.kwargs
        return kwargs["strategy"], kwargs["pre_run_hook"]

    def test_gbpusd_worker_disabled_by_default(self, tmp_path):
        worker = self._forex_worker(tmp_path, svc_module.GBPUSD_1H_SPEC)
        seed_settings(worker.database_url)  # defaults only — enabled_forex_symbols == []

        strategy, refresh = self._run_and_capture_hook(worker, tmp_path)
        refresh()

        assert strategy.rules_enabled["asian_range_london_breakout"] is False

    def test_gbpusd_worker_enabled_when_listed(self, tmp_path):
        worker = self._forex_worker(tmp_path, svc_module.GBPUSD_1H_SPEC)
        seed_settings(worker.database_url, enabled_forex_symbols=["GBPUSD"])

        strategy, refresh = self._run_and_capture_hook(worker, tmp_path)
        refresh()

        assert strategy.rules_enabled["asian_range_london_breakout"] is True

    def test_eurusd_unaffected_by_gbpusd_being_enabled(self, tmp_path):
        worker = self._forex_worker(tmp_path, svc_module.EURUSD_1H_SPEC)
        seed_settings(worker.database_url, enabled_forex_symbols=["GBPUSD"])

        strategy, refresh = self._run_and_capture_hook(worker, tmp_path)
        refresh()

        assert strategy.rules_enabled["asian_range_london_breakout"] is False

    def test_gold_worker_still_reads_enabled_strategies_unchanged(self, tmp_path):
        """Regression: gold's own settings-driven behavior (already covered
        above in TestSettingsDrivenRuleEnabling) must be completely
        unaffected by enabled_forex_symbols existing."""
        worker = make_worker(tmp_path)
        seed_settings(
            worker.database_url,
            enabled_strategies=["order_block_retest"],
            enabled_forex_symbols=["GBPUSD", "EURUSD"],
        )

        strategy, _validator, refresh = run_worker_and_capture_hook(worker, tmp_path)
        refresh()

        assert strategy.rules_enabled == {"order_block_retest": True}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/engine && ./venv/bin/python3 -m pytest tests/test_settings_driven_rules.py::TestForexSymbolEnabling -v`
Expected: FAIL — `strategy.rules_enabled["asian_range_london_breakout"]` stays at its constructor default (`True`) regardless of settings, since nothing reads `enabled_forex_symbols` yet.

- [ ] **Step 3: Add the setting**

In `packages/engine/src/database/settings_models.py`, find the `enabled_strategies` entry and insert a new entry immediately after its closing `},`:

```python
    {
        'key': 'enabled_strategies',
        'category': SettingCategory.STRATEGIES,
        # Only order_block_retest survived shared-config, out-of-sample
        # validation — every other rule tried (5 legacy + 3 new hypotheses)
        # was ruled out and its code deleted; see
        # docs/superpowers/specs/strategy-ledger.md. Listing a ruled-out
        # name here is harmless (GoldStrategy.rules_enabled simply has no
        # such key to toggle), but there's nothing left to enable.
        'value': '["order_block_retest"]',
        'value_type': 'json',
        'default_value': '["order_block_retest"]',
        'description': 'List of enabled trading strategies (applied live, on the next candle close — no restart needed)',
        'editable': True,
        'requires_restart': False,
    },
```

Insert directly after it:

```python
    {
        'key': 'enabled_forex_symbols',
        'category': SettingCategory.STRATEGIES,
        # GBPUSD/EURUSD's ForexSessionStrategy worker runs live (real data
        # feed, heartbeat, restart-protection) from the moment it's
        # deployed, but its single rule (asian_range_london_breakout) only
        # fires for a symbol listed here. Empty by default — both symbols
        # ship disabled until explicitly approved to go live. See
        # docs/superpowers/specs/2026-09-09-gbpusd-eurusd-worker-wiring-design.md.
        # Deliberately a separate setting from enabled_strategies, which
        # keeps its exact current shape/meaning (a flat list of gold rule
        # names) since apps/web's live admin toggle depends on that shape.
        'value': '[]',
        'value_type': 'json',
        'default_value': '[]',
        'description': 'Forex symbols (GBPUSD/EURUSD) whose ForexSessionStrategy rule is live (applied on the next candle close — no restart needed)',
        'editable': True,
        'requires_restart': False,
    },
```

- [ ] **Step 4: Implement the branch in `refresh_settings()`**

In `packages/engine/run_multi_timeframe_service.py`, replace:

```python
            def refresh_settings():
                db_manager = DatabaseManager(self.database_url)
                with db_manager.session_scope() as session:
                    Base.metadata.create_all(bind=session.get_bind())
                    repo = SettingsRepository(session)
                    repo.initialize_defaults()
                    enabled_list = repo.get('enabled_strategies', default=None)
                    min_confidence = repo.get('min_confidence', default=None)
                    min_rr_ratio = repo.get('min_rr_ratio', default=None)

                if enabled_list is not None:
                    for name in strategy.rules_enabled:
                        strategy.set_rule_enabled(name, name in enabled_list)
                if min_confidence is not None:
                    validator.min_confidence = min_confidence
                if min_rr_ratio is not None:
                    validator.min_rr_ratio = min_rr_ratio

                effective = [name for name, on in strategy.rules_enabled.items() if on]
                logger.info(
                    f"   [{self.timeframe}] Settings refreshed — enabled rules: {effective}, "
                    f"min_confidence={validator.min_confidence}, min_rr_ratio={validator.min_rr_ratio}"
                )
```

with:

```python
            def refresh_settings():
                db_manager = DatabaseManager(self.database_url)
                with db_manager.session_scope() as session:
                    Base.metadata.create_all(bind=session.get_bind())
                    repo = SettingsRepository(session)
                    repo.initialize_defaults()
                    enabled_list = repo.get('enabled_strategies', default=None)
                    enabled_forex_symbols = repo.get('enabled_forex_symbols', default=[]) or []
                    min_confidence = repo.get('min_confidence', default=None)
                    min_rr_ratio = repo.get('min_rr_ratio', default=None)

                if self.spec.strategy_class is GoldStrategy:
                    if enabled_list is not None:
                        for name in strategy.rules_enabled:
                            strategy.set_rule_enabled(name, name in enabled_list)
                else:
                    # A forex worker's single rule is gated by symbol
                    # membership in enabled_forex_symbols, not by rule name
                    # — GBPUSD and EURUSD both use the same rule name
                    # (asian_range_london_breakout), which enabled_strategies
                    # can't disambiguate between symbols.
                    for name in strategy.rules_enabled:
                        strategy.set_rule_enabled(name, self.spec.symbol in enabled_forex_symbols)
                if min_confidence is not None:
                    validator.min_confidence = min_confidence
                if min_rr_ratio is not None:
                    validator.min_rr_ratio = min_rr_ratio

                effective = [name for name, on in strategy.rules_enabled.items() if on]
                logger.info(
                    f"   [{self.worker_id}] Settings refreshed — enabled rules: {effective}, "
                    f"min_confidence={validator.min_confidence}, min_rr_ratio={validator.min_rr_ratio}"
                )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd packages/engine && ./venv/bin/python3 -m pytest tests/test_settings_driven_rules.py -v`
Expected: PASS (all classes in the file, including the pre-existing `TestSettingsDrivenRuleEnabling`/`TestLastProcessedCandlePersistence` classes — full-file regression check).

- [ ] **Step 6: Commit**

```bash
git add packages/engine/src/database/settings_models.py packages/engine/run_multi_timeframe_service.py packages/engine/tests/test_settings_driven_rules.py
git commit -m "feat: add enabled_forex_symbols setting, gate ForexSessionStrategy per symbol"
```

---

### Task 5: `MultiTimeframeService` runs all `WORKER_SPECS`, `self.workers` keyed by `worker_id`

**Files:**
- Modify: `packages/engine/run_multi_timeframe_service.py:360-460` (`MultiTimeframeService.__init__`, `.start()`, `._display_status()`)
- Modify: `packages/engine/tests/test_timeframe_scope.py`
- Test: `packages/engine/tests/test_multi_timeframe_service_specs.py` (new)

**Interfaces:**
- Consumes: `WORKER_SPECS`, `TimeframeWorker.worker_id` from Tasks 1–4.
- Produces: `MultiTimeframeService.worker_specs` (list, defaults to `WORKER_SPECS`); `self.workers` dict keyed by `worker_id` instead of bare timeframe.

- [ ] **Step 1: Write the failing test**

Create `packages/engine/tests/test_multi_timeframe_service_specs.py`:

```python
"""Regression coverage: MultiTimeframeService must construct one worker per
WORKER_SPECS entry (not just gold), keyed by worker_id in self.workers."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import run_multi_timeframe_service as svc_module


class TestMultiTimeframeServiceWorkerSpecs:
    def test_default_worker_specs_is_the_module_constant(self):
        service = svc_module.MultiTimeframeService.__new__(svc_module.MultiTimeframeService)
        service.worker_specs = None or svc_module.WORKER_SPECS
        assert service.worker_specs == svc_module.WORKER_SPECS

    def test_start_constructs_one_worker_per_spec_keyed_by_worker_id(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "fake-chat-id")

        with patch.object(svc_module, "DatabaseSubscriber"), \
             patch.object(svc_module, "TelegramSubscriber"), \
             patch.object(svc_module, "DeduplicationSubscriber"), \
             patch.object(svc_module, "TimeframeWorker") as mock_worker_cls, \
             patch("time.sleep"):
            mock_instances = []

            def _make_worker(spec, **kwargs):
                inst = MagicMock()
                inst.spec = spec
                inst.worker_id = f"{spec.symbol}:{spec.timeframe}"
                mock_instances.append(inst)
                return inst

            mock_worker_cls.side_effect = _make_worker

            service = svc_module.MultiTimeframeService(database_url=f"sqlite:///{tmp_path / 'db.sqlite'}")
            service._monitor_loop = MagicMock()  # don't actually loop forever
            service.start()

        assert set(service.workers.keys()) == {'XAUUSD:1h', 'GBPUSD:1h', 'EURUSD:1h'}
        assert mock_worker_cls.call_count == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/engine && ./venv/bin/python3 -m pytest tests/test_multi_timeframe_service_specs.py -v`
Expected: FAIL — `AttributeError` (`worker_specs` doesn't exist) and/or `service.workers.keys()` only contains `{'1h'}` (`TIMEFRAMES` still drives construction, one worker).

- [ ] **Step 3: Implement**

In `packages/engine/run_multi_timeframe_service.py`, replace in `MultiTimeframeService.__init__`:

```python
    def __init__(self, timeframes: List[str] = None, database_url: str = None, enable_trading: bool = False):
        """
        Initialize multi-timeframe service.

        Args:
            timeframes: List of timeframes to monitor (default: all)
            database_url: Database URL (default: from env or PostgreSQL)
            enable_trading: Whether to enable auto-trading (default: False, signals only)
        """
        self.timeframes = timeframes or TIMEFRAMES
```

with:

```python
    def __init__(self, worker_specs: List[WorkerSpec] = None, database_url: str = None, enable_trading: bool = False):
        """
        Initialize multi-timeframe service.

        Args:
            worker_specs: WorkerSpecs to run (default: WORKER_SPECS — all
                configured instruments)
            database_url: Database URL (default: from env or PostgreSQL)
            enable_trading: Whether to enable auto-trading (default: False, signals only)
        """
        self.worker_specs = worker_specs or WORKER_SPECS
```

Replace the print loop and worker-construction loop in `start()`:

```python
        print(f"\n🎯 Monitoring Timeframes: {', '.join(self.timeframes)}")
        for timeframe in self.timeframes:
            tuned_config_path = Path(__file__).parent / 'tuned_configs' / f'{timeframe}.json'
            if tuned_config_path.exists():
                with open(tuned_config_path) as f:
                    enabled = json.load(f)['enabled_rules']
            else:
                enabled = PROFITABLE_RULES
            print(f"📈 [{timeframe}] Enabled Rules ({len(enabled)}):")
            for rule in enabled:
                print(f"   ✅ {rule}")
```

with:

```python
        worker_ids = [f"{spec.symbol}:{spec.timeframe}" for spec in self.worker_specs]
        print(f"\n🎯 Monitoring Workers: {', '.join(worker_ids)}")
        for spec in self.worker_specs:
            worker_id = f"{spec.symbol}:{spec.timeframe}"
            tuned_config_path = Path(__file__).parent / 'tuned_configs' / spec.tuned_config_filename
            if tuned_config_path.exists():
                with open(tuned_config_path) as f:
                    tuned = json.load(f)
                enabled = tuned.get('enabled_rules', list(spec.strategy_class().rules_enabled.keys()))
            else:
                enabled = PROFITABLE_RULES if spec.symbol == 'XAUUSD' else []
            print(f"📈 [{worker_id}] Rules in tuned config ({len(enabled)}):")
            for rule in enabled:
                print(f"   ✅ {rule}")
```

Replace:

```python
        # Create and start workers for each timeframe
        for timeframe in self.timeframes:
            worker = TimeframeWorker(
                timeframe=timeframe,
                database_url=self.database_url,
                shared_dedup_subscriber=self.shared_dedup_subscriber,  # SHARE the same instance
                telegram_subscriber=self.telegram_subscriber,
                enable_trading=self.enable_trading,
                mt5_config=self.mt5_config
            )
            self.workers[timeframe] = worker
            worker.start()
            time.sleep(2)  # Stagger starts to avoid overwhelming the API
```

with:

```python
        # Create and start one worker per configured instrument
        for spec in self.worker_specs:
            worker = TimeframeWorker(
                spec=spec,
                database_url=self.database_url,
                shared_dedup_subscriber=self.shared_dedup_subscriber,  # SHARE the same instance
                telegram_subscriber=self.telegram_subscriber,
                enable_trading=self.enable_trading,
                mt5_config=self.mt5_config
            )
            self.workers[worker.worker_id] = worker
            worker.start()
            time.sleep(2)  # Stagger starts to avoid overwhelming the API
```

Replace the `_display_status` loop variable name for clarity (behavior unchanged, `self.workers` already correctly keyed once the above lands):

```python
        # Show status of each worker
        for timeframe, worker in self.workers.items():
            status = "🟢 RUNNING" if worker.is_running else "🔴 STOPPED"
            signals = worker.generator.total_signals_generated if worker.generator else 0
            candles = worker.generator.total_candles_processed if worker.generator else 0

            print(f"{timeframe:>4} | {status} | Candles: {candles:>5} | Signals: {signals:>3}")
```

with:

```python
        # Show status of each worker
        for worker_id, worker in self.workers.items():
            status = "🟢 RUNNING" if worker.is_running else "🔴 STOPPED"
            signals = worker.generator.total_signals_generated if worker.generator else 0
            candles = worker.generator.total_candles_processed if worker.generator else 0

            print(f"{worker_id:>10} | {status} | Candles: {candles:>5} | Signals: {signals:>3}")
```

Finally, update `main()`'s CLI: the `--timeframes` flag filtered `TIMEFRAMES` down to a subset — with `WORKER_SPECS` now the multi-instrument source of truth, replace it with `--symbols`, filtering `WORKER_SPECS` by symbol (kept for local dev convenience — e.g. running only gold locally without touching forex):

```python
    parser.add_argument(
        '--timeframes', '-t',
        nargs='+',
        choices=['5m', '15m', '30m', '1h', '4h', '1d'],
        help='Timeframes to monitor (default: all)'
    )
```

with:

```python
    parser.add_argument(
        '--symbols', '-s',
        nargs='+',
        choices=[spec.symbol for spec in WORKER_SPECS],
        help='Symbols to run workers for (default: all configured symbols)'
    )
```

And its usage:

```python
    service = MultiTimeframeService(
        timeframes=args.timeframes,
        database_url=args.database,
        enable_trading=enable_trading
    )
```

with:

```python
    worker_specs = (
        [spec for spec in WORKER_SPECS if spec.symbol in args.symbols]
        if args.symbols else None
    )
    service = MultiTimeframeService(
        worker_specs=worker_specs,
        database_url=args.database,
        enable_trading=enable_trading
    )
```

- [ ] **Step 4: Update `test_timeframe_scope.py`**

Replace:

```python
"""Confirms the live service is scoped to the validated 1H timeframe only."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import run_multi_timeframe_service as svc_module


class TestTimeframeScope:
    def test_only_1h_is_configured(self):
        assert svc_module.TIMEFRAMES == ['1h']
```

with:

```python
"""Confirms every configured worker runs the validated 1H timeframe, and
exactly the three instruments this design wires in."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import run_multi_timeframe_service as svc_module


class TestTimeframeScope:
    def test_every_worker_spec_is_1h(self):
        assert all(spec.timeframe == '1h' for spec in svc_module.WORKER_SPECS)

    def test_worker_specs_cover_exactly_these_symbols(self):
        assert {spec.symbol for spec in svc_module.WORKER_SPECS} == {'XAUUSD', 'GBPUSD', 'EURUSD'}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd packages/engine && ./venv/bin/python3 -m pytest tests/test_multi_timeframe_service_specs.py tests/test_timeframe_scope.py tests/test_worker_heartbeat.py tests/test_weekly_report.py tests/test_weekly_report_timer_persistence.py -v`
Expected: PASS (the heartbeat/weekly-report files are included here as a regression check — they construct `self.workers`/`MultiTimeframeService` independently of `worker_specs` and must be unaffected).

- [ ] **Step 6: Commit**

```bash
git add packages/engine/run_multi_timeframe_service.py packages/engine/tests/test_timeframe_scope.py packages/engine/tests/test_multi_timeframe_service_specs.py
git commit -m "feat: MultiTimeframeService runs all WORKER_SPECS, workers keyed by worker_id"
```

---

### Task 6: `YahooFinanceDataFeed.ticker_map` fix

**Files:**
- Modify: `packages/engine/src/data/realtime_feed.py:190-209`
- Test: `packages/engine/tests/test_ticker_map.py` (new)

**Interfaces:**
- Produces: `YahooFinanceDataFeed.ticker_map` includes `GBPUSD`/`EURUSD`; `.connect()` raises `ValueError` for an unmapped symbol instead of silently defaulting to `GC=F`.

- [ ] **Step 1: Write the failing test**

Create `packages/engine/tests/test_ticker_map.py`:

```python
"""Regression coverage: YahooFinanceDataFeed.ticker_map silently fell back
to gold's ticker (GC=F) for any unmapped symbol — a real bug that would
have made a GBPUSD worker silently fetch gold data. See
docs/superpowers/specs/2026-09-09-gbpusd-eurusd-worker-wiring-design.md."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.realtime_feed import YahooFinanceDataFeed


class TestTickerMap:
    def test_gbpusd_maps_to_gbpusd_equals_x(self):
        feed = YahooFinanceDataFeed(symbol="GBPUSD", timeframe="1h")
        assert feed.ticker_map["GBPUSD"] == "GBPUSD=X"

    def test_eurusd_maps_to_eurusd_equals_x(self):
        feed = YahooFinanceDataFeed(symbol="EURUSD", timeframe="1h")
        assert feed.ticker_map["EURUSD"] == "EURUSD=X"

    def test_xauusd_still_maps_to_gc_equals_f(self):
        feed = YahooFinanceDataFeed(symbol="XAUUSD", timeframe="1h")
        assert feed.ticker_map["XAUUSD"] == "GC=F"

    def test_connect_raises_for_unmapped_symbol_instead_of_silently_using_gold(self):
        feed = YahooFinanceDataFeed(symbol="NOTASYMBOL", timeframe="1h")
        with pytest.raises(ValueError, match="NOTASYMBOL"):
            feed.connect()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/engine && ./venv/bin/python3 -m pytest tests/test_ticker_map.py -v`
Expected: FAIL — `KeyError: 'GBPUSD'` (not in `ticker_map` yet) and the unmapped-symbol test fails to raise (silently succeeds using `GC=F`).

- [ ] **Step 3: Implement**

In `packages/engine/src/data/realtime_feed.py`, replace:

```python
        # Map XAUUSD to Yahoo ticker
        self.ticker_map = {
            "XAUUSD": "GC=F",  # Gold futures
            "XAGUSD": "SI=F",  # Silver futures
        }

    def connect(self) -> bool:
        """Initialize Yahoo Finance connection."""
        try:
            import yfinance as yf
            self.yf_ticker = yf.Ticker(self.ticker_map.get(self.symbol, "GC=F"))
            self.is_connected = True
            print(f"✅ Connected to Yahoo Finance ({self.ticker_map.get(self.symbol)})")
            return True
        except ImportError:
            print("❌ yfinance not installed. Install with: pip install yfinance")
            return False
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
```

with:

```python
        # Map internal symbol to Yahoo Finance ticker. No fallback default —
        # an unmapped symbol must fail loudly (connect() raises) rather than
        # silently fetching gold data, which is what a bare `.get(symbol,
        # "GC=F")` used to do. See
        # docs/superpowers/specs/2026-09-09-gbpusd-eurusd-worker-wiring-design.md.
        self.ticker_map = {
            "XAUUSD": "GC=F",     # Gold futures
            "XAGUSD": "SI=F",     # Silver futures
            "GBPUSD": "GBPUSD=X",
            "EURUSD": "EURUSD=X",
        }

    def connect(self) -> bool:
        """Initialize Yahoo Finance connection."""
        if self.symbol not in self.ticker_map:
            raise ValueError(
                f"No Yahoo Finance ticker mapping for symbol '{self.symbol}' "
                f"— known symbols: {sorted(self.ticker_map.keys())}"
            )
        try:
            import yfinance as yf
            self.yf_ticker = yf.Ticker(self.ticker_map[self.symbol])
            self.is_connected = True
            print(f"✅ Connected to Yahoo Finance ({self.ticker_map[self.symbol]})")
            return True
        except ImportError:
            print("❌ yfinance not installed. Install with: pip install yfinance")
            return False
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/engine && ./venv/bin/python3 -m pytest tests/test_ticker_map.py tests/test_realtime_feed_timeframe_case.py tests/test_realtime_feed_end_date.py tests/test_realtime_feed_timezone.py -v`
Expected: PASS (all — including the pre-existing realtime_feed tests, unaffected by this change).

- [ ] **Step 5: Commit**

```bash
git add packages/engine/src/data/realtime_feed.py packages/engine/tests/test_ticker_map.py
git commit -m "fix: add GBPUSD/EURUSD to ticker_map, raise on unmapped symbol instead of silently fetching gold"
```

---

### Task 7: `worker_status.derive_worker_status` accepts `worker_id`, drops the arbitrary-fallback

**Files:**
- Modify: `packages/api/src/worker_status.py`
- Modify: `packages/api/tests/test_worker_status.py`

**Interfaces:**
- Produces: `derive_worker_status(heartbeat: dict, worker_id: str, now: datetime, stale_after_seconds: int = 120) -> WorkerStatus`.

- [ ] **Step 1: Update the test file (write failing tests first)**

Replace `packages/api/tests/test_worker_status.py` in full:

```python
"""Tests for deriving live worker status from the engine's persisted
heartbeat (see packages/engine/run_multi_timeframe_service.py's
_save_heartbeat). Pure logic, no DB/FastAPI needed.
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from worker_status import derive_worker_status


NOW = datetime(2026, 9, 7, 22, 0, 0)


def heartbeat_at(age_seconds, worker_id='XAUUSD:1h', **worker_kwargs):
    updated_at = NOW - timedelta(seconds=age_seconds)
    worker = {'is_running': True, 'candles_processed': 80, 'signals_generated': 1}
    worker.update(worker_kwargs)
    return {
        'updated_at': updated_at.isoformat(),
        'start_time': datetime(2026, 9, 4, 12, 0, 0).isoformat(),
        'workers': {worker_id: worker},
    }


class TestDeriveWorkerStatus:
    def test_no_heartbeat_yet_reports_unknown_not_running(self):
        result = derive_worker_status({}, worker_id='XAUUSD:1h', now=NOW)
        assert result.is_running is False
        assert result.candles_processed == 0
        assert result.signals_generated == 0
        assert result.uptime_hours is None

    def test_fresh_heartbeat_with_running_worker_reports_running(self):
        heartbeat = heartbeat_at(age_seconds=10)
        result = derive_worker_status(heartbeat, worker_id='XAUUSD:1h', now=NOW)
        assert result.is_running is True
        assert result.candles_processed == 80
        assert result.signals_generated == 1
        assert result.uptime_hours == expected_uptime_hours(NOW, datetime(2026, 9, 4, 12, 0, 0))

    def test_stale_heartbeat_reports_not_running_even_if_worker_said_running(self):
        heartbeat = heartbeat_at(age_seconds=999, is_running=True)
        result = derive_worker_status(heartbeat, worker_id='XAUUSD:1h', now=NOW, stale_after_seconds=120)
        assert result.is_running is False
        # counts still reported — last known values, just not "live"
        assert result.candles_processed == 80

    def test_stale_heartbeat_reports_no_uptime(self):
        """A crashed worker shouldn't show an ever-growing uptime next to status=stopped."""
        heartbeat = heartbeat_at(age_seconds=999, is_running=True)
        result = derive_worker_status(heartbeat, worker_id='XAUUSD:1h', now=NOW, stale_after_seconds=120)
        assert result.uptime_hours is None

    def test_worker_reporting_itself_stopped_is_not_running_even_if_heartbeat_fresh(self):
        heartbeat = heartbeat_at(age_seconds=5, is_running=False)
        result = derive_worker_status(heartbeat, worker_id='XAUUSD:1h', now=NOW)
        assert result.is_running is False

    def test_worker_reporting_itself_stopped_reports_no_uptime(self):
        heartbeat = heartbeat_at(age_seconds=5, is_running=False)
        result = derive_worker_status(heartbeat, worker_id='XAUUSD:1h', now=NOW)
        assert result.uptime_hours is None

    def test_unknown_worker_id_reports_not_running_no_arbitrary_fallback(self):
        """Regression: with more than one worker in the heartbeat, a
        worker_id miss must report 'not running', never silently grab a
        different worker's data (the old bare-timeframe fallback's own
        comment flagged this exact gap)."""
        heartbeat = heartbeat_at(age_seconds=5, worker_id='GBPUSD:1h')
        result = derive_worker_status(heartbeat, worker_id='XAUUSD:1h', now=NOW)
        assert result.is_running is False
        assert result.candles_processed == 0

    def test_distinguishes_two_workers_in_the_same_heartbeat(self):
        heartbeat = {
            'updated_at': NOW.isoformat(),
            'start_time': datetime(2026, 9, 4, 12, 0, 0).isoformat(),
            'workers': {
                'XAUUSD:1h': {'is_running': True, 'candles_processed': 80, 'signals_generated': 1},
                'GBPUSD:1h': {'is_running': True, 'candles_processed': 12, 'signals_generated': 0},
            },
        }
        gold = derive_worker_status(heartbeat, worker_id='XAUUSD:1h', now=NOW)
        gbp = derive_worker_status(heartbeat, worker_id='GBPUSD:1h', now=NOW)
        assert gold.candles_processed == 80
        assert gbp.candles_processed == 12


def expected_uptime_hours(now, start_time):
    return (now - start_time).total_seconds() / 3600
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/api && ../engine/venv/bin/python3 -m pytest tests/test_worker_status.py -v` (`packages/api` has no venv of its own — confirmed by inspection — it always runs against the engine's venv at `packages/engine/venv`, which has `fastapi`/`pytest`/etc. installed; the system `python3` does not have `pytest` installed at all)
Expected: FAIL — `TypeError: derive_worker_status() got an unexpected keyword argument 'worker_id'`.

- [ ] **Step 3: Implement**

Replace `packages/api/src/worker_status.py` in full:

```python
"""
Derives live worker status from the engine's persisted heartbeat, shared by
the /v1/signals/service/status and /v1/settings/service/status routes.

The worker (MultiTimeframeService._save_heartbeat, in
packages/engine/run_multi_timeframe_service.py) writes a JSON heartbeat to
the `worker_heartbeat` setting roughly every 15s. Reading it directly here
(instead of each route re-deriving liveness from signal staleness) is what
lets a worker be reported "running" even when it hasn't generated a new
signal in a while.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

# The worker writes a heartbeat roughly every 15s — anything older than this
# means the worker process itself has stopped updating it (crashed, hung, or
# never started this deploy), regardless of what it last reported.
DEFAULT_STALE_AFTER_SECONDS = 120


@dataclass
class WorkerStatus:
    is_running: bool
    candles_processed: int
    signals_generated: int
    uptime_hours: Optional[float]


def derive_worker_status(
    heartbeat: Dict[str, Any],
    worker_id: str,
    now: datetime,
    stale_after_seconds: int = DEFAULT_STALE_AFTER_SECONDS,
) -> WorkerStatus:
    """Compute real worker status from a heartbeat payload (see module
    docstring). worker_id is "SYMBOL:timeframe" (e.g. "XAUUSD:1h") — an
    exact key lookup, no fallback to a different worker's data, since
    worker IDs are unambiguous once every worker has its own symbol."""
    heartbeat = heartbeat or {}
    workers = heartbeat.get('workers') or {}
    worker_data = workers.get(worker_id)

    if worker_data is None:
        return WorkerStatus(is_running=False, candles_processed=0, signals_generated=0, uptime_hours=None)

    updated_at_raw = heartbeat.get('updated_at')
    heartbeat_age_seconds = (
        (now - datetime.fromisoformat(updated_at_raw)).total_seconds() if updated_at_raw else None
    )
    is_fresh = heartbeat_age_seconds is not None and heartbeat_age_seconds < stale_after_seconds
    is_running = bool(worker_data.get('is_running')) and is_fresh

    # Only report uptime while the worker is actually confirmed running —
    # otherwise a crashed worker would show an ever-growing uptime next to
    # status=stopped, computed from a start_time that's no longer meaningful.
    uptime_hours = None
    start_time_raw = heartbeat.get('start_time')
    if is_running and start_time_raw:
        uptime_hours = (now - datetime.fromisoformat(start_time_raw)).total_seconds() / 3600

    return WorkerStatus(
        is_running=is_running,
        candles_processed=worker_data.get('candles_processed', 0),
        signals_generated=worker_data.get('signals_generated', 0),
        uptime_hours=uptime_hours,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/api && ../engine/venv/bin/python3 -m pytest tests/test_worker_status.py -v`
Expected: PASS (all).

- [ ] **Step 5: Commit**

```bash
git add packages/api/src/worker_status.py packages/api/tests/test_worker_status.py
git commit -m "fix: derive_worker_status takes worker_id, no arbitrary fallback across workers"
```

---

### Task 8: `/service/status` endpoints construct gold's `worker_id` explicitly

**Files:**
- Modify: `packages/api/src/routes/signals.py` (`get_service_status`)
- Modify: `packages/api/src/routes/settings.py` (`get_service_status`, `GOLD_SYMBOL` constant)

**Interfaces:**
- Consumes: `derive_worker_status(heartbeat, worker_id, now)` from Task 7.
- Produces: both `/service/status` endpoints keep reporting gold specifically (`worker_id = "XAUUSD:1h"`), unaffected by GBPUSD/EURUSD entries now present in the heartbeat.

- [ ] **Step 1: Update `routes/settings.py`**

Add a `GOLD_SYMBOL` constant next to `LIVE_TIMEFRAME`:

```python
# Only 1h is currently tuned/validated and actually running live — see
# TIMEFRAMES in run_multi_timeframe_service.py.
LIVE_TIMEFRAME = '1h'
```

becomes:

```python
# Only 1h is currently tuned/validated and actually running live — see
# WORKER_SPECS in run_multi_timeframe_service.py.
LIVE_TIMEFRAME = '1h'
GOLD_SYMBOL = 'XAUUSD'
```

In `get_service_status`, replace:

```python
    heartbeat = repo.get("worker_heartbeat", default={}) or {}
    worker_status = derive_worker_status(heartbeat, timeframe=LIVE_TIMEFRAME, now=datetime.now())
```

with:

```python
    heartbeat = repo.get("worker_heartbeat", default={}) or {}
    worker_status = derive_worker_status(heartbeat, worker_id=f"{GOLD_SYMBOL}:{LIVE_TIMEFRAME}", now=datetime.now())
```

- [ ] **Step 2: Update `routes/signals.py`**

Add a `GOLD_SYMBOL` constant near the top of the file (after the existing imports, before `router = APIRouter(...)`):

```python
router = APIRouter(prefix="/v1/signals", tags=["signals"])
```

becomes:

```python
router = APIRouter(prefix="/v1/signals", tags=["signals"])

# This endpoint's status fields have always reported gold specifically
# (symbol="XAUUSD" is hardcoded in the ServiceStatus response below); now
# that the heartbeat can contain more than one worker, worker_id must be
# constructed explicitly rather than picked arbitrarily. See
# docs/superpowers/specs/2026-09-09-gbpusd-eurusd-worker-wiring-design.md.
GOLD_SYMBOL = "XAUUSD"
```

In `get_service_status`, replace:

```python
    settings_repo = SettingsRepository(db)
    heartbeat = settings_repo.get('worker_heartbeat', default={}) or {}
    worker_status = derive_worker_status(heartbeat, timeframe=timeframe, now=datetime.now())
```

with:

```python
    settings_repo = SettingsRepository(db)
    heartbeat = settings_repo.get('worker_heartbeat', default={}) or {}
    worker_status = derive_worker_status(heartbeat, worker_id=f"{GOLD_SYMBOL}:{timeframe}", now=datetime.now())
```

- [ ] **Step 3: Run existing tests to verify nothing broke**

There is no route-level test file for these two endpoints today (confirmed: `packages/api/tests/` only contains `test_worker_status.py`), so this task has no new/existing route test to run. Verify by import:

Run: `cd packages/api && ../engine/venv/bin/python3 -c "import sys; sys.path.insert(0, 'src'); from routes import signals, settings"`
Expected: no `ImportError`/`NameError` (confirms `GOLD_SYMBOL` is defined before use in both files).

- [ ] **Step 4: Commit**

```bash
git add packages/api/src/routes/signals.py packages/api/src/routes/settings.py
git commit -m "fix: /service/status endpoints construct gold's worker_id explicitly"
```

---

### Task 9: `strategies_registry.py` — per-symbol strategy listing

**Files:**
- Create: `packages/api/src/strategies_registry.py`
- Modify: `packages/api/src/routes/settings.py` (`/v1/settings/strategies`, remove `STRATEGY_DISPLAY_NAMES`)
- Test: `packages/api/tests/test_strategies_registry.py` (new)

**Interfaces:**
- Produces: `STRATEGY_REGISTRY: Dict[str, Dict[str, str]]` (symbol → {rule_key: display_name}); `build_strategies_list(enabled_strategies: list, enabled_forex_symbols: list, validation_by_symbol: dict) -> list[dict]` — pure function, no DB/file I/O, mirroring the existing `derive_worker_status` pattern (pure logic pulled out of the route so it's unit-testable without a FastAPI test client, which this package doesn't have set up).

- [ ] **Step 1: Write the failing test**

Create `packages/api/tests/test_strategies_registry.py`:

```python
"""Tests for the per-symbol strategy listing shown in the admin UI —
pure logic, no DB/FastAPI needed (same pattern as test_worker_status.py)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from strategies_registry import STRATEGY_REGISTRY, build_strategies_list


class TestStrategyRegistry:
    def test_covers_all_three_symbols(self):
        assert set(STRATEGY_REGISTRY.keys()) == {'XAUUSD', 'GBPUSD', 'EURUSD'}

    def test_gbpusd_and_eurusd_share_the_same_rule_name(self):
        assert STRATEGY_REGISTRY['GBPUSD'] == {'asian_range_london_breakout': 'Asian Range London Breakout'}
        assert STRATEGY_REGISTRY['EURUSD'] == {'asian_range_london_breakout': 'Asian Range London Breakout'}


class TestBuildStrategiesList:
    def test_gold_entry_enabled_from_enabled_strategies(self):
        result = build_strategies_list(
            enabled_strategies=['order_block_retest'],
            enabled_forex_symbols=[],
            validation_by_symbol={},
        )
        gold_entry = next(r for r in result if r['symbol'] == 'XAUUSD')
        assert gold_entry['key'] == 'order_block_retest'
        assert gold_entry['enabled'] is True

    def test_gbpusd_entry_disabled_by_default(self):
        result = build_strategies_list(
            enabled_strategies=['order_block_retest'],
            enabled_forex_symbols=[],
            validation_by_symbol={},
        )
        gbp_entry = next(r for r in result if r['symbol'] == 'GBPUSD')
        assert gbp_entry['enabled'] is False

    def test_gbpusd_entry_enabled_when_listed(self):
        result = build_strategies_list(
            enabled_strategies=['order_block_retest'],
            enabled_forex_symbols=['GBPUSD'],
            validation_by_symbol={},
        )
        gbp_entry = next(r for r in result if r['symbol'] == 'GBPUSD')
        eur_entry = next(r for r in result if r['symbol'] == 'EURUSD')
        assert gbp_entry['enabled'] is True
        assert eur_entry['enabled'] is False

    def test_validation_stats_attached_per_symbol(self):
        result = build_strategies_list(
            enabled_strategies=['order_block_retest'],
            enabled_forex_symbols=['GBPUSD'],
            validation_by_symbol={
                'GBPUSD': {'asian_range_london_breakout': {'profit_factor': 1.58, 'total_trades': 47}},
            },
        )
        gbp_entry = next(r for r in result if r['symbol'] == 'GBPUSD')
        assert gbp_entry['profit_factor'] == 1.58
        assert gbp_entry['total_trades'] == 47

    def test_missing_validation_reports_none_not_a_crash(self):
        result = build_strategies_list(
            enabled_strategies=['order_block_retest'],
            enabled_forex_symbols=[],
            validation_by_symbol={},
        )
        gbp_entry = next(r for r in result if r['symbol'] == 'GBPUSD')
        assert gbp_entry['profit_factor'] is None
        assert gbp_entry['validated'] is False

    def test_returns_one_entry_per_registry_rule(self):
        result = build_strategies_list(
            enabled_strategies=['order_block_retest'],
            enabled_forex_symbols=[],
            validation_by_symbol={},
        )
        assert len(result) == 3  # order_block_retest, asian_range_london_breakout x2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/api && ../engine/venv/bin/python3 -m pytest tests/test_strategies_registry.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'strategies_registry'`.

- [ ] **Step 3: Implement**

Create `packages/api/src/strategies_registry.py`:

```python
"""
Per-symbol strategy registry for the /v1/settings/strategies admin listing.

Pure logic (no DB/file I/O) so it's unit-testable without a FastAPI test
client — same pattern as worker_status.py. The route in routes/settings.py
reads settings + tuned config files, then calls build_strategies_list().

See docs/superpowers/specs/2026-09-09-gbpusd-eurusd-worker-wiring-design.md.
"""
from typing import Any, Dict, List

# Canonical (symbol -> {rule_key: display_name}). GBPUSD and EURUSD
# deliberately share the same rule key (ForexSessionStrategy has exactly
# one rule) — enabled state for them comes from enabled_forex_symbols
# (symbol membership), not from a rule-name toggle.
STRATEGY_REGISTRY: Dict[str, Dict[str, str]] = {
    'XAUUSD': {'order_block_retest': 'Order Block Retest'},
    'GBPUSD': {'asian_range_london_breakout': 'Asian Range London Breakout'},
    'EURUSD': {'asian_range_london_breakout': 'Asian Range London Breakout'},
}


def build_strategies_list(
    enabled_strategies: List[str],
    enabled_forex_symbols: List[str],
    validation_by_symbol: Dict[str, Dict[str, Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    """
    Args:
        enabled_strategies: the `enabled_strategies` setting's current
            value (gold's rule names — unchanged shape/meaning).
        enabled_forex_symbols: the `enabled_forex_symbols` setting's
            current value (symbol names).
        validation_by_symbol: symbol -> {rule_key: {profit_factor,
            win_rate, total_trades, net_profit_pct}}, pre-loaded by the
            caller from each symbol's tuned config file (shape differs per
            symbol — the caller normalizes it before passing in here).

    Returns:
        One entry per (symbol, rule) in STRATEGY_REGISTRY.
    """
    enabled_strategies = set(enabled_strategies or [])
    enabled_forex_symbols = set(enabled_forex_symbols or [])

    entries = []
    for symbol, rules in STRATEGY_REGISTRY.items():
        symbol_validation = validation_by_symbol.get(symbol, {})
        for rule_key, display_name in rules.items():
            if symbol == 'XAUUSD':
                enabled = rule_key in enabled_strategies
            else:
                enabled = symbol in enabled_forex_symbols

            stats = symbol_validation.get(rule_key, {})
            entries.append({
                "key": rule_key,
                "symbol": symbol,
                "name": display_name,
                "enabled": enabled,
                "validated": rule_key in symbol_validation,
                "profit_factor": stats.get('profit_factor'),
                "win_rate": stats.get('win_rate'),
                "total_trades": stats.get('total_trades'),
                "net_profit_pct": stats.get('net_profit_pct'),
            })
    return entries
```

Now rewrite the route in `packages/api/src/routes/settings.py`. Remove `STRATEGY_DISPLAY_NAMES`:

```python
# Canonical rule keys (must match GoldStrategy.rules_enabled) with display
# names. Only order_block_retest survived validation — every other rule
# tried was ruled out and its code deleted; see
# docs/superpowers/specs/strategy-ledger.md for the full record.
STRATEGY_DISPLAY_NAMES = {
    'order_block_retest': 'Order Block Retest',
}
```

replace with nothing (delete this block — the registry now lives in `strategies_registry.py`), and add the import near the top of the file alongside the existing `from src.worker_status import derive_worker_status`:

```python
from src.worker_status import derive_worker_status
```

becomes:

```python
from src.worker_status import derive_worker_status
from src.strategies_registry import build_strategies_list
```

Replace the `get_strategies` route body:

```python
@router.get("/strategies")
async def get_strategies(db: Session = Depends(get_db)):
    """
    List every strategy rule with its live enabled/disabled state (from the
    `enabled_strategies` setting, which the engine now actually reads on
    every candle close) alongside its real validated performance on the
    live timeframe, so enabling a rule is an informed choice rather than a
    silent one — several rules are unprofitable under the live config even
    though they were profitable in isolation during tuning.

    Declared above GET /{key} so it isn't swallowed by that catch-all route.
    """
    repo = SettingsRepository(db)
    enabled = set(repo.get('enabled_strategies', default=[]) or [])

    validation: Dict[str, Any] = {}
    tuned_config_path = ENGINE_DIR / 'tuned_configs' / f'{LIVE_TIMEFRAME}.json'
    if tuned_config_path.exists():
        with open(tuned_config_path) as f:
            tuned = json.load(f)
        validation = tuned.get('final_shared_config_validation', {})

    return [
        {
            "key": key,
            "name": STRATEGY_DISPLAY_NAMES.get(key, key),
            "enabled": key in enabled,
            "timeframe": LIVE_TIMEFRAME,
            "validated": key in validation,
            "profit_factor": validation.get(key, {}).get('profit_factor'),
            "win_rate": validation.get(key, {}).get('win_rate'),
            "total_trades": validation.get(key, {}).get('total_trades'),
            "net_profit_pct": validation.get(key, {}).get('net_profit_pct'),
        }
        for key in STRATEGY_DISPLAY_NAMES
    ]
```

with:

```python
@router.get("/strategies")
async def get_strategies(db: Session = Depends(get_db)):
    """
    List every strategy rule, across every instrument, with its live
    enabled/disabled state and real validated performance, so enabling a
    rule is an informed choice rather than a silent one. See
    docs/superpowers/specs/2026-09-09-gbpusd-eurusd-worker-wiring-design.md.

    Declared above GET /{key} so it isn't swallowed by that catch-all route.
    """
    repo = SettingsRepository(db)
    enabled_strategies = repo.get('enabled_strategies', default=[]) or []
    enabled_forex_symbols = repo.get('enabled_forex_symbols', default=[]) or []

    validation_by_symbol: Dict[str, Dict[str, Any]] = {}

    gold_config_path = ENGINE_DIR / 'tuned_configs' / f'{LIVE_TIMEFRAME}.json'
    if gold_config_path.exists():
        with open(gold_config_path) as f:
            tuned = json.load(f)
        validation_by_symbol['XAUUSD'] = tuned.get('final_shared_config_validation', {})

    forex_config_filenames = {'GBPUSD': 'gbpusd_1h.json', 'EURUSD': 'eurusd_1h.json'}
    for symbol, filename in forex_config_filenames.items():
        forex_config_path = ENGINE_DIR / 'tuned_configs' / filename
        if forex_config_path.exists():
            with open(forex_config_path) as f:
                tuned = json.load(f)
            # Forex tuned configs have a `test` block (train/test split
            # results), not gold's per-rule final_shared_config_validation
            # dict — normalize into the same {rule_key: stats} shape here.
            validation_by_symbol[symbol] = {
                'asian_range_london_breakout': tuned.get('test', {}),
            }

    return build_strategies_list(
        enabled_strategies=enabled_strategies,
        enabled_forex_symbols=enabled_forex_symbols,
        validation_by_symbol=validation_by_symbol,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/api && ../engine/venv/bin/python3 -m pytest tests/test_strategies_registry.py -v`
Expected: PASS (all).

Also verify the route still imports cleanly:
Run: `cd packages/api && ../engine/venv/bin/python3 -c "import sys; sys.path.insert(0, 'src'); from routes import settings"`
Expected: no error.

- [ ] **Step 5: Commit**

```bash
git add packages/api/src/strategies_registry.py packages/api/src/routes/settings.py packages/api/tests/test_strategies_registry.py
git commit -m "feat: per-symbol strategy registry for /v1/settings/strategies"
```

---

### Task 10: Controls page — gate the strategy toggle to gold rows only

**Added during execution, not in the original plan.** Task 9's task
reviewer found a real, load-bearing gap: `/v1/settings/strategies` now
returns 3 entries (`order_block_retest`/XAUUSD,
`asian_range_london_breakout`/GBPUSD, `asian_range_london_breakout`/EURUSD)
instead of 1, but `apps/web/app/controls/page.tsx` — a live, working admin
page — was never updated for this. Two concrete bugs would ship the moment
this backend change deploys: (1) `key={strategy.key}` (page.tsx:229)
collides for the GBPUSD/EURUSD rows (both share the rule key
`asian_range_london_breakout`); (2) `toggleStrategy(strategy.key)`
(page.tsx:54-58) unconditionally writes `enabled_strategies` for ANY row's
toggle — flipping either forex row's switch would write
`'asian_range_london_breakout'` into gold's `enabled_strategies` setting,
corrupting its *meaning* (not its shape) in a way GoldStrategy's
`rules_enabled` has no key for. This is exactly the kind of live-admin-UI
corruption the plan's "no shape change to `enabled_strategies`" constraint
was meant to prevent, just via a path (a second symbol's own toggle)
nobody had considered when that constraint was written.

Additionally, `page.tsx:250` reads `strategy.timeframe`, a field
`build_strategies_list` (Task 9) no longer returns — this would render
"Not yet validated on undefined" for any non-validated row.

**Files:**
- Modify: `apps/web/lib/types.ts` (`StrategyPerformance` — drop
  `timeframe`, add `symbol`)
- Modify: `apps/web/app/controls/page.tsx` (row `key`, toggle gating, copy
  fix)

**Interfaces:**
- Consumes: `/v1/settings/strategies`'s response shape from Task 9 (each
  entry has `key`, `symbol`, `name`, `enabled`, `validated`,
  `profit_factor`, `win_rate`, `total_trades`, `net_profit_pct` — no
  `timeframe`).
- Produces: the Controls page renders one row per entry with a unique key,
  shows each entry's `symbol` so GBPUSD/EURUSD rows are visually
  distinguishable, and only lets XAUUSD's row toggle `enabled_strategies`
  — non-XAUUSD rows render their switch disabled (visible, informative,
  not interactive), so there is no code path left that can write a forex
  rule name into `enabled_strategies`.

- [ ] **Step 1: Update the type**

In `apps/web/lib/types.ts`, replace:

```typescript
export interface StrategyPerformance {
  key: string;
  name: string;
  enabled: boolean;
  timeframe: string;
  validated: boolean;
  profit_factor: number | null;
  win_rate: number | null;
  total_trades: number | null;
  net_profit_pct: number | null;
}
```

with:

```typescript
export interface StrategyPerformance {
  key: string;
  symbol: string;
  name: string;
  enabled: boolean;
  validated: boolean;
  profit_factor: number | null;
  win_rate: number | null;
  total_trades: number | null;
  net_profit_pct: number | null;
}
```

- [ ] **Step 2: Gate the toggle and fix the row key/copy**

In `apps/web/app/controls/page.tsx`, replace:

```typescript
  const toggleStrategy = (key: string) => {
    const next = enabledStrategies.includes(key)
      ? enabledStrategies.filter((k) => k !== key)
      : [...enabledStrategies, key];
    updateSetting.mutate({ key: "enabled_strategies", value: next });
  };
```

with:

```typescript
  // Only XAUUSD's rows are backed by the enabled_strategies setting.
  // GBPUSD/EURUSD share ForexSessionStrategy's single rule name
  // (asian_range_london_breakout) with each other, so writing their
  // toggle into enabled_strategies would corrupt gold's own rule list —
  // their toggle is gated off below instead (see the Switch's `disabled`
  // prop). Enabling either forex symbol live is a separate, deliberate
  // decision (enabled_forex_symbols), not made from this page yet.
  const toggleStrategy = (key: string) => {
    const next = enabledStrategies.includes(key)
      ? enabledStrategies.filter((k) => k !== key)
      : [...enabledStrategies, key];
    updateSetting.mutate({ key: "enabled_strategies", value: next });
  };
```

Replace the row-rendering block:

```typescript
              {strategies?.map((strategy) => (
                <div
                  key={strategy.key}
                  className="flex items-center justify-between gap-3 p-3 sm:p-4 rounded-lg bg-black/20 hover:bg-black/30 transition-all"
                >
                  <div className="flex items-center gap-3 sm:gap-4 min-w-0">
                    <Switch checked={strategy.enabled} onCheckedChange={() => toggleStrategy(strategy.key)} />
                    <div className="min-w-0">
                      <p className="text-sm sm:text-base font-medium text-white mb-0.5 sm:mb-1 truncate">{strategy.name}</p>
                      {strategy.validated ? (
                        <div className="flex items-center gap-2 sm:gap-3 text-xs text-gray-400 flex-wrap">
                          <span>
                            Win rate: <span className="text-white font-medium">{strategy.win_rate?.toFixed(1)}%</span>
                          </span>
                          <span>
                            PF:{" "}
                            <span className={strategy.profit_factor && strategy.profit_factor >= 1 ? "text-green-400 font-medium" : "text-red-400 font-medium"}>
                              {formatProfitFactor(strategy.profit_factor)}
                            </span>
                          </span>
                          <span>{strategy.total_trades} trades</span>
                        </div>
                      ) : (
                        <span className="text-xs text-amber-400">Not yet validated on {strategy.timeframe}</span>
                      )}
                    </div>
                  </div>
                  {strategy.validated && strategy.profit_factor !== null && strategy.profit_factor < 1 && (
                    <Badge variant="outline" className="border-red-500/40 text-red-400 shrink-0 hidden sm:inline-flex">
                      Unprofitable
                    </Badge>
                  )}
                </div>
              ))}
```

with:

```typescript
              {strategies?.map((strategy) => (
                <div
                  key={`${strategy.symbol}-${strategy.key}`}
                  className="flex items-center justify-between gap-3 p-3 sm:p-4 rounded-lg bg-black/20 hover:bg-black/30 transition-all"
                >
                  <div className="flex items-center gap-3 sm:gap-4 min-w-0">
                    <Switch
                      checked={strategy.enabled}
                      disabled={strategy.symbol !== "XAUUSD"}
                      onCheckedChange={() => toggleStrategy(strategy.key)}
                    />
                    <div className="min-w-0">
                      <p className="text-sm sm:text-base font-medium text-white mb-0.5 sm:mb-1 truncate">
                        {strategy.name} <span className="text-gray-500 font-normal">· {strategy.symbol}</span>
                      </p>
                      {strategy.validated ? (
                        <div className="flex items-center gap-2 sm:gap-3 text-xs text-gray-400 flex-wrap">
                          <span>
                            Win rate: <span className="text-white font-medium">{strategy.win_rate?.toFixed(1)}%</span>
                          </span>
                          <span>
                            PF:{" "}
                            <span className={strategy.profit_factor && strategy.profit_factor >= 1 ? "text-green-400 font-medium" : "text-red-400 font-medium"}>
                              {formatProfitFactor(strategy.profit_factor)}
                            </span>
                          </span>
                          <span>{strategy.total_trades} trades</span>
                        </div>
                      ) : (
                        <span className="text-xs text-amber-400">Not yet validated</span>
                      )}
                    </div>
                  </div>
                  {strategy.validated && strategy.profit_factor !== null && strategy.profit_factor < 1 && (
                    <Badge variant="outline" className="border-red-500/40 text-red-400 shrink-0 hidden sm:inline-flex">
                      Unprofitable
                    </Badge>
                  )}
                </div>
              ))}
```

- [ ] **Step 3: Verify with a type check**

Run: `cd apps/web && npx tsc --noEmit`
Expected: no new type errors introduced by this change (pre-existing
unrelated errors, if any, are not this task's concern — note them if
present and confirm they predate this change).

- [ ] **Step 4: Commit**

```bash
git add apps/web/lib/types.ts apps/web/app/controls/page.tsx
git commit -m "fix: gate the Controls strategy toggle to XAUUSD rows, fix forex row key collision"
```

---

### Task 11: `/v1/signals/stats/performance` gains an optional `symbol` filter

**Files:**
- Modify: `packages/api/src/routes/signals.py` (`get_performance_stats`)

**Interfaces:**
- Produces: `GET /v1/signals/stats/performance?symbol=GBPUSD` filters to that symbol; omitted `symbol` keeps today's all-symbols behavior.

- [ ] **Step 1: Implement (no new test file — this is a thin passthrough to an already-tested repository method)**

`SignalRepository.get_performance_stats` already accepts `symbol: str = None` (confirmed by reading `packages/engine/src/database/signal_repository.py:265`) — this task only wires a query parameter through to it; the filtering logic itself is pre-existing and out of scope to re-test here.

In `packages/api/src/routes/signals.py`, replace:

```python
@router.get("/stats/performance", response_model=PerformanceStats)
async def get_performance_stats(
    days: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Get signal performance statistics.

    Delegates to SignalRepository.get_performance_stats() — the same
    R-multiple math the weekly Telegram report uses — instead of the old
    inline implementation here, which computed wins/losses from `Signal.pnl`.
    `pnl` is always NULL in signals-only mode (no real account behind these
    signals yet), so that implementation silently counted every closed
    signal as neither a win nor a loss and pinned win_rate at 0%.

    Args:
        days: Calculate stats for last N days (default: all time, via a
            30-year lookback since the repository method requires a value)
        db: Database session

    Returns:
        Performance statistics
    """
    repo = SignalRepository(db)
    stats = repo.get_performance_stats(days=days or 365 * 30)
```

with:

```python
@router.get("/stats/performance", response_model=PerformanceStats)
async def get_performance_stats(
    days: Optional[int] = None,
    symbol: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get signal performance statistics.

    Delegates to SignalRepository.get_performance_stats() — the same
    R-multiple math the weekly Telegram report uses — instead of the old
    inline implementation here, which computed wins/losses from `Signal.pnl`.
    `pnl` is always NULL in signals-only mode (no real account behind these
    signals yet), so that implementation silently counted every closed
    signal as neither a win nor a loss and pinned win_rate at 0%.

    Args:
        days: Calculate stats for last N days (default: all time, via a
            30-year lookback since the repository method requires a value)
        symbol: If given, only signals for this symbol (default: all
            symbols, today's behavior — added so GBPUSD/EURUSD performance
            doesn't silently blend into gold's once either goes live; see
            docs/superpowers/specs/2026-09-09-gbpusd-eurusd-worker-wiring-design.md)
        db: Database session

    Returns:
        Performance statistics
    """
    repo = SignalRepository(db)
    stats = repo.get_performance_stats(days=days or 365 * 30, symbol=symbol)
```

- [ ] **Step 2: Verify by import**

Run: `cd packages/api && ../engine/venv/bin/python3 -c "import sys; sys.path.insert(0, 'src'); from routes import signals"`
Expected: no error.

- [ ] **Step 3: Commit**

```bash
git add packages/api/src/routes/signals.py
git commit -m "feat: optional symbol filter on /v1/signals/stats/performance"
```

---

### Task 12: Full regression run, ledger update, final commit

**Files:**
- Modify: `docs/superpowers/specs/strategy-ledger.md` (GBPUSD/EURUSD entry)

**Interfaces:** None — this task verifies the whole change set together and closes out documentation.

- [ ] **Step 1: Run the full engine test suite**

Run: `cd packages/engine && ./venv/bin/python3 -m pytest tests/ -v`
Expected: PASS except one known, pre-existing, unrelated baseline failure —
confirmed present before this plan's implementation began (git commit
`f580006`, the last commit before Task 1): `tests/test_api.py` fails with
`ModuleNotFoundError: No module named 'main'` (1 failed, 6 errors) — a stale
test file referencing a module path from before the API moved to
`packages/api`. This is not something this plan touches or is responsible
for fixing. Every other test must PASS, including all files touched across
Tasks 1–6 and every pre-existing file not touched by this plan (e.g.
`test_realtime_feed_timezone.py`, `test_realtime_feed_end_date.py`,
`test_weekly_report.py`, `test_worker_heartbeat.py`). Any *other* failure
means a gold-regression was introduced — stop and fix before proceeding.

- [ ] **Step 2: Run the full API test suite**

Run: `cd packages/api && ../engine/venv/bin/python3 -m pytest tests/ -v`
Expected: PASS — `test_worker_status.py` and `test_strategies_registry.py`.

- [ ] **Step 3: Update the strategy ledger**

In `docs/superpowers/specs/strategy-ledger.md`, find:

```
- **Verdict:** ✅ Validated on both pairs. **Not wired into the live
  multi-timeframe service** — going live is a separate, later decision,
  same convention as every GoldStrategy rule.
```

Replace with:

```
- **Verdict:** ✅ Validated on both pairs. **Wired into the live
  multi-timeframe service as of 2026-09-09** (see
  docs/superpowers/specs/2026-09-09-gbpusd-eurusd-worker-wiring-design.md)
  — both workers run live in production (real data feed, heartbeat,
  restart-protection) with their rule disabled (`enabled_forex_symbols`
  empty by default). **Actually enabling either symbol's signals is a
  separate, later decision** requiring the user's explicit go-ahead, same
  convention as every GoldStrategy rule.
```

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/specs/strategy-ledger.md
git commit -m "docs: record GBPUSD/EURUSD workers wired live-but-disabled in strategy-ledger.md"
```

**Do not proceed past this point without the user's explicit approval** — deploying to Railway/Vercel (push to `main`) and verifying via the production API are the next steps per the spec's Rollout section, and are a hard checkpoint, not an automatic continuation.

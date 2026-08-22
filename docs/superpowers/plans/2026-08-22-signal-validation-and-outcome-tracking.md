# Signal Re-Tuning, Outcome Tracking & Reporting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Re-tune and validate the gold trading strategy for the 1H timeframe against real market data, add a signal outcome tracker that records whether each generated signal actually hit its take-profit or stop-loss, add performance reporting (on-demand + weekly Telegram), and scope the live Railway service down to the validated 1H feed only.

**Architecture:** `run_multi_timeframe_service.py` becomes the single canonical live entry point, scoped to `TIMEFRAMES = ['1h']`. Each `TimeframeWorker` loads a tuned per-rule config from `tuned_configs/1h.json` (produced offline by `tune_strategy.py`) and wires a new `SignalOutcomeTracker` into its `RealtimeSignalGenerator`, which checks every newly-closed candle against all open signals and closes/expires them using the same conservative SL-before-TP logic as `BacktestEngine`. Reporting reads the same database via an extended `SignalRepository.get_performance_stats()`.

**Tech Stack:** Python 3.11, pandas, SQLAlchemy (SQLite locally / Postgres in prod), pytest, yfinance (via existing `fetch_real_data.py`), Telegram Bot API (via existing `TelegramSubscriber`).

**Spec:** `docs/superpowers/specs/2026-08-22-signal-validation-and-outcome-tracking-design.md`

## Global Constraints

- No new database tables or columns — reuse `SignalStatus.PENDING/ACTIVE/CLOSED_TP/CLOSED_SL/CANCELLED` and the existing `actual_exit`/`pnl_pips`/`closed_at`/`notes` columns on `Signal` (`packages/engine/src/database/models.py`).
- No dollar P&L fabrication — `pnl`/`pnl_pct` stay `None` until real trading exists. Outcomes are tracked via price/pips/R-multiple only.
- No auto-trading changes — `MT5Subscriber`/`enable_trading` stay disabled throughout.
- Only the 1H timeframe gets re-tuned/validated in this pass; `run_signal_service.py` and the other 5 timeframes in `run_multi_timeframe_service.py` are retired from the live path (left in the repo, not deleted).
- Train/test split is chronological 70/30 (test = most recent 30%), and the split is never violated during parameter search — only the final chosen config touches the test slice.
- Every code change must run against the venv at `packages/engine/venv` (Python 3.11) using only already-installed packages (`pandas`, `numpy`, `requests`, `yfinance`, `sqlalchemy`, `python-dotenv`, `pytest`) unless a step explicitly installs something new.

---

### Task 1: Fetch real 1H historical data

**Files:**
- Output: `packages/engine/data/processed/xauusd_1h_2024_2026.csv` (generated, not committed — already covered by `.gitignore`'s `*.csv` pattern; verify this before assuming)

**Interfaces:**
- Produces: a CSV file at a known path that Task 10/11 will load via `GoldDataLoader().load_from_csv(path)`.

- [ ] **Step 1: Confirm CSV files are gitignored**

Run: `cd packages/engine && git check-ignore -v data/processed/xauusd_4h_2025_2026.csv`
Expected: prints a match against a `*.csv` (or similar) rule in `.gitignore`. If it does NOT match (empty output), stop and add `data/processed/*.csv` to `.gitignore` before continuing, so the new file isn't accidentally committed.

- [ ] **Step 2: Fetch 730 days of real 1H XAUUSD data**

Run:
```bash
cd packages/engine
source venv/bin/activate
python fetch_real_data.py --timeframe 1h --start 2024-08-24 --clean --output xauusd_1h_2024_2026.csv
```
Expected output ends with `✅ DATA FETCH COMPLETE!` and reports a candle count in the thousands (730 days × ~24 candles/day, minus market-closed hours — expect roughly 10,000-13,000 candles). Note the exact saved filename it prints (it may append a suffix) — record it, it's needed in Task 10/11.

- [ ] **Step 3: Sanity-check the data**

Run:
```bash
cd packages/engine
source venv/bin/activate
python3 -c "
import sys; sys.path.insert(0, 'src')
from data.loader import GoldDataLoader
df = GoldDataLoader().load_from_csv('data/processed/xauusd_1h_2024_2026.csv')
print('rows:', len(df))
print('range:', df.index[0], 'to', df.index[-1])
print('price range:', df['low'].min(), '-', df['high'].max())
assert len(df) > 5000, 'suspiciously few candles for 730 days of 1H data'
assert 1000 < df['low'].min() and df['high'].max() < 10000, 'price range looks wrong for gold'
print('OK')
"
```
Expected: prints `OK` with no assertion errors.

No commit for this task — the CSV is a local data artifact, not source code.

---

### Task 2: Fix latent bugs found while validating the existing multi-timeframe service

Two bugs were found while smoke-testing `run_multi_timeframe_service.py` on 2026-08-22: it passes `datafeed_type=` to `create_datafeed()`, whose actual parameter is `feed_type=` — the typo silently falls into `**kwargs` and is ignored (no crash, but the intended `DATA_FEED_TYPE` env var override never takes effect; `create_datafeed` falls back to its own `DATAFEED_TYPE` env var or the `yahoo` default instead). Separately, `RealtimeSignalGenerator.start()` always logs `"Strategy: Momentum Equilibrium"` regardless of which rules are actually enabled.

**Files:**
- Modify: `packages/engine/run_multi_timeframe_service.py:127-131`
- Modify: `packages/engine/src/signals/realtime_generator.py:443`
- Test: `packages/engine/tests/test_realtime_generator.py` (new)

**Interfaces:**
- No new interfaces — internal correctness fixes only.

- [ ] **Step 1: Write the failing test for the strategy log line**

Create `packages/engine/tests/test_realtime_generator.py`:
```python
"""Tests for RealtimeSignalGenerator."""
import sys
from pathlib import Path
import logging

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from signals.gold_strategy import GoldStrategy
from signals.realtime_generator import RealtimeSignalGenerator, SignalValidator


class FakeDataFeed:
    """Minimal stand-in for RealtimeDataFeed, just enough to construct a generator."""
    symbol = "XAUUSD"
    timeframe = "1h"
    is_connected = True

    def connect(self):
        return True


class TestStrategyLogLine:
    def test_start_logs_actual_enabled_rules(self, caplog):
        strategy = GoldStrategy()
        for name in strategy.rules_enabled:
            strategy.rules_enabled[name] = False
        strategy.rules_enabled['london_session_breakout'] = True

        generator = RealtimeSignalGenerator(
            data_feed=FakeDataFeed(),
            strategy=strategy,
            validator=SignalValidator(),
        )

        with caplog.at_level(logging.INFO):
            generator.start(max_iterations=0)

        messages = [r.message for r in caplog.records]
        assert any("london_session_breakout" in m for m in messages), messages
        assert not any(m == "Strategy: Momentum Equilibrium" for m in messages), messages
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/engine && source venv/bin/activate && python -m pytest tests/test_realtime_generator.py -v`
Expected: FAIL — the log message is the literal hardcoded string, not the rule name.

- [ ] **Step 3: Fix the hardcoded log line**

In `packages/engine/src/signals/realtime_generator.py`, find line 443:
```python
        logger.info(f"Strategy: Momentum Equilibrium")
```
Replace with:
```python
        enabled_rules = [name for name, on in self.strategy.rules_enabled.items() if on]
        logger.info(f"Strategy: {', '.join(enabled_rules)}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/engine && source venv/bin/activate && python -m pytest tests/test_realtime_generator.py -v`
Expected: PASS

- [ ] **Step 5: Fix the create_datafeed keyword argument mismatch**

In `packages/engine/run_multi_timeframe_service.py`, find (around line 122-131):
```python
            datafeed_type = os.getenv('DATA_FEED_TYPE', 'yahoo')  # Default to yahoo for backward compatibility
            logger.info(f"   [{self.timeframe}] Using data feed: {datafeed_type}")

            data_feed = create_datafeed(
                datafeed_type=datafeed_type,
                symbol='XAUUSD',
                timeframe=self.timeframe
            )
```
Replace with:
```python
            datafeed_type = os.getenv('DATA_FEED_TYPE', 'yahoo')  # Default to yahoo for backward compatibility
            logger.info(f"   [{self.timeframe}] Using data feed: {datafeed_type}")

            data_feed = create_datafeed(
                feed_type=datafeed_type,
                symbol='XAUUSD',
                timeframe=self.timeframe
            )
```

- [ ] **Step 6: Manually verify the fix takes effect**

Run:
```bash
cd packages/engine
source venv/bin/activate
DATA_FEED_TYPE=yahoo python3 -c "
import sys; sys.path.insert(0, 'src')
from data.realtime_feed import create_datafeed
feed = create_datafeed(feed_type='yahoo', symbol='XAUUSD', timeframe='1h')
print(type(feed).__name__)
"
```
Expected: prints `YahooFinanceDataFeed` with no errors.

- [ ] **Step 7: Run the full existing test suite to check for regressions**

Run: `cd packages/engine && source venv/bin/activate && python -m pytest tests/ -v`
Expected: all tests pass (or the same pre-existing failures as before this task — note any and confirm they're unrelated to this change).

- [ ] **Step 8: Commit**

```bash
cd packages/engine
git add run_multi_timeframe_service.py src/signals/realtime_generator.py tests/test_realtime_generator.py
git commit -m "fix: correct create_datafeed kwarg name and stale strategy log line"
```

---

### Task 3: Signal outcome decision logic (pure function, no DB)

**Files:**
- Create: `packages/engine/src/signals/outcome_tracker.py`
- Test: `packages/engine/tests/test_outcome_tracker.py`

**Interfaces:**
- Produces: `OutcomeAction` enum (`NONE`, `CLOSED_TP`, `CLOSED_SL`, `EXPIRED`), `OpenSignalLike` dataclass (`id: int, direction: str, entry_price: float, stop_loss: float, take_profit: float, timestamp: datetime`), and `evaluate_signal_outcome(signal: OpenSignalLike, candle: pd.Series, candle_time: datetime, expiry_hours: float) -> OutcomeAction`. Task 5 imports all three.

- [ ] **Step 1: Write the failing tests**

Create `packages/engine/tests/test_outcome_tracker.py`:
```python
"""Tests for signal outcome decision logic."""
import sys
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from signals.outcome_tracker import OpenSignalLike, OutcomeAction, evaluate_signal_outcome


def make_candle(low, high):
    return pd.Series({'open': (low + high) / 2, 'high': high, 'low': low, 'close': (low + high) / 2})


class TestEvaluateSignalOutcome:
    def test_long_hits_stop_loss(self):
        signal = OpenSignalLike(
            id=1, direction="LONG", entry_price=2000.0,
            stop_loss=1990.0, take_profit=2030.0,
            timestamp=datetime(2026, 1, 1, 10, 0),
        )
        candle = make_candle(low=1985.0, high=2010.0)
        result = evaluate_signal_outcome(
            signal, candle, candle_time=datetime(2026, 1, 1, 11, 0), expiry_hours=48
        )
        assert result == OutcomeAction.CLOSED_SL

    def test_long_hits_take_profit(self):
        signal = OpenSignalLike(
            id=1, direction="LONG", entry_price=2000.0,
            stop_loss=1990.0, take_profit=2030.0,
            timestamp=datetime(2026, 1, 1, 10, 0),
        )
        candle = make_candle(low=1995.0, high=2035.0)
        result = evaluate_signal_outcome(
            signal, candle, candle_time=datetime(2026, 1, 1, 11, 0), expiry_hours=48
        )
        assert result == OutcomeAction.CLOSED_TP

    def test_long_sl_wins_when_both_hit_same_candle(self):
        """Matches BacktestEngine.check_and_close_trades: SL checked before TP."""
        signal = OpenSignalLike(
            id=1, direction="LONG", entry_price=2000.0,
            stop_loss=1990.0, take_profit=2030.0,
            timestamp=datetime(2026, 1, 1, 10, 0),
        )
        candle = make_candle(low=1985.0, high=2035.0)
        result = evaluate_signal_outcome(
            signal, candle, candle_time=datetime(2026, 1, 1, 11, 0), expiry_hours=48
        )
        assert result == OutcomeAction.CLOSED_SL

    def test_short_hits_stop_loss(self):
        signal = OpenSignalLike(
            id=1, direction="SHORT", entry_price=2000.0,
            stop_loss=2010.0, take_profit=1970.0,
            timestamp=datetime(2026, 1, 1, 10, 0),
        )
        candle = make_candle(low=1990.0, high=2015.0)
        result = evaluate_signal_outcome(
            signal, candle, candle_time=datetime(2026, 1, 1, 11, 0), expiry_hours=48
        )
        assert result == OutcomeAction.CLOSED_SL

    def test_short_hits_take_profit(self):
        signal = OpenSignalLike(
            id=1, direction="SHORT", entry_price=2000.0,
            stop_loss=2010.0, take_profit=1970.0,
            timestamp=datetime(2026, 1, 1, 10, 0),
        )
        candle = make_candle(low=1965.0, high=2005.0)
        result = evaluate_signal_outcome(
            signal, candle, candle_time=datetime(2026, 1, 1, 11, 0), expiry_hours=48
        )
        assert result == OutcomeAction.CLOSED_TP

    def test_no_hit_and_not_expired_returns_none(self):
        signal = OpenSignalLike(
            id=1, direction="LONG", entry_price=2000.0,
            stop_loss=1990.0, take_profit=2030.0,
            timestamp=datetime(2026, 1, 1, 10, 0),
        )
        candle = make_candle(low=1998.0, high=2005.0)
        result = evaluate_signal_outcome(
            signal, candle, candle_time=datetime(2026, 1, 1, 11, 0), expiry_hours=48
        )
        assert result == OutcomeAction.NONE

    def test_expires_after_max_holding_time(self):
        signal = OpenSignalLike(
            id=1, direction="LONG", entry_price=2000.0,
            stop_loss=1990.0, take_profit=2030.0,
            timestamp=datetime(2026, 1, 1, 10, 0),
        )
        candle = make_candle(low=1998.0, high=2005.0)
        candle_time = datetime(2026, 1, 1, 10, 0) + timedelta(hours=49)
        result = evaluate_signal_outcome(
            signal, candle, candle_time=candle_time, expiry_hours=48
        )
        assert result == OutcomeAction.EXPIRED

    def test_ignores_candle_at_or_before_entry_time(self):
        """Never check a signal against its own entry candle."""
        signal = OpenSignalLike(
            id=1, direction="LONG", entry_price=2000.0,
            stop_loss=1990.0, take_profit=2030.0,
            timestamp=datetime(2026, 1, 1, 10, 0),
        )
        candle = make_candle(low=1000.0, high=3000.0)  # would hit both if checked
        result = evaluate_signal_outcome(
            signal, candle, candle_time=datetime(2026, 1, 1, 10, 0), expiry_hours=48
        )
        assert result == OutcomeAction.NONE
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/engine && source venv/bin/activate && python -m pytest tests/test_outcome_tracker.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'signals.outcome_tracker'`

- [ ] **Step 3: Implement the decision logic**

Create `packages/engine/src/signals/outcome_tracker.py`:
```python
"""
Signal outcome decision logic.

Determines whether an open signal should be closed (TP/SL hit) or expired,
given a newly-closed candle. Mirrors BacktestEngine.check_and_close_trades()
exactly (stop-loss checked before take-profit when both would be hit by the
same candle) so live outcome tracking stays consistent with the validated
backtest numbers.
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

import pandas as pd


class OutcomeAction(Enum):
    NONE = "none"
    CLOSED_TP = "closed_tp"
    CLOSED_SL = "closed_sl"
    EXPIRED = "expired"


@dataclass
class OpenSignalLike:
    """Minimal view of a Signal needed to evaluate its outcome."""
    id: int
    direction: str  # "LONG" or "SHORT"
    entry_price: float
    stop_loss: float
    take_profit: float
    timestamp: datetime  # when the signal was generated (its entry candle's time)


def evaluate_signal_outcome(
    signal: OpenSignalLike,
    candle: pd.Series,
    candle_time: datetime,
    expiry_hours: float,
) -> OutcomeAction:
    """
    Decide what should happen to `signal` given a new candle.

    Never evaluates a candle at or before the signal's own entry time.
    """
    if candle_time <= signal.timestamp:
        return OutcomeAction.NONE

    if signal.direction == "LONG":
        if candle['low'] <= signal.stop_loss:
            return OutcomeAction.CLOSED_SL
        if candle['high'] >= signal.take_profit:
            return OutcomeAction.CLOSED_TP
    else:  # SHORT
        if candle['high'] >= signal.stop_loss:
            return OutcomeAction.CLOSED_SL
        if candle['low'] <= signal.take_profit:
            return OutcomeAction.CLOSED_TP

    elapsed_hours = (candle_time - signal.timestamp).total_seconds() / 3600
    if elapsed_hours > expiry_hours:
        return OutcomeAction.EXPIRED

    return OutcomeAction.NONE
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/engine && source venv/bin/activate && python -m pytest tests/test_outcome_tracker.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
cd packages/engine
git add src/signals/outcome_tracker.py tests/test_outcome_tracker.py
git commit -m "feat: add pure signal outcome decision logic"
```

---

### Task 4: SignalRepository additions — get_open_signals filtering and close_open_signal

**Files:**
- Modify: `packages/engine/src/database/signal_repository.py:110-118` (replace `get_open_signals`)
- Modify: `packages/engine/src/database/signal_repository.py` (add `close_open_signal` near `close_signal`, line ~142)
- Test: `packages/engine/tests/test_signal_repository.py` (new)

**Interfaces:**
- Consumes: `Signal`, `SignalStatus`, `SignalDirection` from `database.models`.
- Produces: `SignalRepository.get_open_signals(symbol: str = None, timeframe: str = None) -> List[Signal]` (now returns PENDING **and** ACTIVE, filterable by symbol/timeframe — this is a behavior change from the old ACTIVE-only, no-filter version); `SignalRepository.close_open_signal(signal_id: int, exit_price: Optional[float], status: SignalStatus, closed_at: datetime, note_suffix: str = "") -> Optional[Signal]`. Task 5 calls both.

**Note on scope:** `packages/engine/src/trading/position_manager.py` calls `self.signal_repo.get_open_signals(session)` (passing a stray positional arg) and is already broken today independent of this change — auto-trading is disabled (`enable_trading=False` everywhere), so this dead code path is out of scope per the Global Constraints. Do not fix it as part of this task.

- [ ] **Step 1: Write the failing tests**

Create `packages/engine/tests/test_signal_repository.py`:
```python
"""Tests for SignalRepository, using a temporary on-disk SQLite database."""
import sys
from pathlib import Path
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from database.models import Base, Signal, SignalDirection, SignalStatus
from database.signal_repository import SignalRepository


@pytest.fixture
def session(tmp_path):
    db_path = tmp_path / "test_signals.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    sess = SessionLocal()
    yield sess
    sess.close()


@pytest.fixture
def repo(session):
    return SignalRepository(session)


def make_signal(symbol="XAUUSD", timeframe="1h", status=SignalStatus.PENDING, direction=SignalDirection.LONG):
    return Signal(
        timestamp=datetime(2026, 1, 1, 10, 0),
        symbol=symbol,
        timeframe=timeframe,
        strategy_name="Test Strategy",
        direction=direction,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2030.0,
        confidence=0.8,
        risk_pips=100.0,
        reward_pips=300.0,
        risk_reward_ratio=3.0,
        status=status,
    )


class TestGetOpenSignals:
    def test_returns_pending_and_active(self, repo):
        repo.create(make_signal(status=SignalStatus.PENDING))
        repo.create(make_signal(status=SignalStatus.ACTIVE))
        repo.create(make_signal(status=SignalStatus.CLOSED_TP))

        open_signals = repo.get_open_signals()

        assert len(open_signals) == 2
        assert {s.status for s in open_signals} == {SignalStatus.PENDING, SignalStatus.ACTIVE}

    def test_filters_by_symbol_and_timeframe(self, repo):
        repo.create(make_signal(symbol="XAUUSD", timeframe="1h"))
        repo.create(make_signal(symbol="XAUUSD", timeframe="4h"))
        repo.create(make_signal(symbol="XAGUSD", timeframe="1h"))

        result = repo.get_open_signals(symbol="XAUUSD", timeframe="1h")

        assert len(result) == 1
        assert result[0].symbol == "XAUUSD"
        assert result[0].timeframe == "1h"


class TestCloseOpenSignal:
    def test_closes_at_take_profit_and_computes_pnl_pips_from_entry_price(self, repo):
        saved = repo.create(make_signal(direction=SignalDirection.LONG))

        updated = repo.close_open_signal(
            signal_id=saved.id,
            exit_price=2030.0,
            status=SignalStatus.CLOSED_TP,
            closed_at=datetime(2026, 1, 1, 14, 0),
        )

        assert updated.status == SignalStatus.CLOSED_TP
        assert updated.actual_exit == 2030.0
        assert updated.pnl_pips == pytest.approx((2030.0 - 2000.0) * 10)
        assert updated.pnl is None  # no dollar P&L fabricated
        assert updated.closed_at == datetime(2026, 1, 1, 14, 0)

    def test_closes_short_correctly(self, repo):
        saved = repo.create(make_signal(direction=SignalDirection.SHORT))
        saved.entry_price = 2000.0
        repo.update(saved)

        updated = repo.close_open_signal(
            signal_id=saved.id,
            exit_price=1970.0,
            status=SignalStatus.CLOSED_TP,
            closed_at=datetime(2026, 1, 1, 14, 0),
        )

        assert updated.pnl_pips == pytest.approx((2000.0 - 1970.0) * 10)

    def test_expiry_has_no_exit_price_and_appends_note(self, repo):
        saved = repo.create(make_signal())
        saved.notes = "original note"
        repo.update(saved)

        updated = repo.close_open_signal(
            signal_id=saved.id,
            exit_price=None,
            status=SignalStatus.CANCELLED,
            closed_at=datetime(2026, 1, 2, 10, 0),
            note_suffix=" [expired after 48h with no resolution]",
        )

        assert updated.status == SignalStatus.CANCELLED
        assert updated.actual_exit is None
        assert updated.pnl_pips is None
        assert updated.notes == "original note [expired after 48h with no resolution]"

    def test_returns_none_for_unknown_id(self, repo):
        assert repo.close_open_signal(
            signal_id=99999, exit_price=2000.0,
            status=SignalStatus.CLOSED_TP, closed_at=datetime.utcnow(),
        ) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/engine && source venv/bin/activate && python -m pytest tests/test_signal_repository.py -v`
Expected: FAIL — `test_filters_by_symbol_and_timeframe` fails (old `get_open_signals` takes no filter args), and every `TestCloseOpenSignal` test fails with `AttributeError: 'SignalRepository' object has no attribute 'close_open_signal'`.

- [ ] **Step 3: Implement the repository changes**

In `packages/engine/src/database/signal_repository.py`, replace lines 110-118:
```python
    def get_open_signals(self) -> List[Signal]:
        """
        Get all currently open signals.

        Returns:
            List of active signals
        """
        return self.get_by_status(SignalStatus.ACTIVE)
```
with:
```python
    def get_open_signals(self, symbol: str = None, timeframe: str = None) -> List[Signal]:
        """
        Get all signals that are still open (PENDING or ACTIVE), optionally
        filtered by symbol and/or timeframe.

        Args:
            symbol: If given, only signals for this symbol
            timeframe: If given, only signals for this timeframe

        Returns:
            List of open signals, most recent first
        """
        query = self.session.query(Signal).filter(
            Signal.status.in_([SignalStatus.PENDING, SignalStatus.ACTIVE])
        )
        if symbol:
            query = query.filter(Signal.symbol == symbol)
        if timeframe:
            query = query.filter(Signal.timeframe == timeframe)
        return query.order_by(desc(Signal.timestamp)).all()
```

Then, immediately after the existing `close_signal` method (after its closing `return self.update(signal)` around line 176), add:
```python
    def close_open_signal(
        self,
        signal_id: int,
        exit_price: Optional[float],
        status: SignalStatus,
        closed_at: datetime,
        note_suffix: str = "",
    ) -> Optional[Signal]:
        """
        Close a signal that was never executed via MT5 (no actual_entry set),
        computing pnl_pips from the planned entry_price instead. Used by the
        signal outcome tracker for TP/SL hits and expiry — does not set
        pnl/pnl_pct since there is no real account behind these signals yet.

        Args:
            signal_id: ID of signal to close
            exit_price: Exit price, or None for an expiry with no resolution
            status: CLOSED_TP, CLOSED_SL, or CANCELLED (expiry)
            closed_at: Timestamp of the candle that triggered this close
            note_suffix: Text appended to the signal's existing notes

        Returns:
            Updated signal or None if not found
        """
        signal = self.get_by_id(signal_id)
        if not signal:
            return None

        signal.actual_exit = exit_price
        signal.status = status
        signal.closed_at = closed_at

        if exit_price is not None:
            if signal.direction == SignalDirection.LONG:
                signal.pnl_pips = (exit_price - signal.entry_price) * 10
            else:
                signal.pnl_pips = (signal.entry_price - exit_price) * 10

        if note_suffix:
            signal.notes = (signal.notes or "") + note_suffix

        return self.update(signal)
```

Also add `Optional` to the existing `typing` import at the top of the file if not already present — check line 5, it should read `from typing import List, Optional`; it already does, so no change needed there.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/engine && source venv/bin/activate && python -m pytest tests/test_signal_repository.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
cd packages/engine
git add src/database/signal_repository.py tests/test_signal_repository.py
git commit -m "feat: filter open signals by symbol/timeframe, add close_open_signal"
```

---

### Task 5: SignalOutcomeTracker (DB-wiring class)

**Files:**
- Modify: `packages/engine/src/signals/outcome_tracker.py` (add `SignalOutcomeTracker` class alongside the pure logic from Task 3)
- Test: `packages/engine/tests/test_outcome_tracker.py` (extend)

**Interfaces:**
- Consumes: `evaluate_signal_outcome`, `OpenSignalLike`, `OutcomeAction` (Task 3, same file); `DatabaseManager` from `database.connection`; `SignalRepository` from `database.signal_repository` (Task 4); `SignalStatus`, `SignalDirection` from `database.models`.
- Produces: `SignalOutcomeTracker(database_url: str, symbol: str, timeframe: str, expiry_hours: float)` with method `check_candle(candle: pd.Series, candle_time: pd.Timestamp) -> None`. Task 6 constructs and calls this.

- [ ] **Step 1: Write the failing tests**

Append to `packages/engine/tests/test_outcome_tracker.py`:
```python
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Base, Signal, SignalDirection, SignalStatus
from database.signal_repository import SignalRepository
from signals.outcome_tracker import SignalOutcomeTracker


@pytest.fixture
def db_url(tmp_path):
    return f"sqlite:///{tmp_path / 'tracker_test.db'}"


@pytest.fixture
def session_for(db_url):
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    sess = SessionLocal()
    yield sess
    sess.close()


def make_signal(session, direction, entry, sl, tp, timestamp, timeframe="1h", symbol="XAUUSD"):
    repo = SignalRepository(session)
    return repo.create(Signal(
        timestamp=timestamp, symbol=symbol, timeframe=timeframe,
        strategy_name="Test", direction=direction,
        entry_price=entry, stop_loss=sl, take_profit=tp,
        confidence=0.8, risk_pips=abs(entry - sl) * 10,
        reward_pips=abs(tp - entry) * 10, risk_reward_ratio=2.0,
        status=SignalStatus.PENDING,
    ))


class TestSignalOutcomeTracker:
    def test_closes_signal_that_hits_take_profit(self, db_url, session_for):
        signal = make_signal(
            session_for, SignalDirection.LONG, entry=2000.0, sl=1990.0, tp=2030.0,
            timestamp=datetime(2026, 1, 1, 10, 0),
        )

        tracker = SignalOutcomeTracker(
            database_url=db_url, symbol="XAUUSD", timeframe="1h", expiry_hours=48,
        )
        candle = pd.Series({'open': 2020.0, 'high': 2035.0, 'low': 2015.0, 'close': 2032.0})
        tracker.check_candle(candle, candle_time=datetime(2026, 1, 1, 11, 0))

        repo = SignalRepository(session_for)
        refreshed = repo.get_by_id(signal.id)
        assert refreshed.status == SignalStatus.CLOSED_TP
        assert refreshed.actual_exit == 2030.0

    def test_leaves_unresolved_signal_open(self, db_url, session_for):
        signal = make_signal(
            session_for, SignalDirection.LONG, entry=2000.0, sl=1990.0, tp=2030.0,
            timestamp=datetime(2026, 1, 1, 10, 0),
        )

        tracker = SignalOutcomeTracker(
            database_url=db_url, symbol="XAUUSD", timeframe="1h", expiry_hours=48,
        )
        candle = pd.Series({'open': 2001.0, 'high': 2005.0, 'low': 1999.0, 'close': 2002.0})
        tracker.check_candle(candle, candle_time=datetime(2026, 1, 1, 11, 0))

        repo = SignalRepository(session_for)
        refreshed = repo.get_by_id(signal.id)
        assert refreshed.status == SignalStatus.PENDING

    def test_expires_stale_signal(self, db_url, session_for):
        signal = make_signal(
            session_for, SignalDirection.LONG, entry=2000.0, sl=1990.0, tp=2030.0,
            timestamp=datetime(2026, 1, 1, 10, 0),
        )

        tracker = SignalOutcomeTracker(
            database_url=db_url, symbol="XAUUSD", timeframe="1h", expiry_hours=1,
        )
        candle = pd.Series({'open': 2001.0, 'high': 2005.0, 'low': 1999.0, 'close': 2002.0})
        tracker.check_candle(candle, candle_time=datetime(2026, 1, 1, 12, 0))

        repo = SignalRepository(session_for)
        refreshed = repo.get_by_id(signal.id)
        assert refreshed.status == SignalStatus.CANCELLED
        assert "[expired" in refreshed.notes

    def test_only_checks_matching_symbol_and_timeframe(self, db_url, session_for):
        other_tf_signal = make_signal(
            session_for, SignalDirection.LONG, entry=2000.0, sl=1990.0, tp=2030.0,
            timestamp=datetime(2026, 1, 1, 10, 0), timeframe="4h",
        )

        tracker = SignalOutcomeTracker(
            database_url=db_url, symbol="XAUUSD", timeframe="1h", expiry_hours=48,
        )
        candle = pd.Series({'open': 2020.0, 'high': 2035.0, 'low': 2015.0, 'close': 2032.0})
        tracker.check_candle(candle, candle_time=datetime(2026, 1, 1, 11, 0))

        repo = SignalRepository(session_for)
        refreshed = repo.get_by_id(other_tf_signal.id)
        assert refreshed.status == SignalStatus.PENDING  # untouched, different timeframe


class TestMatchesBacktestEngine:
    """
    Divergence check: replay the same signal + candle sequence through both
    SignalOutcomeTracker and BacktestEngine.check_and_close_trades(), and
    assert they reach the same conclusion. Catches the two implementations
    drifting apart even though they're meant to encode identical logic.
    """

    def test_multi_candle_replay_matches_backtest_engine(self, db_url, session_for):
        from backtesting.engine import BacktestEngine, Trade, TradeDirection, TradeStatus

        entry_time = datetime(2026, 1, 1, 10, 0)
        signal = make_signal(
            session_for, SignalDirection.LONG, entry=2000.0, sl=1990.0, tp=2030.0,
            timestamp=entry_time,
        )

        candles = [
            (datetime(2026, 1, 1, 11, 0), pd.Series({'open': 2001, 'high': 2010, 'low': 1995, 'close': 2005})),
            (datetime(2026, 1, 1, 12, 0), pd.Series({'open': 2005, 'high': 2015, 'low': 2000, 'close': 2010})),
            (datetime(2026, 1, 1, 13, 0), pd.Series({'open': 2010, 'high': 2032, 'low': 2008, 'close': 2029})),
        ]

        tracker = SignalOutcomeTracker(
            database_url=db_url, symbol="XAUUSD", timeframe="1h", expiry_hours=48,
        )
        for candle_time, candle in candles:
            tracker.check_candle(candle, candle_time=candle_time)

        repo = SignalRepository(session_for)
        tracker_result = repo.get_by_id(signal.id)

        # Replay the identical sequence through the trusted backtester.
        engine = BacktestEngine(initial_balance=10000, position_size_pct=2.0, slippage=0.0)
        trade = Trade(
            id=1, entry_time=entry_time, entry_price=2000.0,
            direction=TradeDirection.LONG, stop_loss=1990.0, take_profit=2030.0,
        )
        engine.open_trades = [trade]
        engine.trades = [trade]
        for candle_time, candle in candles:
            engine.check_and_close_trades(candle, candle_time)

        assert tracker_result.status.value == trade.status.value
        if trade.status != TradeStatus.OPEN:
            assert tracker_result.actual_exit == trade.exit_price
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/engine && source venv/bin/activate && python -m pytest tests/test_outcome_tracker.py -v`
Expected: the five new tests (four `TestSignalOutcomeTracker` + `TestMatchesBacktestEngine`) FAIL with `ImportError: cannot import name 'SignalOutcomeTracker'`.

- [ ] **Step 3: Implement SignalOutcomeTracker**

Append to `packages/engine/src/signals/outcome_tracker.py`:
```python
import sys
from pathlib import Path as _Path

sys.path.insert(0, str(_Path(__file__).parent.parent))

from database.connection import DatabaseManager
from database.models import SignalStatus
from database.signal_repository import SignalRepository


class SignalOutcomeTracker:
    """
    Checks every open signal for a given symbol/timeframe against a newly
    closed candle, closing it on TP/SL hit or expiring it if it's been open
    too long. Meant to be called once per candle from the live signal loop.
    """

    def __init__(self, database_url: str, symbol: str, timeframe: str, expiry_hours: float):
        self.db_manager = DatabaseManager(database_url)
        self.symbol = symbol
        self.timeframe = timeframe
        self.expiry_hours = expiry_hours

    def check_candle(self, candle: pd.Series, candle_time) -> None:
        with self.db_manager.session_scope() as session:
            repo = SignalRepository(session)
            open_signals = repo.get_open_signals(symbol=self.symbol, timeframe=self.timeframe)

            for sig in open_signals:
                signal_like = OpenSignalLike(
                    id=sig.id,
                    direction=sig.direction.value,
                    entry_price=sig.entry_price,
                    stop_loss=sig.stop_loss,
                    take_profit=sig.take_profit,
                    timestamp=sig.timestamp,
                )
                action = evaluate_signal_outcome(signal_like, candle, candle_time, self.expiry_hours)

                if action == OutcomeAction.CLOSED_TP:
                    repo.close_open_signal(
                        sig.id, exit_price=sig.take_profit,
                        status=SignalStatus.CLOSED_TP, closed_at=candle_time,
                    )
                elif action == OutcomeAction.CLOSED_SL:
                    repo.close_open_signal(
                        sig.id, exit_price=sig.stop_loss,
                        status=SignalStatus.CLOSED_SL, closed_at=candle_time,
                    )
                elif action == OutcomeAction.EXPIRED:
                    repo.close_open_signal(
                        sig.id, exit_price=None,
                        status=SignalStatus.CANCELLED, closed_at=candle_time,
                        note_suffix=f" [expired after {self.expiry_hours}h with no resolution]",
                    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/engine && source venv/bin/activate && python -m pytest tests/test_outcome_tracker.py -v`
Expected: PASS (13 tests total: 8 from Task 3 + 5 new)

- [ ] **Step 5: Commit**

```bash
cd packages/engine
git add src/signals/outcome_tracker.py tests/test_outcome_tracker.py
git commit -m "feat: add SignalOutcomeTracker to close/expire signals against live candles"
```

---

### Task 6: Wire SignalOutcomeTracker into the live signal loop

**Files:**
- Modify: `packages/engine/src/signals/realtime_generator.py:273-289` (`RealtimeSignalGenerator.__init__`)
- Modify: `packages/engine/src/signals/realtime_generator.py:386-421` (`run_once`)
- Modify: `packages/engine/run_multi_timeframe_service.py:99-159` (`TimeframeWorker._run`)
- Test: `packages/engine/tests/test_realtime_generator.py` (extend)

**Interfaces:**
- Consumes: `SignalOutcomeTracker` (Task 5).
- Produces: `RealtimeSignalGenerator(..., outcome_tracker: Optional[SignalOutcomeTracker] = None)` — later tasks don't depend on this further, it's the final integration point.

- [ ] **Step 1: Write the failing test**

Append to `packages/engine/tests/test_realtime_generator.py`:
```python
import pandas as pd
from unittest.mock import MagicMock


class FakeDataFeedWithCandles:
    symbol = "XAUUSD"
    timeframe = "1h"
    is_connected = True

    def __init__(self, df):
        self._df = df

    def connect(self):
        return True

    def get_latest_candles(self, count):
        return self._df

    def wait_for_candle_close(self, check_interval=60):
        pass


class TestOutcomeTrackerWiring:
    def test_run_once_calls_outcome_tracker_with_latest_candle(self):
        dates = pd.date_range(start='2026-01-01', periods=5, freq='1h')
        df = pd.DataFrame({
            'open': [2000, 2001, 2002, 2003, 2004],
            'high': [2005, 2006, 2007, 2008, 2009],
            'low': [1995, 1996, 1997, 1998, 1999],
            'close': [2001, 2002, 2003, 2004, 2005],
        }, index=dates)

        strategy = GoldStrategy()
        for name in strategy.rules_enabled:
            strategy.rules_enabled[name] = False  # no new signals this test

        mock_tracker = MagicMock()
        generator = RealtimeSignalGenerator(
            data_feed=FakeDataFeedWithCandles(df),
            strategy=strategy,
            validator=SignalValidator(),
            outcome_tracker=mock_tracker,
        )

        generator.run_once()

        mock_tracker.check_candle.assert_called_once()
        call_args = mock_tracker.check_candle.call_args
        assert call_args[0][1] == dates[-1]  # candle_time
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/engine && source venv/bin/activate && python -m pytest tests/test_realtime_generator.py -v`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'outcome_tracker'`

- [ ] **Step 3: Add the outcome_tracker parameter**

In `packages/engine/src/signals/realtime_generator.py`, find the `__init__` signature (around line 273):
```python
    def __init__(
        self,
        data_feed: RealtimeDataFeed,
        strategy: Optional[GoldStrategy] = None,
        validator: Optional[SignalValidator] = None,
        lookback_periods: int = 200
    ):
```
Replace with:
```python
    def __init__(
        self,
        data_feed: RealtimeDataFeed,
        strategy: Optional[GoldStrategy] = None,
        validator: Optional[SignalValidator] = None,
        lookback_periods: int = 200,
        outcome_tracker: Optional["SignalOutcomeTracker"] = None,
    ):
```
And add the import near the top of the file, alongside the other `signals.*` imports (around line 27):
```python
from signals.outcome_tracker import SignalOutcomeTracker
```
Then find, a few lines further down in the same method, the line:
```python
        self.data_feed = data_feed
        self.lookback_periods = lookback_periods
```
Replace with:
```python
        self.data_feed = data_feed
        self.lookback_periods = lookback_periods
        self.outcome_tracker = outcome_tracker
```

- [ ] **Step 4: Call the tracker in run_once()**

In `packages/engine/src/signals/realtime_generator.py`, find in `run_once()` (around line 404-412):
```python
        self.total_candles_processed += 1

        logger.info(
            f"📊 Candle close at {df.index[-1]} | "
            f"Close: ${df['close'].iloc[-1]:.2f}"
        )

        # Generate signal
        signal = self.generate_signal(df)
```
Replace with:
```python
        self.total_candles_processed += 1

        logger.info(
            f"📊 Candle close at {df.index[-1]} | "
            f"Close: ${df['close'].iloc[-1]:.2f}"
        )

        if self.outcome_tracker is not None:
            self.outcome_tracker.check_candle(df.iloc[-1], df.index[-1])

        # Generate signal
        signal = self.generate_signal(df)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd packages/engine && source venv/bin/activate && python -m pytest tests/test_realtime_generator.py -v`
Expected: PASS (all tests in this file)

- [ ] **Step 6: Wire tracker construction into TimeframeWorker**

In `packages/engine/run_multi_timeframe_service.py`, add this import near the top of the file, alongside the other `signals.subscribers` imports (around line 30-32):
```python
from signals.outcome_tracker import SignalOutcomeTracker
```

Then find, in `TimeframeWorker._run()` (around line 129-133):
```python
            # Create strategy - all 5 profitable rules enabled by default
            strategy = GoldStrategy()
            # All rules are already enabled by default (they're all profitable!)

            logger.info(f"   [{self.timeframe}] All 5 profitable rules enabled: {list(strategy.rules_enabled.keys())}")
```
Replace with:
```python
            # Create strategy - default config until Task 12 wires in the
            # tuned 1h config
            strategy = GoldStrategy()

            enabled_names = [name for name, on in strategy.rules_enabled.items() if on]
            logger.info(f"   [{self.timeframe}] Enabled rules: {enabled_names}")

            outcome_tracker = SignalOutcomeTracker(
                database_url=self.database_url,
                symbol='XAUUSD',
                timeframe=self.timeframe,
                expiry_hours=48.0,  # placeholder until Task 12 loads the data-derived value
            )
```

Then find, a few lines later, the `RealtimeSignalGenerator` construction (around line 144-148):
```python
            # Create generator
            self.generator = RealtimeSignalGenerator(
                data_feed=data_feed,
                strategy=strategy,
                validator=validator
            )
```
Replace with:
```python
            # Create generator
            self.generator = RealtimeSignalGenerator(
                data_feed=data_feed,
                strategy=strategy,
                validator=validator,
                outcome_tracker=outcome_tracker
            )
```

- [ ] **Step 7: Smoke-test the wiring end to end**

Run:
```bash
cd packages/engine
source venv/bin/activate
rm -f /tmp/wiring_smoke.db
DATABASE_URL="sqlite:////tmp/wiring_smoke.db" python3 -c "
import sys; sys.path.insert(0, 'src')
from run_multi_timeframe_service import MultiTimeframeService
svc = MultiTimeframeService(timeframes=['1h'], database_url='sqlite:////tmp/wiring_smoke.db')
svc.start()
" > /tmp/wiring_smoke.log 2>&1 &
sleep 15
kill %1 2>/dev/null
grep -i "error\|traceback" /tmp/wiring_smoke.log && echo "FOUND ERRORS ABOVE" || echo "no errors found"
```
Expected: `no errors found`, and the log shows the same successful startup sequence as the Task 2 smoke test (candle fetch, "Waiting for next 1h candle close").

- [ ] **Step 8: Commit**

```bash
cd packages/engine
git add src/signals/realtime_generator.py run_multi_timeframe_service.py tests/test_realtime_generator.py
git commit -m "feat: wire SignalOutcomeTracker into the live signal generation loop"
```

---

### Task 7: Extend performance stats with open/expired counts and R-multiple

**Files:**
- Modify: `packages/engine/src/database/signal_repository.py:210-266` (`get_performance_stats`)
- Test: `packages/engine/tests/test_signal_repository.py` (extend)

**Interfaces:**
- Produces: `get_performance_stats(days: int = 30, symbol: str = None, timeframe: str = None) -> dict` with keys `total_signals, tp_hits, sl_hits, expired, still_open, closed_manual, win_rate, avg_r_multiple, net_r_multiple`. Task 8 and 9 both call this and depend on exactly these key names.

**Note:** this changes the return shape of `get_performance_stats` (drops dollar-based keys like `total_pnl`/`profit_factor` since no dollar P&L is fabricated per the Global Constraints). The only caller is `DatabaseSubscriber.get_performance_stats()` (`packages/engine/src/signals/subscribers/database_subscriber.py:152-164`), which just proxies the dict through, and its own `__main__` test block only reads `stats['total_signals']` and `stats['win_rate']` — both keys are kept, so no changes needed there.

- [ ] **Step 1: Write the failing tests**

Append to `packages/engine/tests/test_signal_repository.py`:
```python
from database.models import SignalStatus


class TestGetPerformanceStats:
    def test_counts_and_rates_by_status(self, repo):
        # 2 TP hits, 1 SL hit, 1 expired, 1 still open
        tp1 = repo.create(make_signal(status=SignalStatus.PENDING))
        tp1.risk_pips, tp1.pnl_pips = 100.0, 300.0
        repo.update(tp1)
        repo.close_open_signal(tp1.id, 2030.0, SignalStatus.CLOSED_TP, datetime(2026, 1, 1, 12, 0))

        tp2 = repo.create(make_signal(status=SignalStatus.PENDING))
        tp2.risk_pips, tp2.pnl_pips = 100.0, 300.0
        repo.update(tp2)
        repo.close_open_signal(tp2.id, 2030.0, SignalStatus.CLOSED_TP, datetime(2026, 1, 1, 12, 0))

        sl1 = repo.create(make_signal(status=SignalStatus.PENDING))
        sl1.risk_pips, sl1.pnl_pips = 100.0, -100.0
        repo.update(sl1)
        repo.close_open_signal(sl1.id, 1990.0, SignalStatus.CLOSED_SL, datetime(2026, 1, 1, 12, 0))

        expired1 = repo.create(make_signal(status=SignalStatus.PENDING))
        repo.close_open_signal(
            expired1.id, None, SignalStatus.CANCELLED, datetime(2026, 1, 1, 12, 0),
            note_suffix=" [expired after 48h with no resolution]",
        )

        repo.create(make_signal(status=SignalStatus.PENDING))  # still open

        stats = repo.get_performance_stats(days=30)

        assert stats['total_signals'] == 5
        assert stats['tp_hits'] == 2
        assert stats['sl_hits'] == 1
        assert stats['expired'] == 1
        assert stats['still_open'] == 1
        assert stats['closed_manual'] == 0
        assert stats['win_rate'] == pytest.approx(2 / 3 * 100)  # 2 TP out of 3 resolved
        assert stats['avg_r_multiple'] == pytest.approx((3.0 + 3.0 + (-1.0)) / 3)
        assert stats['net_r_multiple'] == pytest.approx(3.0 + 3.0 + (-1.0))

    def test_empty_period_returns_zeroed_stats(self, repo):
        stats = repo.get_performance_stats(days=30)
        assert stats['total_signals'] == 0
        assert stats['win_rate'] == 0.0
        assert stats['avg_r_multiple'] == 0.0

    def test_filters_by_symbol_and_timeframe(self, repo):
        repo.create(make_signal(symbol="XAUUSD", timeframe="1h", status=SignalStatus.PENDING))
        repo.create(make_signal(symbol="XAUUSD", timeframe="4h", status=SignalStatus.PENDING))

        stats = repo.get_performance_stats(days=30, symbol="XAUUSD", timeframe="1h")
        assert stats['total_signals'] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/engine && source venv/bin/activate && python -m pytest tests/test_signal_repository.py -v -k PerformanceStats`
Expected: FAIL — `KeyError: 'tp_hits'` (old dict doesn't have this key)

- [ ] **Step 3: Rewrite get_performance_stats**

In `packages/engine/src/database/signal_repository.py`, replace the entire method (lines 210-266):
```python
    def get_performance_stats(self, days: int = 30) -> dict:
        """
        Calculate performance statistics for the last N days.

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary with performance metrics
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Get all closed signals in period
        closed_signals = (
            self.session.query(Signal)
            .filter(
                and_(
                    Signal.timestamp >= cutoff_date,
                    Signal.status.in_([SignalStatus.CLOSED_TP, SignalStatus.CLOSED_SL, SignalStatus.CLOSED_MANUAL])
                )
            )
            .all()
        )

        if not closed_signals:
            return {
                'total_signals': 0,
                'winning_signals': 0,
                'losing_signals': 0,
                'win_rate': 0.0,
                'total_pnl': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'largest_win': 0.0,
                'largest_loss': 0.0,
                'profit_factor': 0.0,
            }

        # Calculate metrics
        winners = [s for s in closed_signals if s.pnl and s.pnl > 0]
        losers = [s for s in closed_signals if s.pnl and s.pnl < 0]

        total_wins = sum(s.pnl for s in winners)
        total_losses = abs(sum(s.pnl for s in losers))

        return {
            'total_signals': len(closed_signals),
            'winning_signals': len(winners),
            'losing_signals': len(losers),
            'win_rate': (len(winners) / len(closed_signals) * 100) if closed_signals else 0.0,
            'total_pnl': sum(s.pnl for s in closed_signals if s.pnl),
            'avg_win': (total_wins / len(winners)) if winners else 0.0,
            'avg_loss': (total_losses / len(losers)) if losers else 0.0,
            'largest_win': max((s.pnl for s in winners), default=0.0),
            'largest_loss': min((s.pnl for s in losers), default=0.0),
            'profit_factor': (total_wins / total_losses) if total_losses > 0 else 0.0,
        }
```
with:
```python
    def get_performance_stats(self, days: int = 30, symbol: str = None, timeframe: str = None) -> dict:
        """
        Calculate signal outcome statistics for the last N days.

        No dollar P&L is used (there is no real account behind these signals
        yet) — win rate is measured over resolved (TP/SL) signals, and
        edge is measured in R-multiples (pnl_pips / risk_pips).

        Args:
            days: Number of days to analyze
            symbol: If given, only signals for this symbol
            timeframe: If given, only signals for this timeframe

        Returns:
            Dictionary with keys: total_signals, tp_hits, sl_hits, expired,
            still_open, closed_manual, win_rate, avg_r_multiple, net_r_multiple
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        filters = [Signal.timestamp >= cutoff_date]
        if symbol:
            filters.append(Signal.symbol == symbol)
        if timeframe:
            filters.append(Signal.timeframe == timeframe)

        all_signals = self.session.query(Signal).filter(and_(*filters)).all()

        tp_hits = [s for s in all_signals if s.status == SignalStatus.CLOSED_TP]
        sl_hits = [s for s in all_signals if s.status == SignalStatus.CLOSED_SL]
        expired = [
            s for s in all_signals
            if s.status == SignalStatus.CANCELLED and s.notes and '[expired' in s.notes
        ]
        still_open = [s for s in all_signals if s.status in (SignalStatus.PENDING, SignalStatus.ACTIVE)]
        closed_manual = [s for s in all_signals if s.status == SignalStatus.CLOSED_MANUAL]

        resolved = tp_hits + sl_hits
        win_rate = (len(tp_hits) / len(resolved) * 100) if resolved else 0.0

        r_multiples = [
            s.pnl_pips / s.risk_pips
            for s in resolved
            if s.risk_pips and s.pnl_pips is not None
        ]
        avg_r = (sum(r_multiples) / len(r_multiples)) if r_multiples else 0.0
        net_r = sum(r_multiples)

        return {
            'total_signals': len(all_signals),
            'tp_hits': len(tp_hits),
            'sl_hits': len(sl_hits),
            'expired': len(expired),
            'still_open': len(still_open),
            'closed_manual': len(closed_manual),
            'win_rate': win_rate,
            'avg_r_multiple': avg_r,
            'net_r_multiple': net_r,
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/engine && source venv/bin/activate && python -m pytest tests/test_signal_repository.py -v`
Expected: PASS (all tests in this file, ~9 total)

- [ ] **Step 5: Run the full test suite to check for regressions**

Run: `cd packages/engine && source venv/bin/activate && python -m pytest tests/ -v`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
cd packages/engine
git add src/database/signal_repository.py tests/test_signal_repository.py
git commit -m "feat: report signal outcomes via TP/SL/expired/open counts and R-multiple"
```

---

### Task 8: On-demand performance report script

**Files:**
- Create: `packages/engine/report.py`
- Test: `packages/engine/tests/test_report.py`

**Interfaces:**
- Consumes: `SignalRepository.get_performance_stats()` (Task 7).
- Produces: `build_report_text(stats: dict, days: int) -> str`. Task 9 imports this to reuse the same formatting for the Telegram message.

- [ ] **Step 1: Write the failing test**

Create `packages/engine/tests/test_report.py`:
```python
"""Tests for the on-demand performance report."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from report import build_report_text


class TestBuildReportText:
    def test_includes_all_key_numbers(self):
        stats = {
            'total_signals': 20,
            'tp_hits': 15,
            'sl_hits': 4,
            'expired': 1,
            'still_open': 0,
            'closed_manual': 0,
            'win_rate': 78.9,
            'avg_r_multiple': 1.2,
            'net_r_multiple': 22.8,
        }
        text = build_report_text(stats, days=7)

        assert "7" in text
        assert "20" in text
        assert "15" in text
        assert "4" in text
        assert "78.9" in text
        assert "22.8" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/engine && source venv/bin/activate && python -m pytest tests/test_report.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'report'`

- [ ] **Step 3: Implement report.py**

Create `packages/engine/report.py`:
```python
#!/usr/bin/env python3
"""
On-demand signal performance report.

Usage:
    python report.py                    # last 7 days
    python report.py --days 30
    python report.py --timeframe 1h
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from database.connection import DatabaseManager
from database.signal_repository import SignalRepository


def build_report_text(stats: dict, days: int) -> str:
    """Format a performance stats dict (from get_performance_stats) as text."""
    return (
        f"📊 Signal Performance Report ({days}d)\n"
        f"Total signals: {stats['total_signals']}\n"
        f"TP hits: {stats['tp_hits']}\n"
        f"SL hits: {stats['sl_hits']}\n"
        f"Expired: {stats['expired']}\n"
        f"Still open: {stats['still_open']}\n"
        f"Win rate: {stats['win_rate']:.1f}%\n"
        f"Avg R-multiple: {stats['avg_r_multiple']:.2f}\n"
        f"Net R-multiple: {stats['net_r_multiple']:.2f}"
    )


def main():
    parser = argparse.ArgumentParser(description="Gold Trader's Edge - Signal Performance Report")
    parser.add_argument('--days', type=int, default=7, help='Number of days to look back (default: 7)')
    parser.add_argument('--symbol', type=str, default=None)
    parser.add_argument('--timeframe', type=str, default=None)
    args = parser.parse_args()

    db_manager = DatabaseManager()
    with db_manager.session_scope() as session:
        repo = SignalRepository(session)
        stats = repo.get_performance_stats(days=args.days, symbol=args.symbol, timeframe=args.timeframe)

    print(build_report_text(stats, args.days))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/engine && source venv/bin/activate && python -m pytest tests/test_report.py -v`
Expected: PASS

- [ ] **Step 5: Manually verify the CLI runs end to end**

Run:
```bash
cd packages/engine
source venv/bin/activate
DATABASE_URL="sqlite:///signals.db" python report.py --days 30
```
Expected: prints the report text with real numbers from the local `signals.db` (likely all zeros if no signals have fired yet — that's fine, it should not error).

- [ ] **Step 6: Commit**

```bash
cd packages/engine
git add report.py tests/test_report.py
git commit -m "feat: add on-demand signal performance report script"
```

---

### Task 9: Weekly Telegram performance report

**Files:**
- Modify: `packages/engine/run_multi_timeframe_service.py` (`MultiTimeframeService.__init__`, `_monitor_loop`)
- Test: `packages/engine/tests/test_weekly_report.py`

**Interfaces:**
- Consumes: `build_report_text` (Task 8), `SignalRepository.get_performance_stats` (Task 7), `TelegramSubscriber.send_custom_message` (existing).

- [ ] **Step 1: Write the failing test**

Create `packages/engine/tests/test_weekly_report.py`:
```python
"""Tests for the weekly Telegram report."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import run_multi_timeframe_service as svc_module


class TestSendWeeklyReport:
    def test_sends_formatted_report_via_telegram(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "fake-chat-id")

        service = svc_module.MultiTimeframeService.__new__(svc_module.MultiTimeframeService)
        service.database_url = "sqlite:///:memory:"
        service.telegram_subscriber = MagicMock()

        fake_stats = {
            'total_signals': 10, 'tp_hits': 6, 'sl_hits': 3, 'expired': 1,
            'still_open': 0, 'closed_manual': 0, 'win_rate': 66.7,
            'avg_r_multiple': 0.9, 'net_r_multiple': 8.1,
        }
        with patch.object(svc_module.SignalRepository, 'get_performance_stats', return_value=fake_stats):
            with patch("database.connection.DatabaseManager.session_scope"):
                service._send_weekly_report()

        service.telegram_subscriber.send_custom_message.assert_called_once()
        message = service.telegram_subscriber.send_custom_message.call_args[0][0]
        assert "Weekly" in message
        assert "66.7" in message
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/engine && source venv/bin/activate && python -m pytest tests/test_weekly_report.py -v`
Expected: FAIL with `AttributeError: type object 'MultiTimeframeService' has no attribute '_send_weekly_report'`

- [ ] **Step 3: Store subscriber references and add the import**

In `packages/engine/run_multi_timeframe_service.py`, add near the top of the file (alongside the existing imports around line 30-37):
```python
from database.signal_repository import SignalRepository
from report import build_report_text
```

Then find, in `MultiTimeframeService.__init__` (around line 242-249):
```python
        db_subscriber = DatabaseSubscriber(database_url=self.database_url)
        telegram_subscriber = TelegramSubscriber()

        self.shared_dedup_subscriber = DeduplicationSubscriber(
            subscribers=[db_subscriber, telegram_subscriber],
            dedup_window_hours=4,
            database_url=self.database_url  # Pass database URL for persistence
        )
```
Replace with:
```python
        db_subscriber = DatabaseSubscriber(database_url=self.database_url)
        telegram_subscriber = TelegramSubscriber()
        self.telegram_subscriber = telegram_subscriber  # kept for weekly reports

        self.shared_dedup_subscriber = DeduplicationSubscriber(
            subscribers=[db_subscriber, telegram_subscriber],
            dedup_window_hours=4,
            database_url=self.database_url  # Pass database URL for persistence
        )
```

- [ ] **Step 4: Implement _send_weekly_report**

Add this method to `MultiTimeframeService`, right after `_display_status` (or any existing private helper method — exact placement doesn't matter as long as it's a method of the class):
```python
    def _send_weekly_report(self):
        """Send the last 7 days of signal performance stats to Telegram."""
        from database.connection import DatabaseManager
        try:
            db_manager = DatabaseManager(self.database_url)
            with db_manager.session_scope() as session:
                repo = SignalRepository(session)
                stats = repo.get_performance_stats(days=7)

            message = "📅 Weekly Performance Report\n\n" + build_report_text(stats, days=7)
            self.telegram_subscriber.send_custom_message(message)
            logger.info("✅ Weekly performance report sent to Telegram")
        except Exception as e:
            logger.error(f"Failed to send weekly report: {e}", exc_info=True)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd packages/engine && source venv/bin/activate && python -m pytest tests/test_weekly_report.py -v`
Expected: PASS

- [ ] **Step 6: Wire the weekly check into _monitor_loop**

In `packages/engine/run_multi_timeframe_service.py`, find `_monitor_loop` (around line 305-320):
```python
    def _monitor_loop(self):
        """
        Monitor all workers and display status periodically.
        Also sends keep-alive pings to prevent Railway from sleeping.
        """
        last_status_time = datetime.now()
        last_keepalive_time = datetime.now()
        status_interval = 300  # 5 minutes
        keepalive_interval = 240  # 4 minutes (ping API to keep it awake)

        while self.is_running:
            time.sleep(10)  # Check every 10 seconds
```
Replace with:
```python
    def _monitor_loop(self):
        """
        Monitor all workers and display status periodically.
        Also sends keep-alive pings to prevent Railway from sleeping,
        and a weekly performance report to Telegram.
        """
        last_status_time = datetime.now()
        last_keepalive_time = datetime.now()
        last_report_time = datetime.now()
        status_interval = 300  # 5 minutes
        keepalive_interval = 240  # 4 minutes (ping API to keep it awake)
        report_interval = 7 * 24 * 3600  # weekly

        while self.is_running:
            time.sleep(10)  # Check every 10 seconds

            if (datetime.now() - last_report_time).total_seconds() >= report_interval:
                self._send_weekly_report()
                last_report_time = datetime.now()
```

- [ ] **Step 7: Run the full test suite to check for regressions**

Run: `cd packages/engine && source venv/bin/activate && python -m pytest tests/ -v`
Expected: all pass.

- [ ] **Step 8: Commit**

```bash
cd packages/engine
git add run_multi_timeframe_service.py tests/test_weekly_report.py
git commit -m "feat: send automatic weekly performance report to Telegram"
```

---

### Task 10: Strategy tuning script (tune_strategy.py)

**Files:**
- Create: `packages/engine/tune_strategy.py`
- Test: `packages/engine/tests/test_tune_strategy.py`

**Interfaces:**
- Consumes: `GoldDataLoader` (`data.loader`), `GoldStrategy`, `create_strategy_function` (`signals.gold_strategy`), `BacktestEngine`, `TradeStatus` (`backtesting.engine`) — all existing.
- Produces: `split_train_test(df, train_frac) -> (train_df, test_df)`, `run_isolated_backtest(df, rule_name, config) -> (profit_factor, total_trades, BacktestResult)`, `tune_rule(train_df, rule_name) -> dict` (config), `validate_rule(test_df, rule_name, config) -> (dict, list[float])` (stats, trade durations in hours), `percentile(values, pct) -> float`. Task 11 runs this script's `main()` against real data; nothing else imports these functions, but they must stay named exactly this for the adversarial review in Task 11 to reference them.

- [ ] **Step 1: Write the failing tests**

Create `packages/engine/tests/test_tune_strategy.py`:
```python
"""Tests for the strategy tuning script's core mechanics, using synthetic data."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from tune_strategy import split_train_test, percentile, BASE_1H_CONFIG, run_isolated_backtest


class TestSplitTrainTest:
    def test_splits_chronologically_at_given_fraction(self):
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1h')
        df = pd.DataFrame({'close': range(100)}, index=dates)

        train, test = split_train_test(df, train_frac=0.7)

        assert len(train) == 70
        assert len(test) == 30
        assert train.index[-1] < test.index[0]
        assert train.index[-1] == dates[69]
        assert test.index[0] == dates[70]


class TestPercentile:
    def test_matches_known_values(self):
        values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        assert percentile(values, 50) == pytest.approx(5.5)
        assert percentile(values, 0) == 1
        assert percentile(values, 100) == 10

    def test_empty_list_returns_zero(self):
        assert percentile([], 95) == 0.0


class TestRunIsolatedBacktest:
    def test_only_enables_the_requested_rule(self):
        np.random.seed(42)
        dates = pd.date_range(start='2024-01-01', periods=300, freq='1h')
        base_price = 2000
        trend = np.cumsum(np.random.normal(0.3, 2, len(dates)))
        close = base_price + trend
        high = close + np.abs(np.random.normal(0, 5, len(dates)))
        low = close - np.abs(np.random.normal(0, 5, len(dates)))
        open_prices = close + np.random.normal(0, 2, len(dates))
        high = np.maximum(high, np.maximum(open_prices, close))
        low = np.minimum(low, np.minimum(open_prices, close))
        df = pd.DataFrame({'open': open_prices, 'high': high, 'low': low, 'close': close}, index=dates)

        pf, trades, result = run_isolated_backtest(df, 'momentum_equilibrium', BASE_1H_CONFIG)

        assert isinstance(pf, float)
        assert isinstance(trades, int)
        assert result.total_trades == trades
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/engine && source venv/bin/activate && python -m pytest tests/test_tune_strategy.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tune_strategy'`

- [ ] **Step 3: Implement tune_strategy.py**

Create `packages/engine/tune_strategy.py`:
```python
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

        passed_individually = (
            individual_test_stats['profit_factor'] > 1.0
            and individual_test_stats['total_trades'] >= MIN_TEST_TRADES
        )
        print(f"  train: PF={train_stats['profit_factor']:.2f} trades={train_stats['total_trades']}")
        print(
            f"  test (own config): PF={individual_test_stats['profit_factor']:.2f} "
            f"trades={individual_test_stats['total_trades']} "
            f"-> {'candidate' if passed_individually else 'rejected'}"
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
        passed = stats['profit_factor'] > 1.0 and stats['total_trades'] >= MIN_TEST_TRADES
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/engine && source venv/bin/activate && python -m pytest tests/test_tune_strategy.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
cd packages/engine
git add tune_strategy.py tests/test_tune_strategy.py
git commit -m "feat: add 1H strategy tuning script with train/test validation"
```

---

### Task 11: Run the real tuning with adversarial review

This task has no unit tests of its own — it executes Task 10's script against the real data from Task 1 and produces the artifact Task 12 consumes. Given real capital is the eventual target, this specific task must be run by two independent high-reasoning-effort passes rather than a single quick execution.

**Files:**
- Output: `packages/engine/tuned_configs/1h.json`

**Interfaces:**
- Consumes: `packages/engine/tune_strategy.py` (Task 10), `packages/engine/data/processed/xauusd_1h_2024_2026.csv` (Task 1, or whatever exact filename Task 1's Step 2 reported).
- Produces: `packages/engine/tuned_configs/1h.json` matching the schema written by `tune_strategy.py`'s `main()`. Task 12 reads `config`, `enabled_rules`, and `expiry_hours` from this file by exact key name.

- [ ] **Step 1: Dispatch the tuning execution agent**

Use the Agent tool with `model: opus`, `effort: high`, and this prompt (fill in the exact data filename from Task 1):

> Run `packages/engine/tune_strategy.py` against `packages/engine/data/processed/<exact filename from Task 1>` from the `packages/engine` directory using the venv at `packages/engine/venv` (activate it first). Report: the full stdout, the resulting `tuned_configs/1h.json` contents, and your own written assessment of overfitting risk — specifically: (a) does the train/test split look free of any leakage (test dates strictly after train dates, with no overlap), (b) is `MIN_TRAIN_TRADES`/`MIN_TEST_TRADES` being enforced correctly (a rule with too few trades in either slice should not ship enabled), (c) does the final shared-config re-validation in the script's output show any candidate rule that passed individually but failed under the shared config (if so, confirm it was correctly excluded from `enabled_rules`), and (d) anything else that looks statistically suspicious (e.g. suspiciously round numbers, a rule with very few trades but a huge profit factor).

- [ ] **Step 2: Dispatch the adversarial review agent**

Use the Agent tool with `model: opus`, `effort: high`, and this prompt (fill in the actual `tuned_configs/1h.json` produced by Step 1, pasted inline or by file path):

> Independently review `packages/engine/tuned_configs/1h.json` and the script that produced it (`packages/engine/tune_strategy.py`) for correctness, without trusting the first agent's self-assessment. Specifically: (1) Re-derive the reported profit factor and trade count for at least 2 of the 5 rules from scratch by running `python tune_strategy.py --data <path> --output /tmp/reverify.json` yourself and diffing the result against the original — the numbers must match exactly (deterministic script, same input). (2) Check `split_train_test` for date-range leakage — read the function and confirm the split index truly means every train-slice timestamp is before every test-slice timestamp. (3) Check `tune_rule`'s coordinate search for lookahead bias — confirm no parameter or code path lets a rule "see" data beyond the current candle index during `BacktestEngine.run()` (this class was already validated for 4H, so this is mainly confirming nothing new was introduced here). (4) Check whether `final_config`'s median-based construction produced a config no individual rule was actually tuned around (e.g., if it picks a `trend_lookback` no candidate rule tested), and if so, whether the final shared-config re-validation step still shows real profitability for every rule in `enabled_rules` — this is the step that should catch that problem, confirm it does. Report PASS/FAIL with specifics for each of these four checks, and flag anything else suspicious.

- [ ] **Step 3: Resolve any disagreement**

If either agent flags a real problem (not a false alarm), fix `tune_strategy.py` accordingly, re-run both steps above, and do not proceed until both agents agree the output is trustworthy. Record what was found and fixed (if anything) in the commit message for this task.

- [ ] **Step 4: Confirm the output file is complete**

Run:
```bash
cd packages/engine
python3 -c "
import json
with open('tuned_configs/1h.json') as f:
    data = json.load(f)
assert 'config' in data and isinstance(data['config'], dict)
assert 'enabled_rules' in data and isinstance(data['enabled_rules'], list)
assert 'expiry_hours' in data and isinstance(data['expiry_hours'], (int, float))
print('enabled_rules:', data['enabled_rules'])
print('expiry_hours:', data['expiry_hours'])
print('OK')
"
```
Expected: `OK`, and `enabled_rules` is non-empty (if it's empty, the strategy has no rule that survived real 1H validation — stop and discuss with the user before proceeding to Task 12, do not ship an empty strategy silently).

- [ ] **Step 5: Commit**

```bash
cd packages/engine
git add tuned_configs/1h.json
git commit -m "feat: add validated 1H strategy config from real-data tuning"
```

---

### Task 12: Wire the tuned config into the live service and scope to 1H only

**Files:**
- Modify: `packages/engine/run_multi_timeframe_service.py` (`TIMEFRAMES`, `TimeframeWorker._run`, `MultiTimeframeService.start`)
- Test: `packages/engine/tests/test_timeframe_scope.py`

**Interfaces:**
- Consumes: `packages/engine/tuned_configs/1h.json` (Task 11).

- [ ] **Step 1: Write the failing test**

Create `packages/engine/tests/test_timeframe_scope.py`:
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

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/engine && source venv/bin/activate && python -m pytest tests/test_timeframe_scope.py -v`
Expected: FAIL — `TIMEFRAMES == ['5m', '15m', '30m', '1h', '4h', '1d']`

- [ ] **Step 3: Scope TIMEFRAMES down to 1h**

In `packages/engine/run_multi_timeframe_service.py`, find (around line 54):
```python
# All timeframes to monitor
TIMEFRAMES = ['5m', '15m', '30m', '1h', '4h', '1d']
```
Replace with:
```python
# Only 1H has been re-tuned and validated against real market data
# (see docs/superpowers/specs/2026-08-22-signal-validation-and-outcome-tracking-design.md).
# The other timeframes are left available in the code but not run live
# until each is independently validated the same way.
TIMEFRAMES = ['1h']
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/engine && source venv/bin/activate && python -m pytest tests/test_timeframe_scope.py -v`
Expected: PASS

- [ ] **Step 5: Load the tuned config in TimeframeWorker**

In `packages/engine/run_multi_timeframe_service.py`, add `import json` near the top with the other imports (it's not currently imported). Then find, in `TimeframeWorker._run()` (the block modified in Task 6 Step 6):
```python
            # Create strategy - default config until Task 12 wires in the
            # tuned 1h config
            strategy = GoldStrategy()

            enabled_names = [name for name, on in strategy.rules_enabled.items() if on]
            logger.info(f"   [{self.timeframe}] Enabled rules: {enabled_names}")

            outcome_tracker = SignalOutcomeTracker(
                database_url=self.database_url,
                symbol='XAUUSD',
                timeframe=self.timeframe,
                expiry_hours=48.0,  # placeholder until Task 12 loads the data-derived value
            )
```
Replace with:
```python
            # Load the tuned config for this timeframe if one exists;
            # otherwise fall back to defaults (no other timeframe has a
            # tuned config yet — see TIMEFRAMES above).
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

            enabled_names = [name for name, on in strategy.rules_enabled.items() if on]
            logger.info(f"   [{self.timeframe}] Enabled rules: {enabled_names}")

            outcome_tracker = SignalOutcomeTracker(
                database_url=self.database_url,
                symbol='XAUUSD',
                timeframe=self.timeframe,
                expiry_hours=expiry_hours,
            )
```

- [ ] **Step 6: Update the startup rule-count display**

In `packages/engine/run_multi_timeframe_service.py`, find in `MultiTimeframeService.start()` (around line 261-263):
```python
        print(f"\n🎯 Monitoring Timeframes: {', '.join(self.timeframes)}")
        print(f"📈 Enabled Rules ({len(PROFITABLE_RULES)}):")
        for rule in PROFITABLE_RULES:
            print(f"   ✅ {rule}")
```
Replace with:
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

- [ ] **Step 7: Smoke-test the full wiring**

Run:
```bash
cd packages/engine
source venv/bin/activate
rm -f /tmp/final_smoke.db
DATABASE_URL="sqlite:////tmp/final_smoke.db" python3 -c "
import sys; sys.path.insert(0, 'src')
from run_multi_timeframe_service import MultiTimeframeService
svc = MultiTimeframeService(database_url='sqlite:////tmp/final_smoke.db')
svc.start()
" > /tmp/final_smoke.log 2>&1 &
sleep 15
kill %1 2>/dev/null
cat /tmp/final_smoke.log | grep -E "Loaded tuned config|Enabled rules|Error|Traceback"
```
Expected: shows `Loaded tuned config from .../tuned_configs/1h.json` and `Enabled rules: [...]` listing whatever `tuned_configs/1h.json` actually contains, with no errors/tracebacks.

- [ ] **Step 8: Run the full test suite**

Run: `cd packages/engine && source venv/bin/activate && python -m pytest tests/ -v`
Expected: all pass.

- [ ] **Step 9: Commit**

```bash
cd packages/engine
git add run_multi_timeframe_service.py tests/test_timeframe_scope.py
git commit -m "feat: scope live service to validated 1H timeframe with tuned config"
```

---

### Task 13: Remove hardcoded database credential

**Files:**
- Modify: `check_signals.py:5-13` (repo root)

**Interfaces:**
- None — standalone script fix.

- [ ] **Step 1: Replace the hardcoded connection string**

In `check_signals.py`, replace lines 5-13:
```python
import psycopg2
from datetime import datetime

# Railway DATABASE_URL
DATABASE_URL = "postgresql://postgres:WuOXHUmfceYvlbNuyUrhAsQgJPmFyhJv@postgres.railway.internal:5432/railway"

# For local testing, use the public URL (get from Railway dashboard)
# Replace this with your actual public connection string from Railway
# DATABASE_URL = "postgresql://postgres:password@<your-railway-host>:5432/railway"
```
with:
```python
import os
import sys
import psycopg2
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("❌ DATABASE_URL environment variable is not set.")
    print("   Set it to your Railway Postgres connection string before running this script, e.g.:")
    print("   DATABASE_URL='postgresql://...' python check_signals.py")
    sys.exit(1)
```

- [ ] **Step 2: Verify it fails closed without the env var**

Run: `python3 check_signals.py`
Expected: prints the "DATABASE_URL environment variable is not set" message and exits with status 1 (does not attempt a connection).

- [ ] **Step 3: Commit**

```bash
git add check_signals.py
git commit -m "security: remove hardcoded Postgres credential from check_signals.py"
```

- [ ] **Step 4: Flag credential rotation to the user (not an automated step)**

This commit removes the credential from the file going forward, but the password is already exposed in git history from prior commits and must be rotated in the Railway dashboard (Postgres service → Variables → regenerate password) regardless of this fix. Tell the user this explicitly when reporting this task complete — do not consider the exposure resolved just because the file is fixed.

---

### Task 14: Railway deployment configuration (manual — requires the user's Railway access)

This task cannot be executed by an agent — it requires access to the user's Railway dashboard. Whoever picks up this task should present these exact steps to the user rather than attempting to log into Railway on their behalf.

**Files:** none (environment configuration only)

- [ ] **Step 1: Confirm the Postgres DATABASE_URL Railway env var**

In the Railway project's service running `run_multi_timeframe_service.py` (via `supervisord`), confirm a `DATABASE_URL` environment variable is set to the Postgres connection string, in the form `postgresql://<user>:<password>@<host>:<port>/<database>`. If the credential was rotated per Task 13, use the new password here.

- [ ] **Step 2: Add Telegram environment variables**

Add two environment variables to the same Railway service:
- `TELEGRAM_BOT_TOKEN` — the value currently sitting in `packages/engine/.env` locally (not deployed anywhere yet).
- `TELEGRAM_CHAT_ID` — same source.

- [ ] **Step 3: Redeploy and verify**

Trigger a redeploy (Railway redeploys automatically on git push to the connected branch, once Tasks 1-13's commits are pushed). After it's up, check the deploy logs for the same startup sequence verified locally in Task 12 Step 7 (`Loaded tuned config from .../tuned_configs/1h.json`, `Enabled rules: [...]`, no tracebacks), and confirm a real Telegram message eventually arrives once a live 1H signal fires.

- [ ] **Step 4: Report back**

Once verified live, report to the user: which timeframe is running, which rules are enabled, the expiry window in hours, and remind them the weekly Telegram report will not send anything meaningful until at least one full week of signals has accumulated.

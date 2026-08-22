# Signal Re-Tuning, Outcome Tracking & Reporting — Design

**Date:** 2026-08-22
**Status:** Approved for implementation planning

## Problem

The Gold Trader's Edge currently generates trading signals but has no way to
know whether they're actually good:

1. The live/deployed entry point (`run_multi_timeframe_service.py`, run via
   `supervisord` in the Railway container) runs 6 timeframes (5m/15m/30m/1h/4h/1d)
   simultaneously using the same `GoldStrategy()` default config on all of
   them. Only the 4H config has ever been validated against real market data
   (see the 2026-08-22 backtest session: all 5 rules profitable in isolation
   on 2025-2026 real XAUUSD 4H data — Momentum Equilibrium 80.8% WR/PF 4.58,
   Order Block Retest 41.5% WR/PF 1.35, London Session Breakout 57.1% WR/PF
   2.18, Golden Fibonacci 51.6% WR/PF 1.46, ATH Retest 38.8% WR/PF 1.15).
2. 4H is too infrequent for the user's needs. 1H was chosen as the
   replacement (see decision log below) but the strategy's lookback
   parameters were never re-tuned or validated for 1H — they were carried
   over unchanged from 4H tuning.
3. Once a signal is generated and sent to Telegram, nothing tracks what
   actually happens to it. There's no record of whether price went on to
   hit the take-profit, the stop-loss, or neither. The user cannot answer
   "is this system actually working" without this.
4. There is no recurring performance report.

## Decision log (from brainstorming session)

- Timeframe: **1H**, re-tuned and validated from scratch (not just re-polled
  at the same 4H logic). Yahoo Finance gives 730 days of real 1H history —
  same depth as the trusted 4H validation — vs. only ~60 days for 15m/30m.
- Tuning depth: **full grid-search**, not just a lookback rescale.
- "Did not activate" = **expired**: a distinct outcome from "still open,"
  triggered when a signal has neither hit TP nor SL after a data-derived
  maximum holding time.
- Reporting: **both** an automatic weekly Telegram summary and an on-demand
  script.
- Canonical service: **`run_multi_timeframe_service.py`**, scoped down to
  `TIMEFRAMES = ['1h']` only. The other 5 timeframes and the redundant
  `run_signal_service.py` dev script are retired from the live path (left in
  the repo, just not run) until each is independently re-tuned and validated
  the same way.
- Rigor: tuning and validation is executed and adversarially reviewed by
  separate high-reasoning-effort Opus agents, given real capital is the
  eventual target.

## Non-goals

- No auto-trading changes. `MT5Subscriber`/`enable_trading` stay disabled;
  this work is entirely about alert quality and post-hoc verification.
- No re-tuning of 5m/15m/30m/4h/1d in this pass — only 1H.
- No new database tables or columns (see Data model, below — the existing
  schema already covers everything needed).
- No dollar P&L fabrication. There is no real account behind these signals
  yet, so outcomes are tracked in **price/pips/R-multiple** terms only;
  `pnl`/`pnl_pct` stay null until real trading exists.

## Architecture overview

```
run_multi_timeframe_service.py (TIMEFRAMES=['1h'])
  └─ TimeframeWorker(timeframe='1h')
       └─ RealtimeSignalGenerator
            ├─ GoldStrategy(config=<tuned_configs/1h.json:config>,
            │                rules_enabled=<tuned_configs/1h.json:enabled_rules>)
            ├─ subscribers: [shared_dedup(db, telegram), logger, console]
            └─ outcome_tracker: SignalOutcomeTracker   <-- NEW
                 (invoked once per candle inside run_once(), after
                  fetching the latest candle, before checking for a
                  new entry signal)
```

Weekly reporting is a second lightweight loop inside
`MultiTimeframeService._monitor_loop()` (which already runs every 10s for
worker-health and Railway keepalive checks) — it just adds a "has a week
passed since the last report" check alongside the existing ones.

## Component 1: Strategy re-tuning & validation (offline, one-time per rule set)

**New file:** `packages/engine/tune_strategy.py`

Inputs: `packages/engine/data/processed/xauusd_1h_<start>_<end>.csv` (fetched
via the existing `fetch_real_data.py --timeframe 1h`, covering the full
available 730-day window).

Process:
1. Load the CSV, sort by time, split chronologically at the 70% mark into
   `train_df` and `test_df` (test = most recent 30%, since that best
   simulates "how would this perform going forward").
2. For each rule independently (using `run_backtest.py`'s existing
   `--rules <name>` isolation mode, which avoids the shared-trade-slot
   distortion discovered during the 4H validation):
   a. Compute 1H-equivalent starting points for `swing_lookback`,
      `trend_lookback`, `atr_period` by scaling the 4H-tuned values by 4x
      (1H candles are 1/4 the duration of 4H candles, so the same *real
      time* window needs 4x the candle count).
   b. Grid-search a small neighborhood around those starting points, plus
      `fib_tolerance`, `default_rr_ratio`, and `strong_momentum_threshold`
      (a handful of values each — this is a targeted local search around an
      informed starting point, not a blind exhaustive sweep over the full
      parameter space).
   c. For each combination, run the backtest on `train_df` only. Rank
      candidates by profit factor, **requiring at least 15 trades** on the
      train slice (reject configs whose apparent edge comes from a handful
      of trades).
   d. Take the top candidate per rule and run it once against `test_df`
      (never used during search). Record win rate, profit factor, net
      return, and trade count on the held-out slice — this is the number
      that decides whether the rule ships enabled.
3. A rule is enabled in the final config only if its held-out test-slice
   profit factor is > 1.0 with at least 5 trades in the test slice. If a
   rule fails this bar, it's disabled and the config still records its
   attempted parameters and the failing test-slice numbers (for
   transparency, not silently dropped).
4. Compute the expiry window: across all trades from all *enabled* rules in
   the test-slice run, take `exit_time - entry_time` for every closed trade
   and use the 95th percentile (in hours), rounded up to the nearest whole
   hour, as `expiry_hours`.
5. Write `packages/engine/tuned_configs/1h.json`:
   ```json
   {
     "generated_at": "<ISO timestamp>",
     "symbol": "XAUUSD",
     "timeframe": "1h",
     "data_range": {"start": "...", "end": "...", "train_end": "..."},
     "config": { "fib_tolerance": ..., "swing_lookback": ..., "trend_lookback": ...,
                 "atr_period": ..., "default_rr_ratio": ..., "strong_momentum_threshold": ... },
     "enabled_rules": ["momentum_equilibrium", "..."],
     "expiry_hours": <int>,
     "validation": {
       "momentum_equilibrium": {"train": {...}, "test": {...}},
       "...": {"train": {...}, "test": {...}}
     }
   }
   ```

**Execution & review process** (not a new subsystem, a process requirement
on how step 1-5 above gets run):
- Dispatch one Agent with `model: opus`, `effort: high` to implement and run
  `tune_strategy.py` end to end and report the resulting
  `tuned_configs/1h.json` plus its own written assessment of overfitting
  risk.
- Dispatch a second Agent with `model: opus`, `effort: high` to
  adversarially review the first agent's work: re-derive a couple of the
  reported numbers independently, check the train/test split for date-range
  leakage, check the grid search for lookahead bias (e.g. using
  `trend_lookback` windows that peek past the current candle), and flag
  anything suspicious.
- Only after both agents agree does `tuned_configs/1h.json` get wired into
  the live service.

## Component 2: Signal outcome tracker (online, runs continuously)

**New file:** `packages/engine/src/signals/outcome_tracker.py`

```python
class SignalOutcomeTracker:
    def __init__(self, database_url: str, symbol: str, timeframe: str, expiry_hours: float):
        ...
    def check_candle(self, candle: pd.Series, candle_time: pd.Timestamp) -> None:
        """Called once per newly-closed candle. Closes or expires open signals."""
```

`check_candle` logic, run against every open (`PENDING` or `ACTIVE`) signal
for this `symbol`/`timeframe` whose `timestamp < candle_time` (never check a
signal against its own entry candle):

1. **Hit detection** — mirrors `BacktestEngine.check_and_close_trades()`
   exactly, for consistency with the validated backtest:
   - LONG: if `candle.low <= stop_loss` → `CLOSED_SL`; elif
     `candle.high >= take_profit` → `CLOSED_TP`.
   - SHORT: if `candle.high >= stop_loss` → `CLOSED_SL`; elif
     `candle.low <= take_profit` → `CLOSED_TP`.
   - On close: set `actual_exit`, `pnl_pips` (same formula as
     `Trade.close()`: `(exit-entry)*10` for LONG, `(entry-exit)*10` for
     SHORT), `closed_at = candle_time`, `status`. Leave `pnl`/`pnl_pct` null
     (no real account yet).
2. **Expiry** — if not closed by (1) and
   `candle_time - signal.timestamp > expiry_hours`, set
   `status = CANCELLED`, `closed_at = candle_time`,
   `notes = (existing notes) + " [expired after Xh with no resolution]"`.

No new tables or columns — reuses `SignalStatus.CLOSED_TP`,
`SignalStatus.CLOSED_SL`, and `SignalStatus.CANCELLED`, and the existing
`actual_exit`/`pnl_pips`/`closed_at`/`notes` columns.

**Wiring:** `RealtimeSignalGenerator.run_once()` gains an optional
`outcome_tracker` param; if set, it's called with the latest candle
(`df.iloc[-1]`, `df.index[-1]`) right after the candle is fetched, before
checking for a new entry signal. `TimeframeWorker._run()` constructs one
`SignalOutcomeTracker` per worker (only the `'1h'` worker exists post-scope-down)
using `expiry_hours` from `tuned_configs/1h.json`.

**Extend `SignalRepository`** (`packages/engine/src/database/signal_repository.py`)
with `get_open_signals(symbol, timeframe)` (filters `get_by_status` results
by symbol+timeframe) for the tracker to query each cycle.

## Component 3: Reporting

**Extend `SignalRepository.get_performance_stats()`** to also count open
(`PENDING`/`ACTIVE`) and expired (`CANCELLED` with the "[expired" marker in
notes) signals in the period, not just closed ones, and to report an
R-multiple (`pnl_pips / risk_pips`, signed) alongside win rate — since
there's no dollar P&L to lean on yet.

**New file:** `packages/engine/report.py` — CLI script,
`python report.py --days 7` (default 7), prints the same breakdown the
Telegram message sends: signals generated, TP hits, SL hits, expired,
still-open, win rate (of resolved signals), average R-multiple, net R.

**Weekly Telegram summary** — added to
`MultiTimeframeService._monitor_loop()` in `run_multi_timeframe_service.py`,
alongside the existing keepalive/status checks: track `last_report_sent`,
and once per 7 days (checked on the existing 10-second tick, so no new
thread/timer needed) call the same stats function and send it via
`TelegramSubscriber.send_custom_message()`.

## Component 4: Deployment

- `Dockerfile`/`supervisord.conf` need no structural change — they already
  invoke `run_multi_timeframe_service.py`. The `TIMEFRAMES = ['1h']` scope-down
  and `tuned_configs/1h.json` loading happen inside that script.
- Confirm `DATABASE_URL` in the Railway environment points at the existing
  Postgres instance (already provisioned — see `check_signals.py`'s
  hardcoded connection string from the earlier security finding; that
  hardcoded credential should be rotated and moved to an env var as part of
  this work, not left as-is).
- Move `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` into Railway's environment
  variables (currently only in the local `packages/engine/.env`, gitignored,
  not deployed).

## Testing

- **Tuning script**: unit test on a small synthetic OHLC fixture with a
  known, hand-computed TP/SL hit sequence, asserting the grid search picks
  the parameter combination that should win on that fixture.
- **Outcome tracker**: replay test — take a slice of the already-fetched
  real 1H data plus a handful of known signals (constructed with fixed
  entry/SL/TP), feed candles through `check_candle()` one at a time, and
  assert the final signal statuses/exit prices match what
  `BacktestEngine.check_and_close_trades()` concludes for the identical
  signals over the identical candles. This is the divergence check between
  the tracker and the trusted backtester.
- **Reporting**: unit test `get_performance_stats()` against a fixture set
  of signals covering every status (TP/SL/expired/still-open) and assert
  the counts and R-multiple math.

## Open risk accepted for this pass

Running the outcome tracker only once per candle close means intra-candle
ordering when both SL and TP are touched in the same 1H candle is a
simplifying assumption (SL-first), identical to the backtester's own
assumption — consistent, but still an assumption, not ground truth tick
data. Acceptable for now since it matches the same standard the validation
numbers were computed under; would need tick-level data to remove entirely.

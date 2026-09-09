# Wiring GBPUSD/EURUSD into the live multi-timeframe signal service — Design

**Date:** 2026-09-09
**Status:** Approved, not yet implemented

## Problem

`packages/engine/run_multi_timeframe_service.py` is single-instrument: it
hardcodes `symbol='XAUUSD'` when building the data feed, hardcodes
`GoldStrategy` as the strategy class, and every place that tracks
per-worker state (`last_processed_candle_by_timeframe`, the
`worker_heartbeat` payload, the `enabled_strategies` setting) keys off
*timeframe alone* — an implicit "one worker per timeframe" assumption that
was true only because gold was the only instrument.

`ForexSessionStrategy` (Asian Range London Breakout) is validated and
ready for GBPUSD and EURUSD (see `strategy-ledger.md` and
`2026-09-09-gbpusd-asian-range-breakout-design.md`) but has never run
against a live feed and isn't wired into the service at all. Making it
live requires generalizing the worker architecture to `(symbol,
strategy_class, timeframe)` as the unit of parallelism, not just adding a
config entry.

This is the smallest correct generalization: everywhere the code assumes
"the instrument" is gold, replace it with "the instrument for *this*
worker" and rekey shared state accordingly. It is not a rewrite — every
piece below reuses a pattern already established in this codebase.

## Goals

- Add GBPUSD and EURUSD as new live workers running `ForexSessionStrategy`
  on 1H, alongside the existing XAUUSD/`GoldStrategy`/`order_block_retest`
  worker, with **zero change to gold's observable behavior**.
- Both new workers run their real data feed, settings refresh, heartbeat,
  and restart-protection in production from day one — but their strategy
  rule ships **disabled**, so they generate zero signals, zero Telegram
  messages, and zero DB rows until a human explicitly flips them on.
- Fix the timeframe-only-keying bug this exposes: two workers sharing a
  timeframe string (e.g. `XAUUSD:1h` and `GBPUSD:1h`) must not corrupt each
  other's last-processed-candle or heartbeat state.
- Fix `YahooFinanceDataFeed.ticker_map`'s silent gold-fallback for
  unmapped symbols (a live latent bug, confirmed during design — see
  below).

## Non-goals

- Actually enabling GBPUSD/EURUSD signal generation in production. That is
  a separate, later decision the user makes explicitly after this ships
  and is verified live-but-disabled (mirrors how new `GoldStrategy` rules
  and `TIMEFRAMES` entries already ship disabled-by-default in this repo).
- A dynamic/DB-driven instrument registry with an admin API to add
  instruments without a code change (considered and rejected as approach
  B — see Approaches below).
- Any frontend redesign. Signal cards already render `signal.symbol`
  generically (`apps/web/app/controls/page.tsx:284`); since disabled
  workers produce no signals, there is nothing new to display yet.
  `apps/web/app/page.tsx`'s "Live on XAUUSD" marketing copy is left as-is.

## Approaches considered

**A — Chosen: generalize the existing code-constant model.** Replace
`TIMEFRAMES: List[str]` with a `WORKER_SPECS: List[WorkerSpec]` constant
(same pattern as today — a Python list, changed via deploy). Rekey the
settings that assumed one worker per timeframe from `timeframe` to
`worker_id`. Going live = a code change (moving a rule into the per-symbol
enabled list) + deploy, exactly like every other "ship disabled, flip
later" decision already made in this codebase.

**B — Rejected: dynamic DB-driven instruments table.** A new table holding
instrument definitions, loaded instead of a code constant, with an admin
API to add/toggle instruments without a code change. More powerful, but a
significantly bigger schema/admin-UI lift for a capability nobody asked
for — the actual decision here is between 3 known instruments, not a
self-service instrument marketplace. Rejected on YAGNI grounds.

**C — Rejected: separate Railway service per symbol.** Deploy
`run_multi_timeframe_service.py --symbol GBPUSD` as its own Railway
service instead of adding it to the existing process. Avoids touching
`TimeframeWorker` internals, but triples the ops/monitoring surface (3
services instead of 1) and still requires solving the heartbeat/status
rekeying problem in the API layer — so it adds infrastructure cost without
avoiding the actual hard part. Rejected.

## Design

### Components

**`WorkerSpec`** (new dataclass in `run_multi_timeframe_service.py`):
`symbol`, `strategy_class`, `timeframe`, `tuned_config_filename`. Replaces
the flat `TIMEFRAMES` list:

```python
WORKER_SPECS = [
    WorkerSpec(symbol='XAUUSD', strategy_class=GoldStrategy, timeframe='1h', tuned_config_filename='1h.json'),
    WorkerSpec(symbol='GBPUSD', strategy_class=ForexSessionStrategy, timeframe='1h', tuned_config_filename='gbpusd_1h.json'),
    WorkerSpec(symbol='EURUSD', strategy_class=ForexSessionStrategy, timeframe='1h', tuned_config_filename='eurusd_1h.json'),
]
```

**`TimeframeWorker`** (class name unchanged — renaming is out of scope,
minimizes churn) takes a `WorkerSpec` instead of a bare `timeframe`
string:
- `worker_id` property = `f"{spec.symbol}:{spec.timeframe}"`, used
  everywhere the code currently keys shared state by bare `timeframe`.
- `create_datafeed(symbol=spec.symbol, ...)` instead of hardcoded
  `'XAUUSD'`.
- `strategy = spec.strategy_class(config=tuned['config'])` instead of
  hardcoded `GoldStrategy`.
- `SignalOutcomeTracker(symbol=spec.symbol, ...)` instead of hardcoded
  `'XAUUSD'`.
- Tuned config loaded from `spec.tuned_config_filename` directly, not
  derived from `f'{timeframe}.json'` — `gbpusd_1h.json` and
  `eurusd_1h.json` both target timeframe `'1h'`, so deriving the filename
  from timeframe alone would collide.

**Tuned config loading must branch on shape** — confirmed by inspection
that `gbpusd_1h.json`/`eurusd_1h.json` (written by
`tune_forex_session_strategy.py`) do **not** have gold's `enabled_rules`
or `expiry_hours` keys at all (they have `enabled`/`train`/`test` instead,
which document the tuner's validation verdict, not a live control). The
current loader (`tuned['enabled_rules']`, `tuned['expiry_hours']`) would
`KeyError` immediately on worker start for these two symbols. Fix: if
`enabled_rules` is present in the tuned config, seed `rules_enabled` from
it (gold's existing path, unchanged); if absent, leave `rules_enabled` at
the strategy class's own constructor default. This is safe because
`RealtimeSignalGenerator.start()` calls `pre_run_hook()` before the first
`run_once()` (confirmed by reading `realtime_generator.py`) — so
`refresh_settings()` reading `enabled_strategies["GBPUSD"] == []` from the
DB disables the rule before any evaluation happens regardless, on
iteration 1. Similarly, fall back to `expiry_hours = 48.0` (the same
constant already used today when no tuned config exists at all) when the
tuned config doesn't specify one.

**`MultiTimeframeService`** iterates `WORKER_SPECS`, starts **all** of
them as live threads (per the "run live, rule disabled" decision — there
is no spec-level `enabled` flag gating thread creation). All workers
continue to share the existing `shared_dedup_subscriber`/
`telegram_subscriber` unchanged: signal deduplication keys on exact
(cent-rounded) entry/SL/TP price, which cannot collide across different
instruments' price ranges, so no change is needed there.

**Data feed fix** (`packages/engine/src/data/realtime_feed.py`,
`YahooFinanceDataFeed.ticker_map`): confirmed live via the project venv
(`./venv/bin/python3` + yfinance) that `GBPUSD=X` and `EURUSD=X` are valid
tickers returning proper hourly OHLC, tz-aware `Europe/London`, and that
the existing `tz_convert('UTC').tz_localize(None)` normalization already
handles them correctly (it is generic, not actually GC=F-specific despite
its comment). Two changes:
1. Add `'GBPUSD': 'GBPUSD=X'` and `'EURUSD': 'EURUSD=X'` to `ticker_map`.
2. Change the `.get(self.symbol, "GC=F")` fallback to raise on an
   unmapped symbol instead of silently defaulting to gold — this was a
   real latent bug (any future unmapped symbol silently fetches gold
   data), independent of this task's scope but directly relevant to it.

### Data flow (per candle close, per worker)

1. `TimeframeWorker._run()` computes `worker_id` once at thread start.
2. `refresh_settings()` reads `enabled_strategies[spec.symbol]` (new dict
   shape — see Settings migration) instead of a flat list, applying it to
   `strategy.rules_enabled` exactly as today.
3. `get_last_processed_candle()`/`save_last_processed_candle()` read/write
   `last_processed_candle_by_worker[worker_id]` instead of
   `last_processed_candle_by_timeframe[timeframe]`.
4. `_save_heartbeat()` writes `heartbeat['workers'][worker_id] = {...}`
   instead of `[timeframe]`.

### Settings schema changes

**`enabled_strategies`: flat list → dict keyed by symbol.**
GBPUSD and EURUSD both use `ForexSessionStrategy`'s rule name
`'asian_range_london_breakout'` — a flat list of rule names cannot express
"enabled for GBPUSD but not EURUSD". New shape:
```json
{"XAUUSD": ["order_block_retest"], "GBPUSD": [], "EURUSD": []}
```
Empty lists for the new symbols *are* the "shipped disabled" mechanism,
since worker threads always start regardless (per Goals). A missing key
for a symbol (e.g. a future 4th instrument added without updating this
default) must be treated as `[]` — fail closed, never fall back to
"everything enabled".

**`last_processed_candle_by_timeframe` → `last_processed_candle_by_worker`**,
keyed by `worker_id` instead of bare timeframe. Renamed outright rather
than kept alongside, since the old key becomes meaningless the moment a
second worker shares a timeframe string.

**`worker_heartbeat.workers`**: keyed by `worker_id` instead of bare
timeframe. Same rationale.

### Migration (live production DB, not a fresh install)

Both changes above must apply automatically to the running production
settings table, which currently holds the old shapes. Both migrations run
inside `SettingsRepository.initialize_defaults()` (already called on
every process start), before any worker reads the settings, so there is
no window where a worker observes the old shape:

- **`enabled_strategies`**: if the stored value parses as a JSON *list*
  (old shape), rewrite it to `{"XAUUSD": <that list>, "GBPUSD": [],
  "EURUSD": []}` once. If it's already a dict, no-op — this must not reset
  a value the user has since edited via the admin UI.
- **`last_processed_candle_by_worker`**: on first read, if the key
  `"XAUUSD:1h"` is absent but the old `last_processed_candle_by_timeframe`
  setting has a `"1h"` entry, seed `"XAUUSD:1h"` from it once. This
  preserves gold's restart-duplicate-signal protection (the mechanism
  built for the 2026-09-08 incident — see `strategy-ledger.md`) across the
  deploy boundary. The old setting is left in place afterward, unused but
  harmless — nothing should depend on its absence.

### Error handling

- **Unmapped symbol in the data feed** now raises instead of silently
  fetching gold. `TimeframeWorker._run()`'s existing top-level
  `try/except` already catches this, logs `"❌ [{worker_id}] Worker
  failed"`, sets `is_running = False`, and the existing
  `restart_if_needed()` exponential-backoff loop retries it — correct
  behavior for a real misconfiguration (loud in logs, not silently wrong),
  no new handling required.
- **A worker's strategy throws on live data** (e.g. an untested edge case
  in `ForexSessionStrategy` against real GBPUSD data): isolated to that
  worker's thread by the existing per-worker exception boundary — a second
  timeframe already relies on this same isolation today, so gold cannot be
  taken down by a GBPUSD/EURUSD failure.
- **Missing `enabled_strategies[symbol]` key**: treated as `[]`
  (disabled), never as "everything enabled" — fail closed.

## Testing

Following the existing pattern (`test_worker_restart.py`,
`test_settings_driven_rules.py`: construct `TimeframeWorker` directly
against an in-memory sqlite DB with a mocked `shared_dedup_subscriber`, no
real network) and this project's TDD convention — write each test first,
watch it fail, then implement:

1. `WorkerSpec`-driven construction: a GBPUSD/`ForexSessionStrategy`/1h
   worker calls `create_datafeed(symbol='GBPUSD', ...)` and instantiates
   `ForexSessionStrategy`, not `GoldStrategy`/`'XAUUSD'`.
2. `worker_id` correctness: `TimeframeWorker(spec=...).worker_id ==
   "GBPUSD:1h"`.
3. **Regression test for the collision bug**: two workers, same
   timeframe, different symbols, sharing a DB — each independently calls
   `save_last_processed_candle`/`get_last_processed_candle`; assert
   neither clobbers the other. This is the test that would fail before
   the fix.
4. `enabled_strategies` migration: seed the old flat-list shape, run
   `initialize_defaults()`, assert the new dict shape; a second test
   asserts idempotency (no-op, no reset of user edits) when already
   dict-shaped.
5. `refresh_settings()` per-symbol scoping: GBPUSD's rule state responds
   only to `enabled_strategies["GBPUSD"]`, unaffected by XAUUSD's entry.
6. Missing-key fail-closed: no `"EURUSD"` key → EURUSD's rule(s) disabled.
7. `ticker_map`: GBPUSD/EURUSD map correctly; an unmapped symbol raises.
8. Tuned config loading: a config without `enabled_rules`/`expiry_hours`
   (GBPUSD/EURUSD's actual shape) loads without a `KeyError`, falls back
   to `expiry_hours=48.0`, and leaves `rules_enabled` at the strategy's
   constructor default (which `refresh_settings()` then immediately
   overrides from the DB setting, per the Design section above).
9. `worker_status.derive_worker_status` accepts `worker_id` and correctly
   distinguishes `XAUUSD:1h` vs `GBPUSD:1h` entries in one heartbeat
   payload.
10. **Gold-regression guard**: with all three `WORKER_SPECS` present,
   XAUUSD's worker resolves its existing `last_processed_candle_by_timeframe['1h']`
   data via the migration/seed-fallback, loads the same tuned config, and
   uses the same strategy class as today — the direct answer to "did we
   break gold."

API-layer tests (`packages/api`) for the `worker_id`-aware
`derive_worker_status` and the generalized `/v1/settings/strategies`
registry, scoped during plan-writing once the existing API test setup is
confirmed.

**Not testing**: live Yahoo Finance GBPUSD/EURUSD data quality (Asian-session
candle availability/gaps) — that's a post-deploy production-verification
step (curling the live API, per this project's established convention),
not a unit-test concern.

## Rollout

1. Implement per the plan (TDD, as above), verify gold's existing test
   suite is unaffected.
2. Deploy to Railway/Vercel as usual (auto-deploy on push to `main`).
3. Verify live via the production API: confirm three `worker_id` entries
   appear in `worker_heartbeat`, all `is_running`, GBPUSD/EURUSD producing
   zero signals (rule disabled), gold's signal cadence and last-processed
   candle unaffected by the deploy.
4. Report back to the user with what's now live-but-disabled. **Do not
   flip `enabled_strategies["GBPUSD"]`/`["EURUSD"]` on without the user's
   explicit go-ahead** — a separate decision from building the capability.

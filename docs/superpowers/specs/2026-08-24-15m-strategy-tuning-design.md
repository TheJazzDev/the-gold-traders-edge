# 15-Minute Strategy Tuning — Design

**Date:** 2026-08-24
**Status:** Approved for implementation planning

## Problem

The only timeframe currently validated and live is 1H (`tuned_configs/1h.json`,
sole enabled rule `order_block_retest`, ~2,061 signals/24 months in
production-equivalent volume, +0.104R expectancy). The user wants more
frequent entries than 1H allows, without chasing large moves: consistently
capturing 50-100 pips per trade is an acceptable target, which points at a
lower timeframe (15m considered first; 5m explicitly deferred as noisier and
more spread-sensitive — see decision log).

Two things stand in the way of just re-running `tune_strategy.py` with
`--data data/processed/xauusd_15m_*.csv`:

1. **Data depth.** Yahoo Finance (`fetch_real_data.py`, backed by `yfinance`)
   only returns ~60 days of history for intraday intervals under 1H. The 1H
   tuning trusted 24 months (11,442 candles) across varied market regimes —
   3 rounds of adversarial review were needed to get that result trustworthy.
   60 days is nowhere near enough coverage to trust a 15m result the same way.
2. **`tune_strategy.py` is 1H-specific.** `BASE_1H_CONFIG` is a hand-scaled
   starting point (4H-tuned lookbacks × 4, since 1H candles are 1/4 the
   duration of 4H candles) baked into the script, and the output path/schema
   assume `timeframe: '1h'` throughout.

## Decision log (from brainstorming session)

- **Data source: MetaAPI**, not Yahoo. The user already has a MetaAPI account
  configured (`METAAPI_TOKEN`/`METAAPI_ACCOUNT_ID`, currently unused live
  because `metaapi-cloud-sdk` was never added as a dependency — see the Task
  14 deployment finding). Most MT4/5 brokers retain years of intraday history
  server-side; MetaAPI's `readHistoricalCandles` REST endpoint
  (`GET .../historical-market-data/symbols/:symbol/timeframes/:timeframe/candles`,
  paginated via `startTime`/`limit`) reads directly from the broker's
  terminal, not a MetaAPI-imposed window. **Actual depth available for this
  account is unknown until queried — that's the first implementation step,
  not an assumption baked into this spec.**
- **`metaapi-cloud-sdk` stays dev-only.** It's added to fetch historical bars
  locally for tuning. It is explicitly **not** added to `packages/engine/requirements.txt`
  used by the Docker build, and the live service's `DATA_FEED_TYPE` stays
  `yahoo` — that decision (made during Task 14) is unrelated to and
  unaffected by this work.
- **Timeframe scope: 15m only**, first. 5m deferred — noisier, and spread/
  slippage (unmodeled in the backtester — a known, already-logged gap from
  the 1H work) eats a much larger share of a 50-100 pip target at 5m than at
  15m.
- **Profit-target mechanism: unchanged.** `GoldStrategy` keeps computing
  `take_profit = entry ± (risk × default_rr_ratio)` — a risk-multiple target,
  not a fixed pip amount. 50-100 pips is a target *outcome* to evaluate the
  tuned result against, not a new take-profit mode to build. If tuning
  produces a rule whose typical TP distance is far outside that range, that's
  a data point for the next decision (adjust `default_rr_ratio`'s search
  grid, accept a wider/narrower target, or reconsider), not something this
  pass tries to force.
- **Generalize `tune_strategy.py`, don't fork it.** All of the shared gating
  logic (`_production_valid_strategy_func`, `_resolved_stats`,
  `SignalValidator.meets_min_rr`, `json_safe`, `statistics.median_low`) is
  timeframe-agnostic and was hardened over 3 review rounds on 1H. Duplicating
  it into a `tune_strategy_15m.py` risks exactly the kind of drift that
  produces the class of bug already found and fixed once. The only
  timeframe-specific piece (`BASE_1H_CONFIG`) generalizes to a duration-ratio
  scaling function.
- **Same validation bar, no shortcuts.** Two independent adversarial-review
  agent passes before anything ships, same as 1H, for the same reason: this
  is headed toward real capital. All 5 rules get tried; only whatever
  survives the honest gate ships enabled.
- **Going live is a separate, later decision**, made after seeing the tuned
  15m result — not bundled into this work. The live service already loads
  `tuned_configs/<timeframe>.json` generically per entry in `TIMEFRAMES`
  (built during Task 12), so enabling 15m live later is a one-line change to
  that list plus a redeploy — no new wiring code needed.

## Non-goals

- No 5m tuning in this pass.
- No change to `GoldStrategy`'s take-profit calculation (fixed-pip mode) —
  see decision log.
- No change to the live service's data feed (`DATA_FEED_TYPE` stays `yahoo`)
  or to `packages/engine/requirements.txt` (the production dependency set).
- No auto-trading changes.
- Not fixing the previously-logged, still-open methodology gaps from the 1H
  work (gate undersamples production signal volume, `expiry_hours` not
  applied inside the scoring loop, zero transaction costs modeled) — those
  apply equally here and remain follow-up work, not blocking.

## Architecture overview

```
fetch_metaapi_history.py (NEW, dev-only)
  --timeframe 15m --symbol XAUUSD --output data/processed/xauusd_15m_<range>.csv
  └─ metaapi_cloud_sdk.MetaApi(token) → account.get_historical_candles(...)
       (paginated backward from now via startTime, until the broker returns
        no more data or a sane cap is hit)
     writes the same OHLCV CSV schema GoldDataLoader.load_from_csv() already
     reads — nothing downstream needs to know the data didn't come from Yahoo

tune_strategy.py (GENERALIZED, was 1H-only)
  --data data/processed/xauusd_15m_<range>.csv --timeframe 15m
  └─ BASE_CONFIG = scale_baseline_config(DEFAULT_CONFIG, from_tf='4h', to_tf='15m')
     (same coordinate-search / train-test-split / gating / resolved-stats
      pipeline as 1H, unchanged)
  └─ writes tuned_configs/15m.json (same schema as tuned_configs/1h.json)

[same 2-agent adversarial review process as Task 11, applied to the 15m output]

run_multi_timeframe_service.py — UNCHANGED in this pass.
  Already generically loads tuned_configs/<timeframe>.json per entry in
  TIMEFRAMES (built during Task 12). Adding '15m' to TIMEFRAMES is a
  deliberate follow-up decision after reviewing the tuned result, not part
  of this work.
```

## Component 1: MetaAPI historical data fetcher (new, dev-only)

**New file:** `packages/engine/fetch_metaapi_history.py`

**New dependency:** `metaapi-cloud-sdk`. Installed manually into the local
venv (`pip install metaapi-cloud-sdk`) for this work only — **not** added to
`packages/engine/requirements.txt` (see decision log; that file is what the
Docker build installs). `fetch_metaapi_history.py`'s docstring notes the
manual install step, matching how `MetaAPIDataFeed` in `realtime_feed.py`
already documents its own setup steps.

Process:
1. Connect via `MetaApi(METAAPI_TOKEN)`, resolve the account via
   `METAAPI_ACCOUNT_ID`, same credentials already sitting in Railway's env
   (Task 14) and usable locally via `packages/engine/.env`.
2. **Discovery step (run first, report results before proceeding):** query
   the earliest available 15m candle for XAUUSD on this account/broker by
   paging `readHistoricalCandles` backward from now until the API returns an
   empty page or a request fails. Report the actual depth (calendar days,
   candle count) — this determines the real train/test split, replacing any
   assumption. If depth turns out comparable to Yahoo's ~60 days (i.e., the
   broker itself doesn't retain more), stop and report back rather than
   proceeding to a tuning run that can't be trusted — same principle as
   Task 11 Step 4's "don't ship an empty/untrustworthy result silently."
3. Fetch the full available range in `limit`-sized pages (MetaAPI's REST call
   can take up to its documented ~4 minute timeout per page for a busy
   terminal — page conservatively, don't assume single-request retrieval).
4. Deduplicate/sort by timestamp, validate OHLC invariants (`high >= max(open,close)`,
   `low <= min(open,close)`, matching `GoldDataLoader`'s existing validation
   used for the Yahoo path), and write to
   `data/processed/xauusd_15m_<start>_<end>.csv` with the same column schema
   the 1H CSV uses (`GoldDataLoader.load_from_csv()` must read it with zero
   changes).

## Component 2: Generalize `tune_strategy.py`

**Modify:** `packages/engine/tune_strategy.py`

- Add `--timeframe` (required) and generalize `--output` to default to
  `tuned_configs/<timeframe>.json`.
- Replace the hardcoded `BASE_1H_CONFIG` dict with a
  `scale_baseline_config(base_config, from_minutes, to_minutes)` function:
  scales the candle-count params (`swing_lookback`, `trend_lookback`,
  `atr_period`) by `from_minutes / to_minutes` (e.g. 4H→15m is a 16x
  candle-count scale, matching the same "same real-time window, more
  candles" logic already used for the 1H 4x scale) and leaves
  ratio/percentage params (`fib_tolerance`, `default_rr_ratio`,
  `strong_momentum_threshold`, `sl_buffer_atr`, RSI/EMA settings) unscaled,
  exactly matching the existing 1H comment's stated rationale. Unit-tested
  directly: given the known 1H scale factor (4x) and known `BASE_1H_CONFIG`
  values, `scale_baseline_config(DEFAULT_CONFIG, 240, 60)` must reproduce
  `BASE_1H_CONFIG` exactly — this is a regression check that generalizing
  the function didn't change the already-validated 1H behavior.
- `SEARCH_GRID` values scale with the same ratio for the candle-count
  params; ratio params keep their existing grid values (tuning found no
  evidence the RR/tolerance grid needs to be timeframe-dependent).
- Everything else — `_production_valid_strategy_func`, `_resolved_stats`,
  `passes_pf_gate`, `MIN_TRAIN_TRADES`/`MIN_TEST_TRADES`, the median-low
  shared-config construction, `json_safe` — is already timeframe-agnostic
  and changes only insofar as `'timeframe': '1h'` in the output dict becomes
  the passed-in value.
- **Regression check before trusting any 15m output:** re-run
  `tune_strategy.py --data data/processed/xauusd_1h_2024_2026.csv --timeframe 1h`
  after the refactor and diff against the currently-committed
  `tuned_configs/1h.json` (ignoring `generated_at`) — must still match
  exactly. Generalizing the script must not silently change the already-
  shipped, already-reviewed 1H result.

## Component 3: Validation process

Identical structure to Task 11:
1. Dispatch an agent to run the (generalized, regression-checked)
   `tune_strategy.py --timeframe 15m` against the MetaAPI-sourced CSV and
   report the full output plus its own overfitting-risk assessment (same
   four checks: leakage-free split, trade-count gates enforced, shared-config
   re-validation catching any individually-good-but-collectively-bad rule,
   anything statistically suspicious).
2. Dispatch a second, independent agent to adversarially re-derive the
   result from scratch and check for the same bug classes already found once
   on 1H (force-close artifacts inflating a rule's PF, RR-boundary float
   issues, a rule structurally producing negative-risk trades) — these are
   now fixed at the shared-code level, so the second agent's job is
   confirming they don't recur, not rediscovering them blind.
3. Do not proceed to writing `tuned_configs/15m.json` as a trusted artifact
   until both agents agree, exactly as Task 11 required. If either flags a
   real problem, fix and re-run both, same as the 1H work needed 3 rounds
   for.
4. Report the tuned result back with the same framing used for `order_block_retest`:
   which rule(s) survived, their PF/trade-count across train/individual-test/
   shared-config, and — specifically requested by the user — the resulting
   typical TP distance in pips for whatever ships, so it's clear whether the
   50-100 pip target actually materialized or not.

## Testing

- **`scale_baseline_config`**: unit tests — the 1H-reproduction regression
  check above, plus a synthetic case confirming ratio params pass through
  unscaled while candle-count params scale by the expected factor.
- **`fetch_metaapi_history.py`**: unit tests against a mocked MetaAPI client
  (no real network calls in the test suite) covering pagination, dedup/sort,
  and OHLC validation rejecting a malformed candle. The discovery step and
  actual fetch are integration-level, run once manually as part of this
  work, not part of `pytest`.
- **`tune_strategy.py`** generalization: existing unit tests
  (`test_tune_strategy.py`) continue to pass unchanged (they test
  timeframe-agnostic helpers); add a test for the new `--timeframe`/output-path
  wiring.

## Open risk accepted for this pass

Actual MetaAPI history depth for this specific account/broker is unknown
until queried. If it turns out to be shallow (comparable to or worse than
Yahoo's ~60 days), this whole approach needs to be revisited — that
possibility is explicitly not hidden by this spec, it's the first thing
implementation checks and reports on before any tuning work begins.

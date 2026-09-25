# Gold Strategy Ledger

Persistent record of every trading hypothesis tried for XAUUSD, so a future
"has this been tested?" question has a real, honest answer instead of
needing to be re-derived or re-tested blind. Updated as strategies are
tried — nothing gets removed from *this document*, only appended to.

**Format per entry:** hypothesis, source, what was tested, result, verdict.

**2026-09-08:** every ruled-out rule below (5 legacy + 3 new hypotheses)
was deleted from `GoldStrategy` itself, along with any helper/dataclass
only they used — see commit `ba6fba7`. `gold_strategy.py` now implements
only `order_block_retest`. This document is the only remaining record of
what each deleted rule did and why it failed — that's the point of it.

**2026-09-09:** scope widened beyond gold. Order Block Retest doesn't
transfer to other instruments (see "Tried and ruled out — other
instruments" below), so rather than keep porting a gold-native strategy
elsewhere, work moved to hypotheses native to other instruments — see
"Other instruments" below.

---

## Other instruments

### GBPUSD / EURUSD: Asian Range London Breakout — validated, live but disabled
- **Source:** new hypothesis (2026-09-09), see
  `docs/superpowers/specs/2026-09-09-gbpusd-asian-range-breakout-design.md`.
- **Hypothesis:** GBP liquidity concentrates in the London session — price
  consolidates during the quiet Asian session (00:00-07:00 UTC) and breaks
  out at London open (07:00 UTC). A real, causally-grounded forex pattern,
  structurally distinct from every gold rule (session regime-change, not
  zone-retest/fib-level).
- **Validated via real 70/30 train/test split, no parameter sweep**
  (deliberately — see the methodology note below): GBPUSD test PF 1.58
  (47 trades), EURUSD test PF 1.18 (50 trades), both robust across 5
  parameter variations (GBPUSD 1.25-1.76, EURUSD 1.02-1.64 — not a
  knife-edge result). EURUSD weaker than GBPUSD, consistent with GBP being
  more concentrated in the London session — the result is shaped the way
  the mechanism predicts, not noise.
- **Implemented** as a new `ForexSessionStrategy` class (not a
  `GoldStrategy` rule — a genuinely different instrument gets its own
  module), with full test coverage. Formal validation via
  `tune_forex_session_strategy.py` confirms: GBPUSD ENABLED, EURUSD
  ENABLED (`tuned_configs/gbpusd_1h.json`, `tuned_configs/eurusd_1h.json`).
- **Verdict:** ✅ Validated on both pairs. **Wired into the live
  multi-timeframe service as of 2026-09-09** (see
  docs/superpowers/specs/2026-09-09-gbpusd-eurusd-worker-wiring-design.md)
  — both workers run live in production (real data feed, heartbeat,
  restart-protection) with their rule disabled (`enabled_forex_symbols`
  empty by default). **Actually enabling either symbol's signals is a
  separate, later decision** requiring the user's explicit go-ahead, same
  convention as every GoldStrategy rule.

---

## Operational incidents (not strategy hypotheses, but recorded here for the same reason)

### 2026-09-08: worker restart re-signaled on an already-processed candle

Three near-identical Order Block Retest signals fired for what should have
been one setup: `OBR-0908-01` (16:00 candle, legitimate — the same bearish
order block zone was independently retested 2 hours apart, which the
strategy has no memory to suppress by design) and `OBR-0908-02`/`03`/`04`
(all nominally the "18:00" candle, ~3-20 min apart).

**Root cause:** a deploy restarts the worker process. `RealtimeSignalGenerator.start()`'s
loop evaluates the current candle *immediately* on entry, before any
candle-close wait, and had no memory across restarts of which candle it
last processed. Since Yahoo Finance's 1H gold bar isn't guaranteed
finalized the moment it's fetched (own docstring: "~15-20 minute delay...
not true real-time"), each restart re-fetched the still-forming "18:00"
bar with a slightly different close price, producing near-duplicate but
not identical entry/SL/TP. `SignalDeduplicator`'s dedup hashes on exact
(cent-rounded) entry/SL/TP, so it never caught this — it was designed for
identical-price duplicates, not "same setup, price drifted because the
candle wasn't really closed."

**Compounding factor:** two follow-up deploys (fixing this bug, then
adding a DELETE endpoint to clean up the duplicates) landed before the fix
had a chance to record its first baseline, causing one more duplicate
(`OBR-0908-04`) via the exact same mechanism the fix was meant to close.

**Fix (commit `cf404d8`):** `RealtimeSignalGenerator.run_once()` now takes
`last_processed_candle_getter`/`setter`; `TimeframeWorker` persists the
last-processed candle timestamp per timeframe in the settings table
(`last_processed_candle_by_timeframe`), so a restart — however soon after
the previous evaluation — always skips a candle it already processed.
Verified live: the setting correctly advanced past 18:00 to 20:00 with no
further duplicates once the fix was deployed.

**Cleanup:** signals `OBR-0908-02`, `03`, `04` were deleted (via new
`DELETE /v1/signals/{id}`, commit `ff2e22c`) as genuine duplicates, at the
user's request. `OBR-0908-01` was kept — it's a real, independent
detection.

---

## 2026-09-25: live-parity gates after the 7-stop-loss week (B1-B5)

**Trigger:** 7 of 9 resolved signals stopped out between 2026-09-23 and 09-25
(see `docs/superpowers/2026-09-25-weekly-signal-review.md`). 6 of the 7 were
*stacked* signals, published while another same-symbol signal was still open.
They weren't counter-trend: every losing gold short was with the daily and 4H
trend.

**Method:** `packages/engine/scripts/validate_signal_gates.py`. It uses a
chronological 70/30 split. Gold data: `xauusd_1h_2024_2026.csv`, test from
2026-01-16. Forex data: `*_1h_2023_2026.csv`, test from 2025-11-05. Configs are
fixed (gold: committed `tuned_configs/1h.json`; forex: committed defaults), so
nothing is swept. The variants and the pass rule were chosen before any results
were seen. The pass rule for B3/B4: test PF improves *and* ≥ ~50 test trades.

- "Live gates" means R:R ≥ 1.5, confidence ≥ 0.60 and one open trade.
- The test slice is scored with the preceding candles as warm-up history, but no
  trade opens before the slice starts.
- The "legacy" row reproduces the old tuner exactly (gold 114 trades / PF 1.16;
  EURUSD 50 / 1.18; GBPUSD 47 / 1.58), which checks the harness.

### XAUUSD — Order Block Retest

| Variant | Test PF | Test trades | Test WR | Test net % | Test max losing streak | Train PF (trades) |
|---|---|---|---|---|---|---|
| Legacy tuner method (no confidence gate) | 1.16 | 114 | 37.7% | +28.7% | 8 | 1.03 (319) |
| **Before**: what live ran (live gates, no cooldown) | 1.48 | 140 | 43.6% | +121.8% | 8 | 1.00 (270) |
| **B1 + B2** (re-entry cooldown 20) — shipped | **1.57** | **83** | 44.6% | +68.5% | **6** | 1.17 (164) |
| B1 + B2, `detect_trend` taken literally as lookback=30 | 1.37 | 81 | 42.0% | +46.8% | 7 | 1.07 (126) |
| **B1 + B2 + B3** (1H EMA200 trend gate) | 1.33 | 59 | 40.7% | +26.4% | 9 | 1.22 (100) |
| B1 + B2 + B3, with the literal lookback=30 | 1.17 | 53 | 37.7% | +12.5% | 9 | 1.09 (75) |

(B1, one open trade per symbol, isn't a separate row: every backtest has always
run with `max_open_trades=1`. B1 makes live match that.)

- **B1 — ✅ shipped.** It's a parity fix and can't be measured separately in a
  backtest. On this week's real signals it would have turned −2.0R into 0.0R on
  gold (simulated counterfactual in the weekly review).
- **B2 — ✅ PASS, shipped on by default** (`reentry_cooldown_candles=20`). PF
  improves on *both* slices (train 1.00 → 1.17, test 1.48 → 1.57) and the max
  losing streak drops from 8 to 6. The costs: trade count falls 41% (140 → 83),
  and so does test net % (+121.8% → +68.5%), because the strategy stands aside in
  choppy ranges. That's a risk-for-return trade-off, not a free improvement.
  Definition: a zone stops out when a later candle trades through the stop OBR
  would use (edge ± 0.3 × ATR). Any overlapping same-type zone is then skipped
  for 20 candles after the *latest* stop-out.
- **`detect_trend` lookback bug — API fixed, OBR behaviour kept.**
  `detect_trend(lookback=N)` now only looks at the last N candles. Taking OBR's
  `lookback=30` literally **failed** (test PF 1.57 → 1.37, train 1.17 → 1.07), so
  OBR now passes its whole frame. That reproduces the validated behaviour exactly
  (the `b1_b2_shipped` variant is identical to `b1_b2`).
- **B3 — ❌ FAIL, not enabled** (`htf_trend_filter=False`). Test PF falls from
  1.57 to 1.33 on 59 trades. It *improved* train (1.17 → 1.22), which is the
  classic sign of a filter that doesn't generalise. It also wasn't the mechanism
  this week: the losing shorts were all with the trend.

### EURUSD / GBPUSD — Asian Range London Breakout

| Variant | Symbol | Test PF | Test trades | Test WR | Test net % | Test max losing streak | Train PF (trades) |
|---|---|---|---|---|---|---|---|
| Before (live gates) | EURUSD | 1.18 | 50 | 38.0% | +12.6% | 7 | 1.29 (121) |
| **+ B4** (1H EMA200 trend gate) | EURUSD | 1.98 | **27** | 51.9% | +33.2% | 3 | 1.49 (62) |
| Before (live gates) | GBPUSD | 1.58 | 47 | 44.7% | +34.8% | 4 | 1.10 (128) |
| **+ B4** | GBPUSD | 2.43 | **29** | 55.2% | +44.0% | 4 | 1.23 (73) |

(Live gates change nothing for ARLB: confidence is always 0.60, and the "before"
rows equal the legacy tuner rows.)

- **B4 — ❌ FAIL on sample size, not enabled.** PF improves on both pairs and
  both slices, which is encouraging. But the test counts, 27 and 29, are far below
  the ~50-trade bar, and at that size PF 2.0 vs 1.2 is within noise. Revisit once
  about 1 more year of data doubles the test slice. Don't enable it on this
  evidence.

### B5 — tuner parity

`backtesting/live_parity.py` is now used by both tuners: the confidence gate,
one open trade, the test slice with warm-up history, and the max losing streak.
One consequence: **the 37.7% win rate / PF 1.16 quoted for OBR since August was
measured on a different trade population from the live one.** The live-equivalent
figures are 43.6% / PF 1.48 before the fixes, and 44.6% / PF 1.57 after B1+B2.
`tuned_configs/1h.json` has **not** been regenerated. Its shared config is
unchanged, and it still reports the old numbers. Re-run `tune_strategy.py
--data ... --timeframe 1h` to refresh them.

---

## Validated, live

### Order Block Retest
- **Source:** original 5-rule set (`packages/engine/src/signals/gold_strategy.py`).
- **Hypothesis:** institutional entry zones (order blocks) get retested;
  price reacts at them.
- **Result:** PF 1.16, 114 trades, +28.7% net, on the live 1H shared config
  test slice (`tuned_configs/1h.json`). Confirmed live: first real signal
  (2026-09-04) hit TP for +2.0R.
- **Verdict:** ✅ The only currently validated, live-enabled edge.
- **2026-09-25:** re-measured with live's gates. The live-equivalent test
  slice is PF 1.48 / 140 trades / 43.6% win rate, and PF 1.57 / 83 trades /
  44.6% with the new re-entry cooldown. The HTF trend gate failed (PF 1.33). See
  the 2026-09-25 entry above.

---

## Tried and ruled out — same instrument (gold), other rules

### Momentum Equilibrium, London Session Breakout, Golden Fibonacci, ATH Retest
- **Source:** original 5-rule set.
- **Result:** all score PF < 1.0 on the live 1H shared-config test slice
  (0.89 / 0.97 / 0.97 / not consistently a shared-config candidate),
  despite decent-looking isolated-tuning numbers.
- **Verdict:** ❌ Not real edge under shared-config conditions. Still
  enabled in production settings (user's deliberate choice, not a bug) but
  known to not be pulling weight.

---

## Tried and ruled out — other instruments (same strategy set)

### Order Block Retest on Silver (XAGUSD)
- **Tested:** 2026-09-08. Train PF 1.05 (296 trades) → Test PF 1.03 (124
  trades). Consistent, not overfit, but barely above breakeven.
- **Verdict:** ❌ Edge doesn't transfer to silver.

### Order Block Retest on BTC-USD
- **Tested:** 2026-09-08. Train PF 1.14 (390 trades, inflated by BTC's bull
  run) → Test PF 0.975 (132 trades), **net -4.4%**. Momentum Equilibrium
  looked strong (PF 2.0, 24 trades) but is the same rule that showed zero
  edge on gold and inconsistent results on silver — small-sample noise, not
  trusted.
- **Verdict:** ❌ Loses money out of sample.

### Order Block Retest on GBPUSD
- **Tested:** 2026-09-08. `enabled_rules: []` — not one of the 5 strategies
  passed even the training-slice bar. Order Block Retest: train PF 1.04
  (332 trades) → test PF 0.99, net -4.2%.
- **Verdict:** ❌ Cleanest "no" of the three — nothing survives.

**Conclusion from all three:** the edge is gold-specific, not a portable
"order block" property. Confirmed by the user's own domain knowledge: the
strategy was intentionally built around gold's behavior, not discovered as
a generic pattern. Cross-instrument expansion is not the lever to pull for
more signal volume — see "New strategies, gold-only" below instead.

---

## New strategies, gold-only (this round)

### Volatility Squeeze Breakout
- **Source:** new hypothesis (2026-09-08), see
  `docs/superpowers/specs/2026-09-08-volatility-squeeze-breakout-design.md`.
- **Hypothesis:** gold chops in a tight range through low-news periods,
  then expands sharply on real catalysts (Fed decisions, real-yield moves,
  USD strength shifts, geopolitical shocks) — a volatility *regime change*,
  mechanically distinct from every existing rule (all of which trade a
  *zone*, not a regime shift).
- **Tested (default tuner grid):** train slice only 4 trades over ~2 years
  of 1H gold data (need 15 minimum) — too rare to evaluate at the tuned
  baseline (squeeze_lookback=80 candles ≈ 3.3 days). The default
  coordinate-search tuner (one param at a time from baseline) never found
  a better region because it needs `squeeze_lookback` AND
  `squeeze_atr_ratio` to move together — a known limitation of one-pass
  coordinate search.
- **Exhaustive sweep (2026-09-08, 48 combos, full dataset):** found a
  promising-looking region — `squeeze_lookback=20, squeeze_atr_ratio=0.9,
  breakout_buffer_atr=0.3` → PF=2.35, 27 trades.
- **Real train/test validation of that region:** train PF 3.08-4.14 (13-27
  trades) → **test PF collapses to 0.40-1.28 (only 6-10 trades)**. The
  full-dataset "PF=2.35" was itself an artifact of searching 48
  combinations and reporting the best one (pure post-hoc selection bias) —
  exposed the moment a real held-out test set was used.
- **Verdict:** ❌ Ruled out. Fires too rarely to have real, non-overfit
  edge on gold 1H — every parameterization that fires often enough loses
  its apparent edge out of sample.

### Fibonacci Golden Zone Confluence
- **Source:** the user's own real XAU/USD trading plan (61.8% entry, ONLY
  if it aligns with an Order Block, follows a liquidity grab, and confirms
  a retest of broken structure; SL beyond 78.6%, TP at 38.2%, minimum 1:2
  R:R) — not a generic invented pattern.
- **New building block added:** `_detect_liquidity_grab` (stop-hunt
  detection: price wicks beyond a recent swing low/high then closes back
  inside) — didn't exist in the codebase before, kept as shared
  infrastructure for future strategies.
- **Diagnostic finding:** on real gold 1H data (11,442 candles), each
  individual condition is common alone (`near_618` ~55%, `order block`
  ~61%) but requiring liquidity grab AND structure retest on the *exact
  same candle* as the 61.8% touch collapsed to 17 candles (~0.15%), with
  **zero** direction-matched cases — literally 0 trades even with the R:R
  filter relaxed to 1.2.
- **Also found:** standard Fibonacci level spacing gives a raw
  38.2%→61.8% vs 61.8%→78.6% reward:risk around **1.4**, inherently below
  the plan's own stated 1:2 minimum — a real internal tension in the plan's
  literal mechanics worth knowing about independent of backtest results.
- **Relaxation tried:** liquidity grab / structure retest allowed within a
  `confluence_window` instead of requiring the exact same bar (matching how
  a discretionary trader actually reads "confluence" — things lining up
  nearby, not identically). Window=11 found 15 trades on the full dataset
  with PF=1.39 — but on a real train/test split: train PF 2.15-2.99 (4-12
  trades) → **test PF 0.56-0.81 (11-15 trades), unprofitable**. Same
  overfitting pattern as the squeeze breakout.
- **Verdict:** ❌ Ruled out. The confluence stack is either too rare
  (strict) or unprofitable once loose enough to evaluate (relaxed) — no
  parameterization tested holds up out of sample. The plan's underlying
  logic may still work for *discretionary* trading (a human reading context
  the mechanical proxies here can't capture), but it does not translate
  into a profitable systematic 1H rule as implemented.

---

### Shallow Pullback Continuation
- **Source:** the user's own trading plan hard fact #3: "In strong bullish
  moves, price may only pull back to the 23.6% level before continuing" —
  trend CONTINUATION off a shallow pullback, mechanically distinct from
  every other rule tried this session (all reversal/zone-retest concepts;
  this is the only continuation hypothesis).
- **Method:** confirmed trend (`detect_trend`) in the fib zone's direction,
  price touched 23.6% within a `pullback_window` (default 10 candles) but
  never traded through the deeper 38.2% level in that window (still
  "shallow"), then entry on a structure-break (BOS/CHoCH) confirmation
  candle.
- **Tested directly on a real train/test split** (skipped the full-dataset
  sweep step this time — the previous two strategies' sweep-then-overfit
  pattern made clear that manual sweeping before a real test-set check adds
  overfitting risk, not signal): train PF 1.456 (only 7 trades) → **test PF
  0.485 (5 trades)**. Thin sample on both sides, unprofitable out of
  sample.
- **Verdict:** ❌ Ruled out. Also confirms the shallow-pullback-236 event is
  itself fairly rare at 1H on gold, before even considering the structure
  confirmation on top of it.

---

## Session methodology note

The squeeze breakout and fib confluence attempts both went through a
"sweep many parameter combos on the full dataset, pick the best-looking
one" step before real train/test validation — and both looked strong on
the full-dataset sweep (PF 2.35, PF 1.39) then collapsed on a genuine
held-out test set. That pattern is itself informative: **a full-dataset
parameter sweep followed by cherry-picking the winner is a multiple-
comparisons trap** — searching 48+ combinations makes finding one that
looks good by chance alone the *expected* outcome, not evidence of real
edge. Shallow Pullback Continuation skipped that step (straight to a real
train/test split) and reached the same ruled-out conclusion faster and
more honestly. Future strategy attempts should default to real train/test
validation from the start, not a full-dataset sweep-then-validate.

## Open questions / not yet tried

- Other "hard facts" from the user's trading plan not yet built:
  consolidation-then-ATH-breakout-retest (partially overlaps existing
  `ath_retest`, which already scores PF < 1.0 on gold — low priority); 50%
  rule in strong momentum (already IS what `momentum_equilibrium` tests —
  already ruled out, PF 0.89 on gold).
- Web research (2026-09-08) mostly surfaced already-implemented concepts
  (liquidity sweeps, market structure) from low-credibility marketing
  content, not novel testable ideas — Point of Control / volume-profile
  "magnet" effect is one real candidate not yet tried (needs reliable
  volume data; yfinance's GC=F volume field would need verification first).
- All 3 new strategies this session were tested only on 1H. None were
  tried on 15m (the other timeframe with any existing tuning
  infrastructure) — untested, not ruled out, for that timeframe.

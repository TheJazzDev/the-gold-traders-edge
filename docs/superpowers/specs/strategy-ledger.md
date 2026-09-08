# Gold Strategy Ledger

Persistent record of every trading hypothesis tried for XAUUSD, so a future
"has this been tested?" question has a real, honest answer instead of
needing to be re-derived or re-tested blind. Updated as strategies are
tried — nothing gets removed, only appended to.

**Format per entry:** hypothesis, source, what was tested, result, verdict.

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

## Open questions / not yet tried

- Other "hard facts" from the user's trading plan not yet built:
  23.6% shallow pullback continuation in strong trend; consolidation-then-
  ATH-breakout-retest (partially overlaps existing `ath_retest`); 50% rule
  in strong momentum (already IS what `momentum_equilibrium` tests —
  already ruled out, PF 0.89 on gold).
- Web research (2026-09-08) mostly surfaced already-implemented concepts
  (liquidity sweeps, market structure) from low-credibility marketing
  content, not novel testable ideas — Point of Control / volume-profile
  "magnet" effect is one real candidate not yet tried (needs reliable
  volume data; yfinance's GC=F volume field would need verification first).

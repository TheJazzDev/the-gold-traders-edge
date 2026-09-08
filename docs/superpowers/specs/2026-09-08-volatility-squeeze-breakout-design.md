# Volatility Squeeze Breakout — Design

**Date:** 2026-09-08
**Status:** Approved for implementation

## Problem

`order_block_retest` is the only one of the 5 existing `GoldStrategy` rules
with a real, validated edge on gold's live 1H shared config (PF 1.16, 114
trades, +28.7% net — see `tuned_configs/1h.json`'s
`final_shared_config_validation`). The other 4 (`momentum_equilibrium`,
`london_session_breakout`, `golden_fibonacci`, `ath_retest`) score PF < 1.0
under the same shared config despite looking good in isolated tuning.

Cross-instrument expansion (silver, BTC, GBPUSD — same session, same
methodology) was tried as a way to get more signal volume and confirmed the
edge doesn't transfer: `order_block_retest` degraded to breakeven-or-worse
out-of-sample on all three (silver PF 1.03, BTC PF 0.975, GBPUSD PF 0.99).
The system's entire live viability currently rests on one strategy, on one
instrument.

This spec adds a 6th rule to `GoldStrategy`, on gold, structurally different
from the existing 5 — all of which trade a *zone* (a Fibonacci level, an
order block, a prior high/low) plus a reversal-pattern confirmation. The new
rule instead trades a volatility *regime change*: gold characteristically
chops in a tight range through low-news periods, then expands sharply on
real catalysts (Fed decisions, real-yield moves, USD strength shifts,
geopolitical shocks). `london_session_breakout` tried to time volatility
expansion by *clock* (a fixed session window) and failed (PF 0.97) — this
times it by *measured volatility contraction* instead, which shouldn't
depend on which hour the catalyst actually lands in.

## Decision log

- **Reuses existing machinery, adds no new indicator infrastructure.** ATR
  (`self.ta.calculate_atr`), trend detection (`self.ta.detect_trend`), and
  reversal-pattern detection (`self._detect_reversal_pattern`) already exist
  and are shared by the other 5 rules — this rule is built the same way they
  are: a new `_volatility_squeeze_breakout` method following the exact shape
  of `_order_block_retest`/`_golden_fibonacci`.
- **3 new tunable parameters**, added to `GoldStrategy.DEFAULT_CONFIG` and
  wired into `tune_strategy.py`'s `TUNABLE_PARAMS` (and `squeeze_lookback`
  into `CANDLE_COUNT_PARAMS`, since it's a "how many candles" param like
  `trend_lookback`) so the existing coordinate-search tuner searches them —
  no new tooling, no fork of `tune_strategy.py`.
- **Stop loss is structural, not an arbitrary ATR distance from entry** —
  same philosophy as every other rule (SL sits at the far side of the
  consolidation range that was actually broken, buffered by ATR).
- **Take profit stays risk-multiple based** (`entry ± risk × default_rr_ratio`),
  reusing the existing shared parameter — no new TP mechanism.
- **Validation bar is identical to every existing rule**: it only ships
  enabled if it survives `tune_strategy.py`'s train/test split and, critically,
  the *shared-config* re-validation (a rule only counts if it's still
  profitable when combined with whatever else is enabled, not just on its
  own individually-tuned config) — the same gate that correctly excluded
  `momentum_equilibrium`/`golden_fibonacci`/`ath_retest` from the live 1H
  config despite decent isolated numbers.
- **Exact numeric defaults are starting points for the tuner, not committed
  decisions** — consistent with how every other rule's real parameters were
  found (grid search over a starting point), not hand-picked.

## Non-goals

- No changes to the other 5 existing rules.
- No change to the live worker's timeframe/instrument scope (still 1H
  XAUUSD only) — this adds a rule candidate, it does not itself decide to go
  live. Going live (adding to `enabled_strategies` in production) is a
  separate decision made after seeing the tuned/validated result, same as
  every other rule.
- No new data source — reuses the existing `data/processed/xauusd_1h_2024_2026.csv`
  (free Yahoo Finance data, already fetched for the existing 1H tuning).
- No auto-trading changes.

## Rule logic

New method `GoldStrategy._volatility_squeeze_breakout(df, idx) -> RuleResult`:

1. **Squeeze condition**: current ATR (`atr_period`) is below
   `squeeze_atr_ratio` (starting point: 0.7) of its own rolling mean over
   `squeeze_lookback` candles (starting point: 20) — volatility has
   genuinely contracted, not just one quiet candle.
2. **Consolidation range**: the high/low band price has been confined to
   over that same `squeeze_lookback` window.
3. **Breakout trigger**: the current candle's close is outside that range by
   more than `breakout_buffer_atr` × ATR (starting point: 0.2) — filters out
   marginal pokes that aren't a real break, same buffer pattern already used
   for `sl_buffer_atr`.
4. **Fakeout veto**: skip (as with every other rule) if
   `_detect_reversal_pattern` flags a pattern opposing the breakout
   direction at this candle.
5. **Direction**: LONG on a close above the range high, SHORT on a close
   below the range low.
6. **Entry**: current candle's close (matches every other rule).
7. **Stop loss**: the opposite side of the consolidation range, buffered by
   `sl_buffer_atr` × ATR (the existing shared parameter) — e.g. LONG: `SL =
   range_low - atr * sl_buffer_atr`.
8. **Take profit**: `entry ± risk * default_rr_ratio` (existing shared
   parameter, same as all 5 other rules).
9. **Confidence**: base 0.5, +0.15 if breakout direction agrees with
   `self.ta.detect_trend(lookback=30)` (same check `_order_block_retest`
   uses), +0.1 scaled by how tight the squeeze was relative to
   `squeeze_atr_ratio` (tighter compression → more confidence it's a real
   regime change, not noise), capped at 1.0 — same shape as every other
   rule's confidence scoring.

New `DEFAULT_CONFIG` entries: `squeeze_lookback: 20`, `squeeze_atr_ratio:
0.7`, `breakout_buffer_atr: 0.2`. New rule key: `volatility_squeeze_breakout`,
added to `PROFITABLE_RULES` list and `rules_enabled` dict alongside the
other 5, disabled by default until validated (matches how a brand-new,
unvalidated rule should start).

## Testing

- **Unit tests** (`tests/test_strategy.py` or a new
  `tests/test_volatility_squeeze_breakout.py`, following existing test
  conventions in that file): synthetic OHLCV fixtures constructing (a) a
  clear tight-range squeeze followed by a decisive upward breakout →
  expects a LONG signal with SL at the range low and TP at the RR-scaled
  distance; (b) the mirror case for SHORT; (c) a squeeze with no breakout
  (price stays inside the range) → expects no signal; (d) ATR not actually
  contracted (no real squeeze) even though price looks range-bound → expects
  no signal, to prove the ATR-ratio check is load-bearing and not just the
  range check; (e) a breakout candle immediately followed by an opposing
  reversal pattern → expects the fakeout veto to suppress the signal.
- **Backtest/tuning validation**: run
  `tune_strategy.py --data data/processed/xauusd_1h_2024_2026.csv --timeframe 1h --output <scratch path>`
  with the new rule included — **not** overwriting the live
  `tuned_configs/1h.json` until/unless the result is reviewed and a
  decision is made to ship it. Report the full train/individual-test/
  shared-config numbers, exactly the same framing already used for
  `order_block_retest` and for the silver/BTC/GBPUSD attempts — including
  if it fails to validate. A clean "no" is a legitimate, useful outcome here
  (as three cross-instrument attempts already were).

## Open risk accepted for this pass

Same in-sample/out-of-sample split as every other rule in this codebase; no
change to the tuning methodology's known open gaps (documented in the
2026-08-24 15m spec) — those apply equally here and aren't reintroduced or
fixed by this work.

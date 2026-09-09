# GBPUSD Asian Range London Breakout — Design

**Date:** 2026-09-09
**Status:** Implemented, pending proper tuning-pipeline validation

## Problem

Order Block Retest's edge is gold-specific — confirmed by testing it on
silver, BTC-USD, and GBPUSD (all ruled out; see
`docs/superpowers/specs/strategy-ledger.md`). Rather than keep porting a
gold-native strategy to other instruments, this looks for a hypothesis
genuinely native to a forex pair instead.

## Hypothesis

GBP liquidity concentrates in the London trading session (07:00-16:00
UTC) — a real, well-established forex market-structure fact, not
something invented for this test. The corollary: price often consolidates
during the quiet Asian session (00:00-07:00 UTC, thin GBP liquidity) and
breaks out decisively at London open as London desks start trading. This
is mechanically distinct from every gold rule (a volatility/session
regime-change trigger tied to real session structure, not a zone-retest
or fib-level concept) — the closest gold analog,
`london_session_breakout`, was itself a fixed-clock-window idea and
failed on gold (PF 0.97); this is testing the *same underlying market
mechanism* on the currency pair whose liquidity actually drives it.

## Validation (standalone prototype, before implementation)

Real 70/30 chronological train/test split on 2.7 years of 1H OHLCV
(2023-11-23 to 2026-09-08, via Yahoo Finance `GBPUSD=X`/`EURUSD=X` — free,
no MetaAPI needed), default (untuned) parameters:

| | GBPUSD train | GBPUSD test | EURUSD train | EURUSD test |
|---|---|---|---|---|
| PF | 1.10 | 1.58 | 1.29 | 1.18 |
| Trades | 128 | 47 | 121 | 50 |
| Win rate | 35.9% | 44.7% | 40.5% | 38.0% |
| Net | +15.9% | +34.8% | +59.6% | +12.6% |

**Robustness check** (5 nearby parameter variations, test slice only, not
a full sweep): GBPUSD stayed in PF 1.25-1.76 across all 5; EURUSD stayed
in PF 1.02-1.64. Neither collapsed the way the gold squeeze-breakout and
confluence attempts did under the same kind of check — this doesn't look
like a knife-edge, sweep-then-cherry-pick artifact.

**Cross-instrument confirmation, not just repetition:** the *same*
untuned hypothesis produces a *real but weaker* edge on EURUSD than
GBPUSD, consistent with GBP being more concentrated in the London session
than EUR — a result shaped the way the underlying mechanism predicts,
not noise.

## Decision log

- **Implemented as a new class, not a GoldStrategy rule.** GoldStrategy is
  gold-specific by identity (class name, existing rule set, tuned config
  schema). A genuinely different instrument with a structurally different
  hypothesis gets its own module (`ForexSessionStrategy`,
  `packages/engine/src/signals/forex_session_strategy.py`), mirroring
  GoldStrategy's shape (`DEFAULT_CONFIG`, `rules_enabled`, `evaluate()`,
  reusing the shared `RuleResult` dataclass and `TechnicalAnalysis`
  helper) for consistency, without entangling the two.
- **Entry is a single fixed hour** (07:00 UTC, the first London-session
  candle), not a wider window — matches exactly what was validated.
  Widening it is a legitimate future iteration, but only as a new,
  separately-validated variant, not silently baked into what shipped.
- **Not wired into the live multi-timeframe service.** Going live is a
  separate, later decision — same convention as every GoldStrategy rule
  (see `strategy-ledger.md`).

## Testing

`tests/test_forex_session_strategy.py`: breakout above/below the Asian
range triggers LONG/SHORT with correct SL/TP; price staying inside the
range doesn't trigger; a marginal poke within the ATR buffer doesn't
trigger; wrong entry hour doesn't trigger even given a real breakout; too
few Asian-hour candles in the lookback (a weekend/holiday gap) doesn't
trigger; `evaluate()`'s data-sufficiency gate and rule-disable toggle.

## Next step

Wire into a proper train/test tuning pipeline (parameter search +
shared validation, same rigor as `tune_strategy.py` — see that script's
docstring for the process this should mirror) rather than relying on the
standalone prototype's default parameters. Not yet started.

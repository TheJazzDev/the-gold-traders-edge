# Weekly Signal Review — Mon 2026-09-21 → Fri 2026-09-25

**Source of truth:** every signal below is a **real, published** signal pulled from
the production API (`GET /v1/signals/?limit=1000`, fetched 2026-09-25 ~12:50 UTC).
Nothing in the totals, trend or stacking sections is simulated. The only simulated
material is the clearly separated counterfactual at the end ("What the new gates
would have done — SIMULATED"), which is never mixed into the real totals.

Price data for the trend / zone / outcome checks: Yahoo Finance (`GC=F`,
`EURUSD=X`, `GBPUSD=X`, the same tickers the live feed uses), 1H for the last
120 days and daily for 3 years, fetched the same day.

## 1. Data coverage — read this first

| Check | Result |
|---|---|
| Signals returned by the API | 14 total (ids 1–17, gaps are deleted duplicates from the 2026-09-08 incident) |
| Signals published this week | **10** (ids 8–17) |
| Earliest this week | `OBR-0923-01`, candle 2026-09-23 17:00, published 18:00 UTC |
| Latest this week | `ARLB-0925-01`, candle 2026-09-25 07:00, published 08:00 UTC |
| Database reset after a redeploy? | **No.** IDs continue from the 2026-09-19 backup (1, 2, 3, 7 are still there, unchanged), so no history was lost. |
| Real outcomes vs Yahoo | For all 9 resolved signals, the first level Yahoo prices touch after publish matches the recorded status (TP or SL). No same-candle TP/SL ambiguity. |

**Service timeline (from `railway deployment list` and the stored worker heartbeat):**

- The service ran until about **Sat 2026-09-19 21:45 UTC** (last heartbeat in the backup), then was stopped.
- It was redeployed **Wed 2026-09-23 14:28 UTC**. That's a day earlier than the "restarted 09-24" in the brief.
- It was redeployed again **Thu 2026-09-24 13:35 UTC** (the pip-size fix `2fc1888`). The current worker `start_time` is 2026-09-24 13:39.

**Gap:** there are **no signals from Mon 21 to Wed 23 ~14:28 UTC because the service
was not running**, not because the strategy saw nothing. This review therefore
covers **about 2 days of live trading (Wed 23 afternoon → Fri 25 morning)**, not a
full week. Nothing here says anything about what would have happened Mon–Wed.

## 2. Every signal

This week is ids 8–17. The four earlier signals (ids 1–7) are included only as
context for the re-entry question (the brief's `OBR-0908-01` / `OBR-0909-01`
example). They are **not** in this week's totals.

- **R:** +RR for TP, −1 for SL, blank if open or cancelled.
- **Published:** candle open + 1h (signals are evaluated at candle close).
- **Time to close:** from publish to the end of the candle that resolved it.
- **Daily / 4H:** the higher-timeframe trend defined in §4, with alignment in brackets.
- **Zone:** the order-block candle and range behind the signal. It was recovered
  from Yahoo data by matching the zone edge the live stop loss implies
  (SL = edge ± 0.3 × ATR56), because Yahoo has revised some candles since.
  All 12 OBR signals matched within 1.5 points.

| Ref | Symbol | Strategy | Dir | Entry | SL | TP | Status | R | Conf | Published (UTC) | Time to close | Daily | 4H | Open same-symbol signals at publish | Zone (OB candle, range) | Re-entry of stopped zone |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| *(id 1)* | XAUUSD | OBR | SHORT | 4513.70 | 4528.42 | 4484.25 | closed_tp | +2.0 | 0.55 | Fri 09-04 13:00 | 1h | UP (counter) | UP (counter) | 0 | 09-04 03:00 4513.6–4523.5 | — |
| *GF-0904-01* | XAUUSD | GF | LONG | 4476.40 | 4323.36 | 4782.48 | cancelled |  | 0.60 | Fri 09-04 15:00 | 144h | UP (with) | UP (with) | 0 | — | — |
| *OBR-0908-01* | XAUUSD | OBR | SHORT | 4429.50 | 4454.42 | 4379.66 | closed_sl | −1.0 | 0.70 | Tue 09-08 17:00 | 15h | UP (counter) | MIXED | 1 (GF-0904-01) | 09-08 07:00 4434.3–4448.6 | — |
| *OBR-0909-01* | XAUUSD | OBR | SHORT | 4438.20 | 4461.81 | 4390.98 | closed_sl | −1.0 | 0.70 | Wed 09-09 11:00 | 3h | UP (counter) | MIXED | 1 (GF-0904-01) | 09-08 13:00 4434.7–4456.3 | **OBR-0908-01** |
| OBR-0923-01 | XAUUSD | OBR | SHORT | 4327.10 | 4351.43 | 4278.44 | closed_tp | +2.0 | 0.70 | Wed 09-23 18:00 | 17h | UP (counter) | DOWN (with) | 0 | 09-23 13:00 4317.3–4346.3 | — |
| OBR-0923-02 | XAUUSD | OBR | SHORT | 4322.70 | 4351.23 | 4265.65 | closed_sl | −1.0 | 0.70 | Wed 09-23 22:00 | 38h | UP (counter) | DOWN (with) | 1 (0923-01) | 09-23 13:00 4317.3–4346.3 | — |
| OBR-0924-01 | XAUUSD | OBR | SHORT | 4319.60 | 4351.03 | 4256.74 | closed_sl | −1.0 | 0.80 | Thu 09-24 02:00 | 34h | DOWN (with) | DOWN (with) | 2 (0923-01, 0923-02) | 09-23 13:00 4317.3–4346.3 | — |
| OBR-0924-02 | XAUUSD | OBR | SHORT | 4318.00 | 4351.14 | 4251.71 | closed_sl | −1.0 | 0.80 | Thu 09-24 06:00 | 30h | DOWN (with) | DOWN (with) | 3 (0923-01, 0923-02, 0924-01) | 09-23 13:00 4317.3–4346.3 | — |
| ARLB-0924-01 | EURUSD | ARLB | LONG | 1.13973 | 1.13698 | 1.14522 | closed_sl | −1.0 | 0.60 | Thu 09-24 08:00 | 3h | DOWN (counter) | DOWN (counter) | 0 | — | — |
| OBR-0924-03 | XAUUSD | OBR | SHORT | 4310.00 | 4318.28 | 4293.44 | closed_sl | −1.0 | 0.70 | Thu 09-24 13:00 | 1h | DOWN (with) | DOWN (with) | 3 (0923-02, 0924-01, 0924-02) | 09-24 08:00 4295.0–4313.4 | — |
| OBR-0924-04 | XAUUSD | OBR | SHORT | 4305.30 | 4338.77 | 4238.37 | closed_sl | −1.0 | 0.70 | Thu 09-24 14:00 | 21h | DOWN (with) | DOWN (with) | 3 (0923-02, 0924-01, 0924-02) | 09-24 01:00 4312.6–4333.8 | **OBR-0924-03** (marginal overlap, see §6) |
| OBR-0924-05 | XAUUSD | OBR | SHORT | 4293.90 | 4338.68 | 4204.33 | closed_sl | −1.0 | 0.70 | Thu 09-24 18:00 | 17h | DOWN (with) | DOWN (with) | 4 (0923-02, 0924-01, 0924-02, 0924-04) | 09-24 01:00 4312.6–4333.8 | **OBR-0924-03** (marginal overlap) |
| OBR-0925-01 | XAUUSD | OBR | LONG | 4311.20 | 4295.49 | 4342.61 | closed_tp | +2.0 | 0.70 | Fri 09-25 07:00 | 4h | DOWN (counter) | DOWN (counter) | 5 (0923-02, 0924-01, 0924-02, 0924-04, 0924-05) | 09-24 12:00 4300.2–4318.2 | — |
| ARLB-0925-01 | GBPUSD | ARLB | LONG | 1.32308 | 1.32078 | 1.32768 | pending |  | 0.60 | Fri 09-25 08:00 | open | DOWN (counter) | DOWN (counter) | 0 | — | — |

Italic rows are pre-week context.

## 3. Totals (this week, real signals only)

| | Signals | TP | SL | Open | Cancelled | Win rate (resolved) | Net R |
|---|---|---|---|---|---|---|---|
| **XAUUSD — Order Block Retest** | 8 | 2 | 6 | 0 | 0 | 25% (2/8) | **−2.0R** |
| **EURUSD — Asian Range London Breakout** | 1 | 0 | 1 | 0 | 0 | 0% (0/1) | **−1.0R** |
| **GBPUSD — Asian Range London Breakout** | 1 | 0 | 0 | 1 | 0 | — | 0 (open) |
| **All** | **10** | **2** | **7** | **1** | **0** | **22% (2/9)** | **−3.0R** |

By strategy: OBR −2.0R (8 resolved). ARLB −1.0R (1 resolved, 1 open).

All 7 stop losses came in two bursts:

- **Thu 24 13:00:** OBR-0924-03 (its stop was only 8.3 points, the tightest of the week) and ARLB-0924-01 (EURUSD, 10:00).
- **Fri 25 10:00–11:00:** a ~45-point gold rally from ~4295 to ~4352 took out **five** open shorts in two candles: 0924-04 and 0924-05 at 10:00, then 0923-02, 0924-01 and 0924-02 at 11:00. The same rally paid the one long (0925-01 TP).

## 4. With or against the higher-timeframe trend?

**Definition** (as asked): **Daily** trend is UP when the last *completed* daily close
is above the daily EMA200 **and** the daily EMA50 is higher than 5 days earlier.
It is DOWN in the mirror case, and MIXED otherwise. **4H** uses the same rule on
completed 4H bars resampled from 1H (EMA200 / EMA50, slope over 5 bars). Only
bars completed before the signal was published are used, so there is no lookahead.

Context: gold is sitting almost exactly on its daily EMA200 (~4343). The daily
close was 4376 on Tue 22 and 4318 on Wed 23. So the daily trend flipped from UP
to DOWN in the middle of this week's cluster, and the regime is transitional, not
trending.

| Alignment (resolved signals, this week) | Daily: n | Daily: SL | Daily: SL rate | 4H: n | 4H: SL | 4H: SL rate |
|---|---|---|---|---|---|---|
| **With trend** | 5 | 5 | **100%** | 7 | 6 | **86%** |
| **Counter-trend** | 4 | 2 | **50%** | 2 | 1 | **50%** |
| Mixed | 0 | — | — | 0 | — | — |

**Result: this week's losses were not counter-trend trades.** Every short from
Thu 24 onward was *with* both the daily and 4H trend, and they lost. The two TPs
were one short that was counter-trend on the daily (0923-01) and one long that
was counter-trend on both (0925-01). The samples are far too small (5 vs 4, 7 vs 2)
to read anything into the difference. What they do show is that a trend gate
**would not have prevented this week's losses**, and a 4H or daily gate would
have removed the long that won.

The one trend-related loss is **ARLB-0924-01**: a EURUSD long taken against a
daily and 4H downtrend. The still-open GBPUSD long (ARLB-0925-01) is also
counter-trend on both.

(Cause 1 check: every OBR signal this week scored 0.70 or 0.80, which means the
existing short-term swing trend check *agreed* with the direction each time.
None got through on the 0.55 + 0.10 reversal-candle path alone. Cause 1 is a real
code gap, but it wasn't the mechanism this week.)

## 5. Stacking — signals published while another same-symbol signal was open

"Open at publish" means an earlier same-symbol signal was published before this
one and had not yet resolved.

- **7 of 10** signals this week were published while at least one other signal on the same symbol was open. All 7 are XAUUSD OBR.
- The XAUUSD signals form **one unbroken overlap chain** from Wed 23 18:00 to Fri 25 11:00. Up to **five** gold shorts were open at once, and 0925-01 even went long while five shorts were still open.
- By zone: **zone A** (09-23 13:00 block, 4317.3–4346.3) was sold **4 times**: 0923-01, 0923-02, 0924-01 and 0924-02. **Zone C** (09-24 01:00 block, 4312.6–4333.8) was sold **twice**: 0924-04 and 0924-05.

| Group (this week) | Signals | TP | SL | Net R |
|---|---|---|---|---|
| **First of cluster / nothing else open** (0923-01, ARLB-0924-01; ARLB-0925-01 still open) | 3 | 1 | 1 | **+1.0R** |
| **Stacked** (published while ≥1 same-symbol signal was open) | 7 | 1 | 6 | **−4.0R** |

**6 of this week's 7 stop losses were stacked signals.** This is cause 3 in action:
the backtest this strategy was validated on only ever holds one trade
(`max_open_trades=1`), so its 37.7% win rate and PF 1.16 say nothing about what
happens when the same zone is sold four times and all four ride the same move.
Stacking turns one bad move into several correlated losses: the Fri 25 rally
cost 5R when a one-at-a-time rule would have lost at most 1R on it.

## 6. Re-entries into a zone that had already stopped out

A signal counts as a re-entry if, before it was published, an earlier signal on an
overlapping zone of the same type had already closed at SL.

- **This week: 2**, both SL. OBR-0924-04 (published 14:00) and OBR-0924-05 (18:00) sold zone C, 4312.6–4333.8. That's the block directly above zone B (4295.0–4313.4), which had stopped out OBR-0924-03 on the 13:00 candle. The overlap is **marginal** (0.8 points). A stricter reading would call these adjacent zones rather than the same zone. Either way, they re-sold resistance that price had just broken through.
- **Pre-week evidence confirmed:** OBR-0909-01 re-sold zone 4434.7–4456.3 **3 hours** after OBR-0908-01's overlapping zone (4434.3–4448.6) stopped out. It stopped out too. The two were different order-block candles (07:00 vs 13:00 on 09-08) with overlapping prices. That's why the existing deduplicator, which needs identical entry/SL/TP, could never catch it.

## 7. Win rate vs the backtest's 37.7%

| Sample | Resolved | Wins | Win rate | P(≤ this many wins \| p = 0.377) |
|---|---|---|---|---|
| This week, all signals | 9 | 2 | 22% | **0.28** |
| This week, OBR only | 8 | 2 | 25% | **0.37** |
| All live OBR history since 2026-09-04 | 11 | 3 | 27% | **0.35** |

(One-sided binomial, treating trades as independent.)

**The 37.7% benchmark is from the wrong trade population.** It comes from the old
tuner, which didn't apply live's `min_confidence=0.60`. Re-running the same
backtest with live's gates (B5, see the strategy ledger's 2026-09-25 entry) gives
a test-slice win rate of **43.6%** (140 trades) for the setup live actually ran.
Against that tougher benchmark, the p-values become **0.17** (all 9), **0.24**
(OBR 8) and **0.22** (OBR history 11). Still not significant, but closer to the
edge.

**This is well within normal variance.** With a 37.7% win-rate strategy, a run
this bad or worse happens roughly 1 time in 3 to 4. Treating the trades as
independent actually makes the week look *worse* than it was. The stacked trades
moved together, so the 8 gold trades were really about 4 independent bets: zone A,
zone B, zone C, and the long. Counted that way it's 2 wins out of 4, P ≈ 0.85.

So the *strategy's* win rate this week is not evidence it has broken. The damage
comes from **how many correlated positions live published per bad move**, which
the backtest never modeled. With one open signal at a time (B1 alone), the same
real signals would have netted 0.0R on gold instead of −2.0R (see the simulated
counterfactual below).

## 8. Verdict on the suspected causes (from this week's real signals)

| # | Suspected cause | Code verified? | Drove this week's losses? |
|---|---|---|---|
| 1 | OBR has no trend filter | ✅ Yes, trend only adds confidence | **No.** Every OBR signal already had short-term trend agreement (0.70 or 0.80), and the shorts that lost were with the daily/4H trend. |
| 2 | `detect_trend(lookback=30)` ignores its lookback | ✅ Yes. `_trend_by_swings` builds swings from all of `self.df` and ignores the window it's passed. | **Indirectly.** It's why the confidence bonus is a very short-term signal, but it didn't separate winners from losers this week. |
| 3 | Live has no open-trade limit and the backtest has 1 | ✅ Yes. `run_once` publishes without checking open signals. | **Yes, the main cause.** 6 of 7 SLs were stacked; one rally cost 5R. |
| 4 | Tuner never applies `min_confidence=0.60` | ✅ Yes. `_production_valid_strategy_func` only checks R:R. | Not directly, but the backtest numbers don't describe the live population. |
| 5 | ARLB has no trend filter; small validation sample | ✅ Yes | **Partly.** The one ARLB loss (EURUSD) was a counter-trend long. |
| — | Re-entry into a stopped-out zone | ✅ Yes (0909-01, and marginally 0924-04/05) | **Minor.** 2 SLs this week. |

## 9. What the new gates would have done — SIMULATED counterfactual

*Everything in this section is **SIMULATED**: the real signals above, run after
the fact through the gate code as committed on this branch
(`signals/order_block_zones.py`, `analysis/trend_gate.py`), using Yahoo 1H data.
It is shown only to illustrate how the gates behave. It is not part of the real
results, and it is not the explanation for this week's losses (§3–§8 are).*

It uses the real XAUUSD signal sequence. With B1, a skipped signal never becomes
"open", so it can't block later ones. The outcome of each kept signal is its real
outcome.

| Gate set (SIMULATED) | Kept XAUUSD signals | Result |
|---|---|---|
| Actual live | all 8 | 2 TP / 6 SL = **−2.0R** |
| B1 only (one open per symbol) | 0923-01 TP, 0924-03 SL, 0924-04 SL | **0.0R** |
| B1 + B3 (1H EMA200 trend gate) | 0923-01 TP, 0924-03 SL, 0924-04 SL. The gate allows every short; it only blocks the long (0925-01), which B1 already skipped. | **0.0R** |
| B1 + B2 (re-entry cooldown) | **none**. All 8 zones overlapped a same-type zone that price had broken through within the previous 20 candles. | **0R** (no trades) |
| B1 + B2 + B3 | none | **0R** |

What B2 blocked, and why:
- **0908-01 / 0909-01:** both blocked. That zone had already been broken on 09-08 before 0908-01 was even published, then broken again at 09-09 07:00.
- **Zone A (0923-01/02, 0924-01/02):** blocked because it overlaps a 4335.5–4354.3 bearish zone broken on 09-23 at 08:00, and later a 4313.3–4330.6 zone broken on 09-24 at 01:00.
- **Zones B and C (0924-03/04/05):** blocked by the same 09-24 01:00 break and the 13:00 stop-out.
- **The long 0925-01:** blocked because bullish zones over the same prices had broken down at 09-25 05:00.

In this choppy, range-bound market (gold sitting on its daily EMA200), overlapping
zones kept breaking both ways. B2 read that as "nothing here is a clean zone" and
would have stood aside the whole time. That removed both winners along with the
six losers. Whether that trade-off pays over two years is answered only by the
held-out backtest, not by these 8 trades.

With B4 on, the EURUSD long **ARLB-0924-01 (−1R)** and the still-open GBPUSD long
**ARLB-0925-01** would not have been published (1H trend DOWN for both).

A full replay of the strategy over the same two days on today's Yahoo data was
also tried. It does **not** reproduce the live signal set: it gives 1 trade
instead of 8, because Yahoo has revised candles since and the `detect_trend` fix
changes confidence scores. So it is left out rather than presented as evidence.

## 10. Fixes and validation outcome (Part B)

Full tables are in `docs/superpowers/specs/strategy-ledger.md` (2026-09-25 entry).
They come from `packages/engine/scripts/validate_signal_gates.py`: a 70/30 split,
fixed configs, no sweep. Test-slice results:

| Change | Test PF | Trades | Win rate | Net % | Max losing streak | Verdict |
|---|---|---|---|---|---|---|
| Gold before (live-equivalent) | 1.48 | 140 | 43.6% | +121.8% | 8 | — |
| Gold **B1+B2** | **1.57** | 83 | 44.6% | +68.5% | **6** | ✅ ship |
| Gold B1+B2+**B3** | 1.33 | 59 | 40.7% | +26.4% | 9 | ❌ fail, keep off |
| EURUSD before → **B4** | 1.18 → 1.98 | 50 → **27** | 38.0% → 51.9% | +12.6% → +33.2% | 7 → 3 | ❌ too few trades, keep off |
| GBPUSD before → **B4** | 1.58 → 2.43 | 47 → **29** | 44.7% → 55.2% | +34.8% → +44.0% | 4 → 4 | ❌ too few trades, keep off |

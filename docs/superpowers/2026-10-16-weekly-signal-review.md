# Weekly Signal Review — Sun 2026-10-11 (gold open) → Fri 2026-10-16

**Source of truth:** every signal below is a **real, published** signal pulled from
the production API (`GET /v1/signals/?limit=60`, fetched 2026-10-19 ~08:30 UTC).
The parity numbers come from `scripts/live_parity_replay.py --days 9` and
`--days 17`, run the same morning against the same Yahoo feed live uses.

## 1. Data coverage

| Check | Result |
|---|---|
| Service uptime | 394.6h at fetch time, so it has run continuously since the `fbf2b0d` deploy (2026-10-02 22:03 UTC). No outage this week. |
| Signals published this week | **6** (OBR-1011-01 → OBR-1015-01) |
| Database reset? | No. IDs continue from earlier weeks. |

## 2. Every signal

| Ref | Symbol | Strategy | Dir | Entry | SL | TP | Status | R | Conf | Candle (UTC) | Closed (UTC) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| OBR-1011-01 | XAUUSD | OBR | LONG | 4210.70 | 4196.13 | 4239.83 | closed_tp | +2.0 | 0.70 | Sun 10-11 22:00 | Mon 10-12 01:00 |
| OBR-1012-01 | XAUUSD | OBR | LONG | 4218.60 | 4196.42 | 4262.96 | closed_sl | −1.0 | 0.70 | Mon 10-12 04:00 | Mon 10-12 09:00 |
| OBR-1012-02 | XAUUSD | OBR | SHORT | 4193.40 | 4205.56 | 4169.07 | closed_sl | −1.0 | 0.65 | Mon 10-12 22:00 | Tue 10-13 04:00 |
| ARLB-1013-01 | EURUSD | ARLB | LONG | 1.11919 | 1.11547 | 1.12664 | closed_sl | −1.0 | 0.60 | Tue 10-13 07:00 | Wed 10-14 12:00 |
| ARLB-1013-02 | GBPUSD | ARLB | LONG | 1.32347 | 1.32027 | 1.32987 | closed_sl | −1.0 | 0.60 | Tue 10-13 07:00 | Wed 10-14 13:00 |
| OBR-1015-01 | XAUUSD | OBR | LONG | 4167.30 | 4101.24 | 4299.43 | open | — | 0.65 | Thu 10-15 07:00 | — (+~30 pts at fetch; gold expiry is 143 market hours, so ~Thu 10-22) |

## 3. Totals

| | Resolved | TP | SL | Open | Net R |
|---|---|---|---|---|---|
| XAUUSD — Order Block Retest | 3 | 1 | 2 | 1 | **0.0R** |
| EURUSD — Asian Range London Breakout | 1 | 0 | 1 | 0 | **−1.0R** |
| GBPUSD — Asian Range London Breakout | 1 | 0 | 1 | 0 | **−1.0R** |
| **All** | **5** | **1** | **4** | **1** | **−2.0R** |

No ARLB signal Wed–Fri. The replay found none either, so nothing was missed.

## 4. Backtest parity

| Window | Symbol | Live | Backtest replay |
|---|---|---|---|
| 9 days | EURUSD | −1.0R (2) | −1.0R (2) ✅ |
| 9 days | GBPUSD | −1.0R (2) | −1.0R (2) ✅ |
| 9 days | XAUUSD | 0.0R (4) | 0.0R (3) ⚠️ |
| 17 days | EURUSD | −2.0R (4) | −2.0R (4) ✅ |
| 17 days | GBPUSD | −2.0R (3) | −2.0R (3) ✅ |
| 17 days | XAUUSD | 0.0R (7) | +1.0R (5) ⚠️ |

Since the 2026-10-02 plumbing fixes, FX live and backtest match trade for trade.
**The FX losses are now the strategy's own results, not data or expiry artefacts.**

Gold signals that appear only in live:

- **10-05 04:00 SHORT (SL, −1R).** The 10-05 00:00 long hit its SL inside the 04:00
  candle. Live's outcome tracker closed it before the generator evaluated that
  candle, so the one-open-signal gate (B1) let a new short through. The backtest
  still had the long open on that bar and skipped it. It's an ordering difference
  and should be rare.
- **10-15 07:00 LONG (open).** Live's entry (4167.3) equals Yahoo's 07:00 close, so
  delayed data isn't the cause. The backtest doesn't fire on that bar. The reason
  isn't known yet.

## 5. Findings

1. **ARLB live record: 1W / 8L, −6R across 9 resolved signals.** That's a 11% win rate.
   The validated test win rate is 38% (EURUSD) and 45% (GBPUSD). At 38%, a run of
   1 win or fewer in 9 happens about 9% of the time. That's unlucky but not
   conclusive.
2. **EURUSD and GBPUSD ARLB fire on the same candle in the same direction.**
   It happened on 10-06 (both SL), 10-13 (both SL) and 10-19 (both SHORT, open).
   Each time that's one bet on the dollar at 2R, not two independent trades.
   Validation scored each pair alone, so the real swings are bigger than the
   per-pair numbers suggest.
3. **Gold OBR since the parity fix is 2W / 4L, 0R.** That's within normal range
   for 6 trades at the validated 44% win rate and 2R target.

## 6. Running record

| Period | Resolved | W / L | Net R |
|---|---|---|---|
| All time (from 2026-09-04) | 27 | 6 / 21 | −9R |
| Since parity fix `fbf2b0d` (2026-10-03 →) | 10 | 2 / 8 | −4R (OBR 0R, ARLB −4R) |

## 7. Follow-ups

- Don't change any strategy settings on this sample. Live has only matched the
  backtest since 2026-10-03.
- ~~Test a USD-exposure gate for correlated EURUSD/GBPUSD ARLB signals~~ Done
  2026-10-19 and ruled out: both variants fail on test. The same run found that
  live's 48h FX expiry is what removes ARLB's validated edge. See strategy-ledger.md
  "2026-10-19".
- Fix or document the B1 same-candle ordering difference so gold parity is exact.

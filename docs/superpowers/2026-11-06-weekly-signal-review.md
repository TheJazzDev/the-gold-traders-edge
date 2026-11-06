# Weekly Signal Review — Sun 2026-11-01 (gold open) → Fri 2026-11-06 (partial)

**Partial week:** fetched Fri 2026-11-06 ~09:00 UTC, before the week closed. Three
trades were open at that point, and anything after it isn't included. Every signal
is a **real, published** signal from the production API
(`GET /v1/signals/?limit=1000`). Parity comes from
`scripts/live_parity_replay.py --days 21`, run the same morning.

## 1. Data coverage

| Check | Result |
|---|---|
| Service uptime | 308h at fetch time, so it has run continuously since the `8f7d220` deploy (2026-10-24 12:49 UTC). No outage this week. |
| Signals published this week | **7** (OBR-1102-01 → ARLB-1106-01) |
| Trades resolved this week | **4** |
| Database reset? | No. IDs continue from earlier weeks. |

## 2. Every signal

| Ref | Symbol | Strategy | Dir | Entry | SL | TP | Status | R | Conf | Candle (UTC) | Closed (UTC) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| OBR-1102-01 | XAUUSD | OBR | SHORT | 3921.80 | 3969.06 | 3827.28 | closed_sl | −1.0 | 0.70 | Mon 11-02 05:00 | Mon 11-02 14:00 |
| ARLB-1102-01 | EURUSD | ARLB | LONG | 1.12007 | 1.11579 | 1.12864 | open | — (~−0.4 at fetch) | 0.60 | Mon 11-02 07:00 | — |
| ARLB-1102-02 | GBPUSD | ARLB | LONG | 1.34165 | 1.33772 | 1.34952 | closed_tp | +2.0 | 0.60 | Mon 11-02 07:00 | Wed 11-04 10:00 |
| OBR-1103-01 | XAUUSD | OBR | SHORT | 3942.40 | 3960.37 | 3906.46 | closed_sl | −1.0 | 0.70 | Tue 11-03 12:00 | Tue 11-03 13:00 |
| OBR-1104-01 | XAUUSD | OBR | LONG | 4059.00 | 4003.28 | 4170.45 | open | — (~+0.4 at fetch) | 0.70 | Wed 11-04 15:00 | — |
| ARLB-1105-01 | GBPUSD | ARLB | SHORT | 1.34709 | 1.35014 | 1.34100 | closed_tp | +2.0 | 0.60 | Thu 11-05 07:00 | Fri 11-06 07:00 |
| ARLB-1106-01 | GBPUSD | ARLB | SHORT | 1.34012 | 1.34665 | 1.32706 | open | — (~+0.1 at fetch) | 0.60 | Fri 11-06 07:00 | — |

## 3. Totals (by exit date)

| | Resolved | TP | SL | Open | Net R |
|---|---|---|---|---|---|
| XAUUSD — Order Block Retest | 2 | 0 | 2 | 1 | **−2.0R** |
| EURUSD — Asian Range London Breakout | 0 | 0 | 0 | 1 | **0.0R** |
| GBPUSD — Asian Range London Breakout | 2 | 2 | 0 | 1 | **+4.0R** |
| **All** | **4** | **2** | **2** | **3** | **+2.0R** |

## 4. Backtest parity

| Window | Symbol | Live | Backtest replay |
|---|---|---|---|
| 21 days | EURUSD | +1.0R (3) | +1.0R (3) ✅ |
| 21 days | GBPUSD | +4.0R (6) | +4.0R (6) ✅ |
| 21 days | XAUUSD | −3.0R (7) | −1.0R (8) ⚠️ |

Every trade this week matches. Gold's one difference is the 10-19 19:00 short.

## 5. Findings

1. **ARLB since the fair start (10-19) is 4W / 3L, +5R.** That's 7 trades, too few
   to call it proven, but no stop-rule trigger is close.
2. **Gold is now the drag, and plumbing no longer explains it.** Since the parity
   fix, gold is 3W / 10L, −4R. Over the same period, today's replay is 3W / 9L,
   −3R. A 13-trade window at −4R or worse happened 14% of the time in the backtest,
   so this is poor but not yet abnormal.
3. **Both gold losses this week were shorts into a rally.** Gold went from about
   3920 on Mon to about 4080 on Fri, and the one long, OBR-1104-01, is still open. Two
   trades can't support a rule change.
4. **Gold had no pre-set stop rule.** It now has one. See strategy-ledger.md
   "2026-11-06".

## 6. Stop rules at fetch time

| Rule | Trigger | Limit | Now |
|---|---|---|---|
| ARLB | Losing streak | 12 | 0 |
| ARLB | Drawdown from live peak | more than 19R | 1R |
| ARLB | First 30 trades from 2026-10-19 | net below −9R | 7 trades, +5R |
| Gold | Losing streak | 9 | 2 |
| Gold | Drawdown from live peak | more than 16R | 10R |
| Gold | First 30 trades from 2026-10-03 | net below −9R | 13 trades, −4R |

No trigger hit. Gold's closest limit is drawdown, 6R away.

## 7. Running record (by exit date)

| Period | Resolved | W / L | Net R |
|---|---|---|---|
| All time (from 2026-09-04) | 41 | 11 / 30 | −8R |
| Since parity fix `fbf2b0d` (2026-10-03 →) | 24 | 7 / 17 | −3R |

## 8. Follow-ups

- No strategy changes on this sample. Check all six stop-rule numbers in every
  weekly review.
- Fix the parity window so trades already open at its start are counted. Until
  then, use `--days 21` or check any FX "backtest only" line by widening the window.
- Update this review if the three open trades resolve in a way that changes the
  week's totals.

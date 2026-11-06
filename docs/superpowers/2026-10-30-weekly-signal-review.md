# Weekly Signal Review — Sun 2026-10-25 (gold open) → Fri 2026-10-30

**Written late:** this review was written on 2026-11-06, a week after the period
ended. Every signal is a **real, published** signal from the production API
(`GET /v1/signals/?limit=1000`, fetched 2026-11-06 ~09:00 UTC). Parity comes from
`scripts/live_parity_replay.py --days 21`, run the same morning.

## 1. Data coverage

| Check | Result |
|---|---|
| Service uptime | 308h at fetch time, so it has run continuously since the `8f7d220` deploy (2026-10-24 12:49 UTC). No outage this week. |
| Signals published this week | **3** (OBR-1027-01 → OBR-1030-01) |
| Trades resolved this week | **6**, including 3 opened on Fri 10-23 |
| Database reset? | No. IDs continue from earlier weeks. |

## 2. Every trade that was published or resolved this week

| Ref | Symbol | Strategy | Dir | Entry | SL | TP | Status | R | Conf | Candle (UTC) | Closed (UTC) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ARLB-1023-01 | EURUSD | ARLB | SHORT | 1.12007 | 1.12319 | 1.11384 | closed_tp | +2.0 | 0.60 | Fri 10-23 07:00 | Tue 10-27 17:00 |
| ARLB-1023-02 | GBPUSD | ARLB | SHORT | 1.33758 | 1.34100 | 1.33073 | closed_tp | +2.0 | 0.60 | Fri 10-23 07:00 | Tue 10-27 16:00 |
| OBR-1023-01 | XAUUSD | OBR | SHORT | 4040.30 | 4066.57 | 3987.76 | closed_sl | −1.0 | 0.70 | Fri 10-23 12:00 | Tue 10-27 14:00 |
| OBR-1027-01 | XAUUSD | OBR | LONG | 4075.80 | 4062.58 | 4102.24 | closed_sl | −1.0 | 0.65 | Tue 10-27 23:00 | Wed 10-28 01:00 |
| OBR-1028-01 | XAUUSD | OBR | LONG | 4054.50 | 4039.44 | 4084.62 | closed_sl | −1.0 | 0.70 | Wed 10-28 15:00 | Wed 10-28 18:00 |
| OBR-1030-01 | XAUUSD | OBR | SHORT | 4001.20 | 4038.06 | 3927.49 | closed_tp | +2.0 | 0.80 | Fri 10-30 05:00 | Fri 10-30 13:00 |

## 3. Totals (by exit date)

| | Resolved | TP | SL | Open at Fri close | Net R |
|---|---|---|---|---|---|
| XAUUSD — Order Block Retest | 4 | 1 | 3 | 0 | **−1.0R** |
| EURUSD — Asian Range London Breakout | 1 | 1 | 0 | 0 | **+2.0R** |
| GBPUSD — Asian Range London Breakout | 1 | 1 | 0 | 0 | **+2.0R** |
| **All** | **6** | **3** | **3** | **0** | **+3.0R** |

## 4. Backtest parity

| Window | Symbol | Live | Backtest replay |
|---|---|---|---|
| 21 days | EURUSD | +1.0R (3) | +1.0R (3) ✅ |
| 21 days | GBPUSD | +4.0R (6) | +4.0R (6) ✅ |
| 21 days | XAUUSD | −3.0R (7) | −3.0R (7) ✅ |

The 21 days cover this whole week, and every trade in it matches. These are the
numbers after the fix below. Before it, gold showed −1.0R (8), with the 10-19 19:00
short as backtest only. That short was blocked by OBR-1015-01, which opened before
the 21-day window, so it now drops out. `--days 28` matches all 11 gold trades on
today's data, including OBR-1015-01. That trade did not reproduce on 10-24's data,
so Yahoo's history for that day appears to have changed again (see the 10-24 ledger
entry).

**False alarm, fixed the same day.** `--days 14` first reported EURUSD and GBPUSD
shorts on 10-26 07:00 as "backtest only (TP)", worth +4R. Live did not miss them.
The replay started after the 10-23 trades opened, so it didn't know they were still
open on 10-26. The replay now waits for any live trade carried into its window, and
`--days 14` shows no FX mismatch.

## 5. Findings

1. **ARLB ended its losing streak.** The two 10-23 shorts both hit TP on 10-27,
   the first ARLB wins since 10-01. Both ran past 48 market hours, so the old expiry
   would have cancelled them; the 10-19 change is why they counted. They're one USD
   bet, not two independent wins (see the 10-16 review).
2. **OBR-1023-01 nearly hit TP, then lost.** It reached 3989.1 on 10-23 against a
   TP of 3987.76, 1.34 points short, and stopped out on 10-27 for −1R. That's a
   single trade and doesn't justify changing the exit.
3. **Gold longs lost twice in a day.** OBR-1027-01 and OBR-1028-01 stopped out
   within 2–3 hours. Replay took the same trades.

## 6. ARLB stop rule at Fri close

| Trigger | Limit | At 10-30 |
|---|---|---|
| Losing streak | 12 | 0 |
| Drawdown from live peak | more than 19R | 5R |
| First 30 trades from 2026-10-19 | net below −9R | 5 trades, +1R |

No trigger hit.

## 7. Running record (by exit date)

| Period | Resolved | W / L | Net R |
|---|---|---|---|
| All time (from 2026-09-04) | 37 | 9 / 28 | −10R |
| Since parity fix `fbf2b0d` (2026-10-03 →) | 20 | 5 / 15 | −5R |

## 8. Follow-ups

- No strategy changes on this sample.
- ~~Fix the parity window's blind spot for trades already open at its start~~
  Fixed 2026-11-06 in `services/weekly_parity.py`.

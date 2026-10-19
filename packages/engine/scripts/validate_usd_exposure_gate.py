#!/usr/bin/env python3
"""
Does a USD-exposure gate on the EURUSD / GBPUSD Asian Range London
Breakout pair improve risk-adjusted return?

Both workers enter at the 07:00 UTC candle, and both pairs are quoted
against USD, so on many days they fire together in the same direction:
one dollar bet at 2R, not two independent trades. Live hit this on
2026-10-06 and 2026-10-13 (all four legs SL). Each pair was validated
alone, so the combined drawdown has never been measured.

Pre-registered before scoring the test slice (see the 2026-10-16 weekly
review). The config is fixed: the committed tuned_configs/*usd_1h.json
with live gates and live's expiry. Nothing is swept.

  independent - what live does: each pair at 1R, its own one-open gate
  drop_gbp    - when both enter on the same candle in the same direction,
                skip GBPUSD (EURUSD has the better TRAIN PF, 1.29 vs 1.10).
                GBPUSD is re-run with those entries blocked, so its
                one-open slot frees up the way it would live.
  half_size   - when both enter together, each leg risks 0.5R

Ship rule: a variant ships only if net R / max drawdown beats
`independent` on BOTH train and test.

Usage (from packages/engine):
    venv/bin/python scripts/validate_usd_exposure_gate.py
"""
import contextlib
import io
import json
import sys
from pathlib import Path

import pandas as pd

ENGINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(ENGINE / 'src'))

from backtesting.engine import TradeStatus  # noqa: E402
from backtesting.live_parity import live_gated_strategy_func, run_on_window  # noqa: E402
from data.loader import GoldDataLoader  # noqa: E402
from signals.forex_session_strategy import ForexSessionStrategy  # noqa: E402
import tune_forex_session_strategy as forex_tuner  # noqa: E402

TRAIN_FRAC = 0.7
PAIRS = {
    'EURUSD': ('data/processed/eurusd_1h_2023_2026.csv', 'tuned_configs/eurusd_1h.json'),
    'GBPUSD': ('data/processed/gbpusd_1h_2023_2026.csv', 'tuned_configs/gbpusd_1h.json'),
}
RESOLVED = (TradeStatus.CLOSED_TP, TradeStatus.CLOSED_SL)


def _load(symbol):
    csv, config_file = PAIRS[symbol]
    with contextlib.redirect_stdout(io.StringIO()):
        df = GoldDataLoader().load_from_csv(str(ENGINE / csv))
    tuned = json.loads((ENGINE / config_file).read_text())
    return df, tuned


def _run(symbol, df, tuned, start, end, blocked=frozenset()):
    """Resolved trades (entry, exit, direction, R) for df[start:end) under
    live's gates and expiry, skipping entries on `blocked` (time, direction)."""
    strategy = ForexSessionStrategy(config=tuned['config'])
    gated = live_gated_strategy_func(strategy)

    def func(frame, idx):
        signal = gated(frame, idx)
        if signal is not None and (frame.index[idx], signal.direction.name) in blocked:
            return None
        return signal

    window = df[df.index < end] if end is not None else df
    with contextlib.redirect_stdout(io.StringIO()):
        result = run_on_window(window, start, func,
                               warmup=forex_tuner.slice_warmup_candles(strategy.config),
                               expiry_hours=tuned.get('expiry_hours', 48.0))
    trades = []
    for t in result.trades:
        if t.status not in RESOLVED:
            continue
        sign = 1 if t.direction.name == 'LONG' else -1
        r = (t.exit_price - t.entry_price) * sign / abs(t.entry_price - t.stop_loss)
        trades.append({'symbol': symbol, 'entry': t.entry_time, 'exit': t.exit_time,
                       'direction': t.direction.name, 'r': r, 'size': 1.0})
    return trades


def _stats(trades):
    trades = sorted(trades, key=lambda t: t['exit'])
    pnl = [t['r'] * t['size'] for t in trades]
    equity = peak = max_dd = 0.0
    for p in pnl:
        equity += p
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    gains = sum(p for p in pnl if p > 0)
    losses = -sum(p for p in pnl if p < 0)
    by_day = pd.Series(pnl, index=[pd.Timestamp(t['exit']).date() for t in trades]).groupby(level=0).sum()
    return {
        'trades': len(trades),
        'net_r': round(equity, 2),
        'pf': round(gains / losses, 2) if losses else float('inf'),
        'max_dd_r': round(max_dd, 2),
        'net_over_dd': round(equity / max_dd, 2) if max_dd else float('inf'),
        'worst_day_r': round(by_day.min(), 2) if len(by_day) else 0.0,
    }


def _key(t):
    return (t['entry'], t['direction'])


def evaluate(slice_name, eur, gbp, eur_df, eur_tuned, gbp_df, gbp_tuned, start, end):
    eur_keys = {_key(t) for t in eur}
    co = [t for t in gbp if _key(t) in eur_keys]
    eur_by_key = {_key(t): t for t in eur}
    same_outcome = sum((t['r'] > 0) == (eur_by_key[_key(t)]['r'] > 0) for t in co)

    gbp_dropped = _run('GBPUSD', gbp_df, gbp_tuned, start, end, blocked=frozenset(eur_keys))

    halved = [dict(t) for t in eur + gbp]
    co_keys = {_key(t) for t in co}
    for t in halved:
        if _key(t) in co_keys:
            t['size'] = 0.5

    rows = {
        'independent': _stats(eur + gbp),
        'drop_gbp': _stats(eur + gbp_dropped),
        'half_size': _stats(halved),
    }
    print(f"\n== {slice_name}  ({start.date()} → {(end or eur_df.index[-1]).date()})")
    print(f"EURUSD {len(eur)} trades, GBPUSD {len(gbp)} trades, co-fired same candle+direction: "
          f"{len(co)} ({len(co) / max(1, len(gbp)):.0%} of GBPUSD), same outcome in "
          f"{same_outcome}/{len(co)}")
    print(f"{'variant':12} {'trades':>6} {'netR':>7} {'PF':>5} {'maxDD':>6} {'net/DD':>7} {'worstDay':>8}")
    for name, s in rows.items():
        print(f"{name:12} {s['trades']:>6} {s['net_r']:>7} {s['pf']:>5} {s['max_dd_r']:>6} "
              f"{s['net_over_dd']:>7} {s['worst_day_r']:>8}")
    return rows


def main():
    eur_df, eur_tuned = _load('EURUSD')
    gbp_df, gbp_tuned = _load('GBPUSD')
    split = eur_df.index[int(len(eur_df) * TRAIN_FRAC)]
    first = eur_df.index[forex_tuner.slice_warmup_candles(eur_tuned['config'])]

    results = {}
    for slice_name, start, end in (('train', first, split), ('test', split, None)):
        eur = _run('EURUSD', eur_df, eur_tuned, start, end)
        gbp = _run('GBPUSD', gbp_df, gbp_tuned, gbp_df.index[gbp_df.index >= start][0], end)
        results[slice_name] = evaluate(slice_name, eur, gbp, eur_df, eur_tuned,
                                       gbp_df, gbp_tuned, start, end)

    print("\nShip rule: net/DD beats independent on train AND test")
    base = {s: results[s]['independent']['net_over_dd'] for s in results}
    for variant in ('drop_gbp', 'half_size'):
        passes = all(results[s][variant]['net_over_dd'] > base[s] for s in results)
        print(f"  {variant:10} {'PASS' if passes else 'FAIL'}  "
              + "  ".join(f"{s}: {results[s][variant]['net_over_dd']} vs {base[s]}" for s in results))


if __name__ == '__main__':
    main()

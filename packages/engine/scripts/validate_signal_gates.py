#!/usr/bin/env python3
"""
Before/after validation of the 2026-09-25 signal gates (B1-B5).

Every variant runs on the same chronological 70/30 train/test split with a
fixed, pre-chosen config: gold uses the committed tuned_configs/1h.json
shared config, forex the committed default config. Nothing is swept, so the
test slice is looked at once per pre-registered variant, and a variant
can't win by parameter search (see strategy-ledger.md's methodology note).

Variants (test slice scored with warm-up history, trades only in the slice,
live gates on: R:R >= 1.5, confidence >= 0.60, one open trade):

  XAUUSD Order Block Retest
    legacy    - the old tuner method (no confidence gate, no warm-up);
                should reproduce 1h.json's 114 trades / PF 1.16
    before    - what live actually ran: old detect_trend, no cooldown
    b1_b2         - + re-entry cooldown (B1 is the one-open-trade rule the
                    backtest always had)
    b1_b2_shipped - the same, on this branch's code (must equal b1_b2)
    b1_b2_dt30    - + detect_trend honouring lookback=30 literally
    b1_b2_b3      - shipped B1+B2 + HTF trend gate
    b1_b2_dt30_b3 - b1_b2_dt30 + HTF trend gate
  EURUSD / GBPUSD Asian Range London Breakout
    legacy    - the old tuner method; should reproduce 50 / 47 trades
    before    - live gates, no trend gate
    b4        - + HTF trend gate

Usage (from packages/engine):
    venv/bin/python scripts/validate_signal_gates.py --out results.json
"""
import argparse
import contextlib
import io
import json
import sys
from multiprocessing import Pool
from pathlib import Path

ENGINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(ENGINE / 'src'))

from analysis.technical import TechnicalAnalysis, TrendDirection  # noqa: E402
from backtesting.engine import BacktestEngine  # noqa: E402
from backtesting.live_parity import live_gated_strategy_func, resolved_stats, run_on_window  # noqa: E402
from data.loader import GoldDataLoader  # noqa: E402
from signals.forex_session_strategy import ForexSessionStrategy  # noqa: E402
from signals.gold_strategy import GoldStrategy  # noqa: E402
import tune_forex_session_strategy as forex_tuner  # noqa: E402
import tune_strategy as gold_tuner  # noqa: E402

TRAIN_FRAC = 0.7

DATA = {
    'XAUUSD': ENGINE / 'data/processed/xauusd_1h_2024_2026.csv',
    'EURUSD': ENGINE / 'data/processed/eurusd_1h_2023_2026.csv',
    'GBPUSD': ENGINE / 'data/processed/gbpusd_1h_2023_2026.csv',
}


def _legacy_trend_by_swings(self, df):
    """detect_trend's swing method as live ran it before B3: swings built
    from the whole history (self.df), ignoring the lookback window `df`."""
    swing_points = self.detect_swing_points(lookback=3, min_strength=1)
    if len(swing_points) < 4:
        return TrendDirection.SIDEWAYS
    recent_highs = [sp for sp in swing_points[-10:] if sp.is_high]
    recent_lows = [sp for sp in swing_points[-10:] if not sp.is_high]
    if len(recent_highs) < 2 or len(recent_lows) < 2:
        return TrendDirection.SIDEWAYS
    hh = recent_highs[-1].price > recent_highs[-2].price
    hl = recent_lows[-1].price > recent_lows[-2].price
    lh = recent_highs[-1].price < recent_highs[-2].price
    ll = recent_lows[-1].price < recent_lows[-2].price
    if hh and hl:
        return TrendDirection.UPTREND
    if lh and ll:
        return TrendDirection.DOWNTREND
    return TrendDirection.SIDEWAYS


_CURRENT_TREND_BY_SWINGS = TechnicalAnalysis._trend_by_swings
_CURRENT_DETECT_TREND = TechnicalAnalysis.detect_trend

# trend: how OBR's confidence-bonus trend is computed.
#   'legacy'   - pre-fix code path, patched back in (what live ran)
#   'shipped'  - this branch as committed (full-frame swings; identical
#                result to 'legacy', run to prove it)
#   'window30' - detect_trend honouring lookback=30 literally
GOLD_VARIANTS = {
    'legacy':         dict(legacy_method=True,  trend='legacy',   cooldown=0,  gate=False),
    'before':         dict(legacy_method=False, trend='legacy',   cooldown=0,  gate=False),
    'b1_b2':          dict(legacy_method=False, trend='legacy',   cooldown=20, gate=False),
    'b1_b2_shipped':  dict(legacy_method=False, trend='shipped',  cooldown=20, gate=False),
    'b1_b2_dt30':     dict(legacy_method=False, trend='window30', cooldown=20, gate=False),
    'b1_b2_b3':       dict(legacy_method=False, trend='shipped',  cooldown=20, gate=True),
    'b1_b2_dt30_b3':  dict(legacy_method=False, trend='window30', cooldown=20, gate=True),
}
FOREX_VARIANTS = {
    'legacy': dict(legacy_method=True,  gate=False),
    'before': dict(legacy_method=False, gate=False),
    'b4':     dict(legacy_method=False, gate=True),
}


def _load(symbol):
    with contextlib.redirect_stdout(io.StringIO()):
        df = GoldDataLoader().load_from_csv(str(DATA[symbol]))
    split = int(len(df) * TRAIN_FRAC)
    return df, df.iloc[:split], df.index[split]


def _legacy_func(strategy):
    """The pre-B5 tuner gate: R:R only, no confidence minimum."""
    return live_gated_strategy_func(strategy, min_confidence=0.0)


def run_job(job):
    symbol, variant, slice_name = job
    df, train_df, test_start = _load(symbol)

    if symbol == 'XAUUSD':
        v = GOLD_VARIANTS[variant]
        TechnicalAnalysis._trend_by_swings = (
            _legacy_trend_by_swings if v['trend'] == 'legacy' else _CURRENT_TREND_BY_SWINGS
        )
        TechnicalAnalysis.detect_trend = (
            (lambda self, lookback=50, method='swing': _CURRENT_DETECT_TREND(self, 30, method))
            if v['trend'] == 'window30' else _CURRENT_DETECT_TREND
        )
        base = json.loads((ENGINE / 'tuned_configs/1h.json').read_text())['config']
        config = {**base, 'reentry_cooldown_candles': v['cooldown'], 'htf_trend_filter': v['gate']}
        strategy = GoldStrategy(config=config)
        warmup = gold_tuner.slice_warmup_candles(strategy.config)
    else:
        v = FOREX_VARIANTS[variant]
        config = {**ForexSessionStrategy.DEFAULT_CONFIG, 'htf_trend_filter': v['gate']}
        strategy = ForexSessionStrategy(config=config)
        warmup = forex_tuner.slice_warmup_candles(strategy.config)

    func = _legacy_func(strategy) if v['legacy_method'] else live_gated_strategy_func(strategy)

    with contextlib.redirect_stdout(io.StringIO()):
        if slice_name == 'train':
            result = BacktestEngine(initial_balance=10000, position_size_pct=2.0).run(
                train_df, func, max_open_trades=1)
        elif v['legacy_method']:
            result = BacktestEngine(initial_balance=10000, position_size_pct=2.0).run(
                df[df.index >= test_start], func, max_open_trades=1)
        else:
            result = run_on_window(df, test_start, func, warmup=warmup)

    stats = {k: float(x) for k, x in resolved_stats(result).items()}
    return {'symbol': symbol, 'variant': variant, 'slice': slice_name, **stats,
            'test_start': str(test_start)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', default='gate_validation.json')
    parser.add_argument('--workers', type=int, default=7)
    parser.add_argument('--only', nargs='*', help='Run only these variant names')
    args = parser.parse_args()

    jobs = [('XAUUSD', v, s) for v in GOLD_VARIANTS for s in ('test', 'train')]
    jobs += [(sym, v, s) for sym in ('EURUSD', 'GBPUSD') for v in FOREX_VARIANTS for s in ('test', 'train')]
    if args.only:
        jobs = [j for j in jobs if j[1] in args.only]
    # Longest (gold train) first so the pool stays busy.
    jobs.sort(key=lambda j: (j[0] != 'XAUUSD', j[2] != 'train'))

    # maxtasksperchild=1: a fresh process per job, so no state (patched
    # methods, caches) can leak from one variant into another.
    with Pool(args.workers, maxtasksperchild=1) as pool:
        results = []
        for r in pool.imap_unordered(run_job, jobs):
            print(f"{r['symbol']} {r['variant']:14} {r['slice']:5} PF={r['profit_factor']:.2f} "
                  f"trades={int(r['total_trades'])} WR={r['win_rate']:.1f}% net={r['net_profit_pct']:.1f}% "
                  f"maxLS={int(r['max_losing_streak'])}", flush=True)
            results.append(r)

    Path(args.out).write_text(json.dumps(results, indent=2))
    print(f"wrote {args.out}")


if __name__ == '__main__':
    main()

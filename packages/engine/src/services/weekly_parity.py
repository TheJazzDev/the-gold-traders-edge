"""
The weekly report's backtest-parity section: replay the week through the
backtest with each live worker's own strategy, gates and expiry, and
compare it with what live published (see backtesting/parity_replay.py).
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, Iterable, List, Optional

import pandas as pd

from backtesting.live_parity import live_gated_strategy_func
from backtesting.parity_replay import build_parity_text, compare, live_outcome, replay_outcomes


@dataclass
class ParityTarget:
    """What one live worker runs."""
    symbol: str
    timeframe: str
    strategy: object
    min_rr: float
    min_confidence: float
    expiry_hours: float
    warmup: int  # candles of history live evaluates with (its lookback_periods)


def clone_strategy(strategy):
    """A fresh copy, so replaying never touches the live worker's strategy
    state (e.g. OBR's re-entry cooldown) from the report thread."""
    clone = type(strategy)(config=dict(strategy.config))
    clone.rules_enabled = dict(strategy.rules_enabled)
    return clone


def build_weekly_parity_text(
    targets: List[ParityTarget],
    live_signals: Iterable,
    fetch_candles: Callable[[ParityTarget, int], pd.DataFrame],
    days: int = 7,
    now: Optional[datetime] = None,
) -> str:
    """
    `live_signals`: Signal rows (or anything with the same attributes).
    `fetch_candles(target, count)`: the latest `count` closed candles.
    """
    since = pd.Timestamp((now or datetime.utcnow()) - timedelta(days=days))

    replay = []
    for target in targets:
        candles_needed = target.warmup + days * 24 + 48
        df = fetch_candles(target, candles_needed)
        func = live_gated_strategy_func(clone_strategy(target.strategy),
                                        min_rr=target.min_rr, min_confidence=target.min_confidence)
        replay += replay_outcomes(target.symbol, df, func, start=since,
                                  warmup=target.warmup, expiry_hours=target.expiry_hours)

    live_keys = {(t.symbol, t.timeframe) for t in targets}
    live = []
    for s in live_signals:
        if (s.symbol, s.timeframe) not in live_keys or pd.Timestamp(s.timestamp) < since:
            continue
        status = getattr(s.status, 'value', s.status)
        direction = getattr(s.direction, 'value', s.direction)
        outcome = live_outcome(s.symbol, s.timestamp, direction, status, s.pnl_pips, s.risk_pips, s.notes)
        if outcome is not None:
            live.append(outcome)

    return build_parity_text(compare(live, replay), days=days)

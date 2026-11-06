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


# How far back to load live signals: the report's week plus any trade still
# open when it starts. ARLB has no expiry, so that trade can be weeks old.
LIVE_HISTORY_DAYS = 90


@dataclass
class ParityTarget:
    """What one live worker runs."""
    symbol: str
    timeframe: str
    strategy: object
    min_rr: float
    min_confidence: float
    expiry_hours: Optional[float]  # None = never expires
    warmup: int  # candles of history live evaluates with (its lookback_periods)


def clone_strategy(strategy):
    """A fresh copy, so replaying never touches the live worker's strategy
    state (e.g. OBR's re-entry cooldown) from the report thread."""
    clone = type(strategy)(config=dict(strategy.config))
    clone.rules_enabled = dict(strategy.rules_enabled)
    return clone


def replay_start(symbol: str, timeframe: str, live_signals: List, since: pd.Timestamp) -> Optional[pd.Timestamp]:
    """
    When the replay may take its first trade: `since`, or later if live
    carried a trade into the window, because live's one-open gate blocked
    every entry until that trade closed. Without this the replay starts flat
    and reports those blocked entries as trades live missed, as it did for
    EURUSD and GBPUSD on 2026-10-26. None = the trade is still open.
    """
    start = since
    for s in live_signals:
        if s.symbol != symbol or s.timeframe != timeframe or pd.Timestamp(s.timestamp) >= since:
            continue
        outcome = _as_outcome(s)
        if outcome is None:
            continue
        if outcome.outcome == 'open':
            return None
        if s.closed_at is not None:
            start = max(start, pd.Timestamp(s.closed_at))
    return start


def _as_outcome(s):
    status = getattr(s.status, 'value', s.status)
    direction = getattr(s.direction, 'value', s.direction)
    return live_outcome(s.symbol, s.timestamp, direction, status, s.pnl_pips, s.risk_pips, s.notes)


def build_weekly_parity_text(
    targets: List[ParityTarget],
    live_signals: Iterable,
    fetch_candles: Callable[[ParityTarget, int], pd.DataFrame],
    days: int = 7,
    now: Optional[datetime] = None,
) -> str:
    """
    `live_signals`: Signal rows (or anything with the same attributes),
    reaching back far enough to include trades still open when the window
    starts.
    `fetch_candles(target, count)`: the latest `count` closed candles.
    """
    since = pd.Timestamp((now or datetime.utcnow()) - timedelta(days=days))
    live_signals = list(live_signals)

    replay = []
    for target in targets:
        start = replay_start(target.symbol, target.timeframe, live_signals, since)
        if start is None:
            continue
        candles_needed = target.warmup + days * 24 + 48
        df = fetch_candles(target, candles_needed)
        func = live_gated_strategy_func(clone_strategy(target.strategy),
                                        min_rr=target.min_rr, min_confidence=target.min_confidence)
        replay += replay_outcomes(target.symbol, df, func, start=start,
                                  warmup=target.warmup, expiry_hours=target.expiry_hours)

    live_keys = {(t.symbol, t.timeframe) for t in targets}
    live = []
    for s in live_signals:
        if (s.symbol, s.timeframe) not in live_keys or pd.Timestamp(s.timestamp) < since:
            continue
        outcome = _as_outcome(s)
        if outcome is not None:
            live.append(outcome)

    return build_parity_text(compare(live, replay), days=days)

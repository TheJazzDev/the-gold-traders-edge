"""
Order-block zone detection, with a re-entry cooldown for zones that have
already stopped out.

An order block is the zone of a strong-bodied candle (body > 60% of range):
for a bearish candle, low..open; for a bullish candle, open..high. A retest
is the current candle's high (bearish) or low (bullish) trading back inside
that zone.

A zone has "stopped out" once a later candle trades through the level a
trade on it would have used as its stop: zone edge +/- sl_buffer_atr * ATR,
the same stop Order Block Retest places. That is derived from price alone,
so it behaves identically in the backtest, live, and across restarts, with
no dependency on which signals happened to be published.

With a cooldown, any candidate zone of the same type overlapping a zone that
stopped out within the last `reentry_cooldown_candles` candles is skipped,
so a different order-block candle over the same prices (OBR-0908-01 then
OBR-0909-01) can't re-sell a level that just failed. A new block that
doesn't overlap is traded normally.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

STRONG_BODY_RATIO = 0.6


@dataclass(frozen=True)
class StoppedZone:
    type: str          # 'bullish' | 'bearish'
    low: float
    high: float
    stopped_at: int    # positional index of the candle that hit the stop


def _zone_of(o: float, h: float, l: float, c: float) -> Optional[tuple]:
    """(type, low, high) for a strong-bodied candle, else None."""
    rng = h - l
    if rng == 0 or abs(c - o) <= rng * STRONG_BODY_RATIO:
        return None
    if c > o:
        return 'bullish', o, h
    return 'bearish', l, o


def stopped_out_zones(
    df: pd.DataFrame, idx: int, atr: Sequence[float], sl_buffer_atr: float, start: int
) -> List[StoppedZone]:
    """
    Zones formed by candles in [start, idx) whose stop level was hit by any
    later candle up to and including idx (the evaluated candle has closed,
    so its range is known). NaN ATR never counts as a hit.
    """
    o, h, l, c = (df[col].to_numpy() for col in ('open', 'high', 'low', 'close'))
    atr = np.asarray(atr, dtype=float)
    zones = []
    for i in range(max(0, start), idx):
        zone = _zone_of(o[i], h[i], l[i], c[i])
        if zone is None:
            continue
        kind, low, high = zone
        later = slice(i + 1, idx + 1)
        buffer = atr[later] * sl_buffer_atr
        if kind == 'bearish':
            hit = h[later] > high + buffer
        else:
            hit = l[later] < low - buffer
        hit &= ~np.isnan(buffer)
        if hit.any():
            zones.append(StoppedZone(kind, low, high, i + 1 + int(np.argmax(hit))))
    return zones


def detect_order_block(
    df: pd.DataFrame,
    idx: int,
    lookback: int = 20,
    atr: Optional[Sequence[float]] = None,
    sl_buffer_atr: float = 0.3,
    reentry_cooldown_candles: int = 0,
) -> Optional[Dict]:
    """
    Oldest order block in [idx - lookback, idx - 3) that the candle at idx
    retests, skipping zones in cooldown. With reentry_cooldown_candles=0
    this is exactly the original GoldStrategy detector.
    """
    if idx < lookback + 5:
        return None

    blocked: List[StoppedZone] = []
    if reentry_cooldown_candles > 0 and atr is not None:
        blocked = [
            z for z in stopped_out_zones(df, idx, atr, sl_buffer_atr,
                                         start=idx - lookback - reentry_cooldown_candles)
            if idx - z.stopped_at <= reentry_cooldown_candles
        ]

    current = df.iloc[idx]
    for i in range(idx - lookback, idx - 3):
        candle = df.iloc[i]
        zone = _zone_of(candle['open'], candle['high'], candle['low'], candle['close'])
        if zone is None:
            continue
        kind, low, high = zone
        probe = current['low'] if kind == 'bullish' else current['high']
        if not (low <= probe <= high):
            continue
        if any(z.type == kind and z.low <= high and low <= z.high for z in blocked):
            continue
        return {'type': kind, 'high': high, 'low': low, 'index': i}

    return None

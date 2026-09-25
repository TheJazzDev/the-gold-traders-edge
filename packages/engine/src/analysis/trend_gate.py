"""
Higher-timeframe trend gate.

A hard directional filter shared by Order Block Retest (B3) and Asian Range
London Breakout (B4): a signal may only go in the direction of the 1H EMA
trend. UPTREND means the last close is above the EMA *and* the EMA is higher
than `slope_candles` ago; DOWNTREND is the mirror; anything else is SIDEWAYS
and blocks both directions.

The default (EMA200 on 1H, slope over 24 candles, i.e. about one trading
day) was chosen up front, not searched for — see the 2026-09-25 entries in
docs/superpowers/specs/strategy-ledger.md.

The EMA is computed over exactly the last warmup_candles(ema_period)
candles. The backtest hands a strategy the whole history while live only
fetches a few hundred candles, and a recursive EMA depends on its starting
point, so fixing the window is what keeps live and backtest identical.
Fewer candles than that returns SIDEWAYS, so the gate fails closed instead
of trading on an under-warmed EMA.
"""

import pandas as pd

from analysis.technical import TrendDirection
from backtesting.engine import TradeDirection

WARMUP_MULTIPLE = 3


def warmup_candles(ema_period: int) -> int:
    """Candles the gate needs (and reads) for an EMA of `ema_period`."""
    return WARMUP_MULTIPLE * ema_period


def ema_trend(close: pd.Series, ema_period: int = 200, slope_candles: int = 24) -> TrendDirection:
    window = warmup_candles(ema_period)
    if len(close) < window:
        return TrendDirection.SIDEWAYS

    ema = close.iloc[-window:].ewm(span=ema_period, adjust=False).mean()
    last_close, last_ema, prev_ema = close.iloc[-1], ema.iloc[-1], ema.iloc[-1 - slope_candles]

    if last_close > last_ema and last_ema > prev_ema:
        return TrendDirection.UPTREND
    if last_close < last_ema and last_ema < prev_ema:
        return TrendDirection.DOWNTREND
    return TrendDirection.SIDEWAYS


def trend_allows(direction: TradeDirection, trend: TrendDirection) -> bool:
    if direction == TradeDirection.LONG:
        return trend == TrendDirection.UPTREND
    return trend == TrendDirection.DOWNTREND

"""
Tests for GoldStrategy._shallow_pullback_continuation — from the user's own
trading plan hard fact: "In strong bullish moves, price may only pull back
to the 23.6% level before continuing." Confirmation = a small consolidation
near 23.6%, followed by a break of structure in the trend direction.

Unlike Fibonacci Golden Zone Confluence (deep pullback, reversal), this
trades trend CONTINUATION off a shallow pullback. See
docs/superpowers/specs/strategy-ledger.md.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from signals.gold_strategy import GoldStrategy, FibZone, MarketStructure
from backtesting.engine import TradeDirection
from analysis.technical import TrendDirection


UP_ZONE = FibZone(
    swing_low=1900.0, swing_high=2100.0,
    level_236=2052.8, level_382=2023.6, level_500=2000.0,
    level_618=1976.4, level_786=1942.8,
    direction='up',
)

DOWN_ZONE = FibZone(
    swing_low=1900.0, swing_high=2100.0,
    level_236=1947.2, level_382=1976.4, level_500=2000.0,
    level_618=2023.6, level_786=2057.2,
    direction='down',
)


def _df(rows: int, pullback_close: float, pullback_at: int, entry_close: float,
        baseline: float = 2090.0) -> pd.DataFrame:
    """Builds a flat df of `rows` candles, all closing at `baseline`, except
    row `pullback_at` closes at `pullback_close` and the LAST row closes at
    `entry_close`. Default baseline (2090, for UP_ZONE) sits within the
    "shallow" band (above level_382=2023.6) but far enough from
    level_236=2052.8 that the filler rows alone don't register as "near
    23.6%" (fib_tolerance's ~30.8-point band is wider than the 236-382 gap
    itself, so anything between them would spuriously read as "near 236")."""
    dates = pd.date_range(start='2024-01-01', periods=rows, freq='1h')
    closes = [baseline] * rows
    closes[pullback_at] = pullback_close
    closes[-1] = entry_close
    lows = [c - 1 for c in closes]
    highs = [c + 1 for c in closes]
    return pd.DataFrame({'open': closes, 'high': highs, 'low': lows, 'close': closes}, index=dates)


def _stubbed_strategy(fib_zone, trend, structure, pullback_window=10):
    strategy = GoldStrategy(config={'pullback_window': pullback_window})
    fake_ta = MagicMock()
    fake_ta.calculate_atr.return_value = pd.Series([5.0])
    fake_ta.detect_trend.return_value = trend
    strategy.ta = fake_ta
    strategy._get_fib_zones = lambda df, idx: fib_zone
    strategy._detect_market_structure = lambda df, idx: structure
    return strategy


class TestShallowPullbackContinuation:
    def test_shallow_pullback_then_bos_triggers_long_in_uptrend(self):
        strategy = _stubbed_strategy(UP_ZONE, TrendDirection.UPTREND, MarketStructure.BOS)
        # Entry/breakout candle continues UP away from the pullback, back
        # toward the baseline — not a further move down into the zone.
        df = _df(rows=11, pullback_close=UP_ZONE.level_236, pullback_at=8, entry_close=2070.0)

        result = strategy._shallow_pullback_continuation(df, idx=10)

        assert result.triggered is True
        assert result.direction == TradeDirection.LONG
        assert result.stop_loss < result.entry_price < result.take_profit

    def test_shallow_pullback_then_bos_triggers_short_in_downtrend(self):
        strategy = _stubbed_strategy(DOWN_ZONE, TrendDirection.DOWNTREND, MarketStructure.BOS)
        df = _df(rows=11, pullback_close=DOWN_ZONE.level_236, pullback_at=8, entry_close=1930.0, baseline=1910.0)

        result = strategy._shallow_pullback_continuation(df, idx=10)

        assert result.triggered is True
        assert result.direction == TradeDirection.SHORT
        assert result.take_profit < result.entry_price < result.stop_loss

    def test_no_uptrend_confirmation_does_not_trigger(self):
        strategy = _stubbed_strategy(UP_ZONE, TrendDirection.SIDEWAYS, MarketStructure.BOS)
        df = _df(rows=11, pullback_close=UP_ZONE.level_236, pullback_at=8, entry_close=2010.0)

        result = strategy._shallow_pullback_continuation(df, idx=10)

        assert result.triggered is False

    def test_no_pullback_to_236_does_not_trigger(self):
        strategy = _stubbed_strategy(UP_ZONE, TrendDirection.UPTREND, MarketStructure.BOS)
        df = _df(rows=11, pullback_close=2000.0, pullback_at=8, entry_close=2010.0)  # never near 23.6%

        result = strategy._shallow_pullback_continuation(df, idx=10)

        assert result.triggered is False

    def test_no_structure_confirmation_does_not_trigger(self):
        strategy = _stubbed_strategy(UP_ZONE, TrendDirection.UPTREND, MarketStructure.NONE)
        df = _df(rows=11, pullback_close=UP_ZONE.level_236, pullback_at=8, entry_close=2010.0)

        result = strategy._shallow_pullback_continuation(df, idx=10)

        assert result.triggered is False

    def test_pullback_outside_the_window_does_not_trigger(self):
        strategy = _stubbed_strategy(UP_ZONE, TrendDirection.UPTREND, MarketStructure.BOS, pullback_window=3)
        df = _df(rows=11, pullback_close=UP_ZONE.level_236, pullback_at=2, entry_close=2010.0)  # too far back

        result = strategy._shallow_pullback_continuation(df, idx=10)

        assert result.triggered is False

    def test_pullback_that_went_too_deep_does_not_trigger(self):
        """If price traded through the 38.2% level anywhere in the pullback
        window, this isn't a SHALLOW pullback anymore — should not trigger
        even though it touched 23.6% at some point too."""
        strategy = _stubbed_strategy(UP_ZONE, TrendDirection.UPTREND, MarketStructure.BOS)
        # UP_ZONE.level_382 = 2023.6; force every candle's low down to 2010,
        # well below that, simulating a deep move within the window.
        df = _df(rows=11, pullback_close=UP_ZONE.level_236, pullback_at=8, entry_close=2010.0)
        df['low'] = 2010.0  # every candle's low sits below level_382 -> "went too deep"

        result = strategy._shallow_pullback_continuation(df, idx=10)

        assert result.triggered is False

"""
Tests for GoldStrategy._volatility_squeeze_breakout (see
docs/superpowers/specs/2026-09-08-volatility-squeeze-breakout-design.md).

The rule: detect a genuine ATR contraction (not just narrow closes) over
`squeeze_lookback` candles immediately BEFORE the current candle, then check
whether the current candle's close breaks decisively outside the price
range those candles traded in. The squeeze/range window deliberately
excludes the current candle so a big breakout candle can't inflate its own
"was this a squeeze" check.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from signals.gold_strategy import GoldStrategy
from signals.realtime_generator import SignalValidator  # noqa: F401 (import sanity)
from backtesting.engine import TradeDirection
from analysis.technical import TechnicalAnalysis


TEST_CONFIG = {
    'atr_period': 5,
    'squeeze_lookback': 10,
    'squeeze_atr_ratio': 0.7,
    'breakout_buffer_atr': 0.2,
    'sl_buffer_atr': 0.3,
    'default_rr_ratio': 2.0,
}


def _build_df(direction: str, breakout: bool, contracted: bool, fakeout: bool = False) -> pd.DataFrame:
    """
    Build a synthetic OHLCV series: a volatile lead-in, then a consolidation
    window, then one final candle that either breaks out of that
    consolidation or doesn't.

    - direction: 'up' or 'down' — which way the (attempted) breakout goes.
    - breakout: whether the final candle actually closes outside the range.
    - contracted: whether the consolidation window has genuinely low true
      range (a real squeeze) or merely narrow closes with wide wicks (looks
      boxed in by closing price alone, but true range/ATR stays elevated).
    - fakeout: append one more candle after the breakout that reverses
      hard in the opposite direction (tests the reversal-pattern veto).
    """
    n_lead_in = 15
    n_consolidation = TEST_CONFIG['squeeze_lookback']
    base = 2000.0

    rows = []
    # Volatile lead-in so ATR's rolling window has real history to average.
    rng = np.random.RandomState(7)
    for i in range(n_lead_in):
        o = base + rng.uniform(-8, 8)
        c = base + rng.uniform(-8, 8)
        h = max(o, c) + rng.uniform(2, 5)
        l = min(o, c) - rng.uniform(2, 5)
        rows.append((o, h, l, c))

    # Consolidation window immediately before the candle under test.
    for i in range(n_consolidation):
        center = base
        if contracted:
            o = center + rng.uniform(-0.2, 0.2)
            c = center + rng.uniform(-0.2, 0.2)
            h = max(o, c) + 0.1
            l = min(o, c) - 0.1
        else:
            # Narrow closes, but wide intrabar wicks — true range stays high
            # even though the closing price looks range-bound.
            o = center + rng.uniform(-0.2, 0.2)
            c = center + rng.uniform(-0.2, 0.2)
            h = max(o, c) + rng.uniform(4, 6)
            l = min(o, c) - rng.uniform(4, 6)
        rows.append((o, h, l, c))

    # The candle under test.
    range_high = max(r[1] for r in rows[-n_consolidation:])
    range_low = min(r[2] for r in rows[-n_consolidation:])
    if breakout:
        if direction == 'up':
            o = range_high
            c = range_high + 6.0
            h = c + 0.5
            l = o - 0.2
        else:
            o = range_low
            c = range_low - 6.0
            h = o + 0.2
            l = c - 0.5
    else:
        # Stays inside the established range.
        o = c = base
        h = base + 0.3
        l = base - 0.3
    rows.append((o, h, l, c))

    if fakeout:
        # A strong candle immediately reversing the breakout direction.
        if direction == 'up':
            o = c + 0.5
            c2 = o - 8.0
            h2 = o + 0.3
            l2 = c2 - 0.3
            rows.append((o, h2, l2, c2))
        else:
            o = c - 0.5
            c2 = o + 8.0
            h2 = c2 + 0.3
            l2 = o - 0.3
            rows.append((o, h2, l2, c2))

    dates = pd.date_range(start='2024-01-01', periods=len(rows), freq='1h')
    df = pd.DataFrame(rows, columns=['open', 'high', 'low', 'close'], index=dates)
    df['volume'] = 1000
    return df


def _evaluate(df: pd.DataFrame):
    strategy = GoldStrategy(config=TEST_CONFIG)
    idx = len(df) - 1
    strategy.df = df
    strategy.ta = TechnicalAnalysis(df.iloc[:idx + 1])
    return strategy._volatility_squeeze_breakout(df, idx)


class TestVolatilitySqueezeBreakout:
    def test_genuine_squeeze_then_upward_breakout_triggers_long(self):
        df = _build_df(direction='up', breakout=True, contracted=True)
        result = _evaluate(df)

        assert result.triggered is True
        assert result.direction == TradeDirection.LONG
        assert result.stop_loss < result.entry_price < result.take_profit

    def test_genuine_squeeze_then_downward_breakout_triggers_short(self):
        df = _build_df(direction='down', breakout=True, contracted=True)
        result = _evaluate(df)

        assert result.triggered is True
        assert result.direction == TradeDirection.SHORT
        assert result.take_profit < result.entry_price < result.stop_loss

    def test_squeeze_with_no_breakout_does_not_trigger(self):
        df = _build_df(direction='up', breakout=False, contracted=True)
        result = _evaluate(df)

        assert result.triggered is False

    def test_narrow_closes_without_real_atr_contraction_does_not_trigger(self):
        """Wide wicks keep true range/ATR elevated even though closes look boxed in —
        the squeeze check must be ATR-based, not just a closing-price range check."""
        df = _build_df(direction='up', breakout=True, contracted=False)
        result = _evaluate(df)

        assert result.triggered is False

    def test_opposing_reversal_pattern_on_the_breakout_candle_is_vetoed(self):
        """An upward breakout that itself carries a bearish reversal-candle
        shape (e.g. a bearish engulfing) is more likely a fakeout than a
        real regime change — same veto every other rule already applies via
        _detect_reversal_pattern."""
        df = _build_df(direction='up', breakout=True, contracted=True)
        result_without_veto = _evaluate(df)
        assert result_without_veto.triggered is True  # sanity: would trigger but for the veto

        strategy = GoldStrategy(config=TEST_CONFIG)
        idx = len(df) - 1
        strategy.df = df
        strategy.ta = TechnicalAnalysis(df.iloc[:idx + 1])
        strategy._detect_reversal_pattern = lambda df, idx: "bearish_engulfing"

        result = strategy._volatility_squeeze_breakout(df, idx)

        assert result.triggered is False

    def test_stop_loss_sits_at_the_broken_range_boundary(self):
        df = _build_df(direction='up', breakout=True, contracted=True)
        idx = len(df) - 1
        range_low = df.iloc[idx - TEST_CONFIG['squeeze_lookback']:idx]['low'].min()

        result = _evaluate(df)

        # SL should be the range low, buffered further down by ATR — not an
        # arbitrary distance from entry.
        assert result.stop_loss < range_low

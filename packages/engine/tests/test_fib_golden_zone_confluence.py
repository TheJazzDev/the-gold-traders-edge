"""
Tests for GoldStrategy._detect_liquidity_grab and
_fib_golden_zone_confluence — a faithful implementation of the user's own
XAU/USD trading plan: entry at 61.8% Fibonacci retracement, ONLY if it
aligns with an Order Block, follows a liquidity grab, AND confirms a
retest of broken structure (S/R flip). SL slightly beyond the 78.6% level,
TP at the 38.2% level (not RR-multiple based, unlike every other rule).
See docs/superpowers/specs/strategy-ledger.md.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from signals.gold_strategy import GoldStrategy, FibZone, MarketStructure
from backtesting.engine import TradeDirection


class TestDetectLiquidityGrab:
    @pytest.fixture
    def strategy(self):
        return GoldStrategy()

    def test_wick_below_prior_low_closing_back_above_is_bullish_grab(self, strategy):
        dates = pd.date_range(start='2024-01-01', periods=12, freq='1h')
        rows = [(2000, 2002, 1998, 2000)] * 10  # prior_low = 1998
        rows.append((2000, 2001, 1990, 1999))   # wicks to 1990, closes at 1999 (> 1998)
        rows.append((0, 0, 0, 0))  # placeholder to keep idx math simple below
        df = pd.DataFrame(rows, columns=['open', 'high', 'low', 'close'], index=dates)

        result = strategy._detect_liquidity_grab(df, idx=10, lookback=10)

        assert result == 'bullish'

    def test_wick_above_prior_high_closing_back_below_is_bearish_grab(self, strategy):
        dates = pd.date_range(start='2024-01-01', periods=12, freq='1h')
        rows = [(2000, 2002, 1998, 2000)] * 10  # prior_high = 2002
        rows.append((2000, 2010, 1999, 2001))   # wicks to 2010, closes at 2001 (< 2002)
        rows.append((0, 0, 0, 0))
        df = pd.DataFrame(rows, columns=['open', 'high', 'low', 'close'], index=dates)

        result = strategy._detect_liquidity_grab(df, idx=10, lookback=10)

        assert result == 'bearish'

    def test_no_wick_beyond_prior_range_is_no_grab(self, strategy):
        dates = pd.date_range(start='2024-01-01', periods=11, freq='1h')
        rows = [(2000, 2002, 1998, 2000)] * 11
        df = pd.DataFrame(rows, columns=['open', 'high', 'low', 'close'], index=dates)

        result = strategy._detect_liquidity_grab(df, idx=10, lookback=10)

        assert result is None

    def test_wick_beyond_range_but_close_also_beyond_it_is_not_a_grab(self, strategy):
        """A close that stays outside the prior range is a genuine breakout,
        not a stop-hunt-and-reverse."""
        dates = pd.date_range(start='2024-01-01', periods=12, freq='1h')
        rows = [(2000, 2002, 1998, 2000)] * 10
        rows.append((2000, 2001, 1990, 1993))  # wicks to 1990 AND closes at 1993 (still < 1998)
        rows.append((0, 0, 0, 0))
        df = pd.DataFrame(rows, columns=['open', 'high', 'low', 'close'], index=dates)

        result = strategy._detect_liquidity_grab(df, idx=10, lookback=10)

        assert result is None


def _stubbed_strategy(fib_zone, order_block, liquidity_grab, structure, reversal_pattern=None):
    strategy = GoldStrategy()
    fake_ta = MagicMock()
    fake_ta.calculate_atr.return_value = pd.Series([5.0])
    strategy.ta = fake_ta
    strategy.df = pd.DataFrame()  # unused directly; rule reads via df.iloc[idx] passed in
    strategy._get_fib_zones = lambda df, idx: fib_zone
    strategy._detect_order_block = lambda df, idx: order_block
    strategy._detect_liquidity_grab = lambda df, idx, lookback=10: liquidity_grab
    strategy._detect_market_structure = lambda df, idx, lookback=10: structure
    strategy._detect_reversal_pattern = lambda df, idx: reversal_pattern
    return strategy


# NOTE: standard Fibonacci spacing (38.2%/61.8%/78.6%) gives a raw
# reward:risk around 1.4 (the 38.2%->61.8% gap is ~0.236 of the swing range,
# the 61.8%->78.6% gap only ~0.168) — inherently below this rule's own 1:2
# minimum. These fixtures use non-standard level gaps specifically to clear
# that bar and exercise the "everything aligns" happy path; see
# test_resulting_rr_below_minimum_does_not_trigger for the standard-spacing
# (realistic) case, which correctly does NOT trigger.
UP_ZONE = FibZone(
    swing_low=1900.0, swing_high=2100.0,
    level_236=2052.8, level_382=2000.0, level_500=1990.0,
    level_618=1980.0, level_786=1975.0,
    direction='up',
)

DOWN_ZONE = FibZone(
    swing_low=1900.0, swing_high=2100.0,
    level_236=1947.2, level_382=2000.0, level_500=2010.0,
    level_618=2020.0, level_786=2025.0,
    direction='down',
)


def _df_with_close_at(price: float, rows: int = 1) -> pd.DataFrame:
    """`rows` candles, all identical, with the LAST one closing at `price`."""
    dates = pd.date_range(start='2024-01-01', periods=rows, freq='1h')
    return pd.DataFrame(
        {'open': [price] * rows, 'high': [price + 1] * rows, 'low': [price - 1] * rows, 'close': [price] * rows},
        index=dates,
    )


class TestFibGoldenZoneConfluence:
    def test_all_four_confluences_present_triggers_long(self):
        strategy = _stubbed_strategy(
            fib_zone=UP_ZONE,
            order_block={'type': 'bullish', 'high': 1980, 'low': 1970, 'index': 0},
            liquidity_grab='bullish',
            structure=MarketStructure.BOS,
        )
        df = _df_with_close_at(UP_ZONE.level_618)  # near 61.8%

        result = strategy._fib_golden_zone_confluence(df, idx=0)

        assert result.triggered is True
        assert result.direction == TradeDirection.LONG
        assert result.take_profit == pytest.approx(UP_ZONE.level_382)
        assert result.stop_loss < result.entry_price

    def test_all_four_confluences_present_triggers_short(self):
        strategy = _stubbed_strategy(
            fib_zone=DOWN_ZONE,
            order_block={'type': 'bearish', 'high': 2030, 'low': 2020, 'index': 0},
            liquidity_grab='bearish',
            structure=MarketStructure.BOS,
        )
        df = _df_with_close_at(DOWN_ZONE.level_618)

        result = strategy._fib_golden_zone_confluence(df, idx=0)

        assert result.triggered is True
        assert result.direction == TradeDirection.SHORT
        assert result.take_profit == pytest.approx(DOWN_ZONE.level_382)
        assert result.stop_loss > result.entry_price

    def test_missing_order_block_does_not_trigger(self):
        strategy = _stubbed_strategy(
            fib_zone=UP_ZONE, order_block=None, liquidity_grab='bullish', structure=MarketStructure.BOS,
        )
        df = _df_with_close_at(UP_ZONE.level_618)

        result = strategy._fib_golden_zone_confluence(df, idx=0)

        assert result.triggered is False

    def test_missing_liquidity_grab_does_not_trigger(self):
        strategy = _stubbed_strategy(
            fib_zone=UP_ZONE,
            order_block={'type': 'bullish', 'high': 1980, 'low': 1970, 'index': 0},
            liquidity_grab=None,
            structure=MarketStructure.BOS,
        )
        df = _df_with_close_at(UP_ZONE.level_618)

        result = strategy._fib_golden_zone_confluence(df, idx=0)

        assert result.triggered is False

    def test_missing_structure_confirmation_does_not_trigger(self):
        strategy = _stubbed_strategy(
            fib_zone=UP_ZONE,
            order_block={'type': 'bullish', 'high': 1980, 'low': 1970, 'index': 0},
            liquidity_grab='bullish',
            structure=MarketStructure.NONE,
        )
        df = _df_with_close_at(UP_ZONE.level_618)

        result = strategy._fib_golden_zone_confluence(df, idx=0)

        assert result.triggered is False

    def test_price_not_near_618_level_does_not_trigger(self):
        strategy = _stubbed_strategy(
            fib_zone=UP_ZONE,
            order_block={'type': 'bullish', 'high': 1980, 'low': 1970, 'index': 0},
            liquidity_grab='bullish',
            structure=MarketStructure.BOS,
        )
        df = _df_with_close_at(UP_ZONE.swing_high)  # nowhere near 61.8%

        result = strategy._fib_golden_zone_confluence(df, idx=0)

        assert result.triggered is False

    def test_wrong_direction_order_block_does_not_trigger(self):
        """A bearish OB in an 'up' (LONG-bias) zone isn't real confluence."""
        strategy = _stubbed_strategy(
            fib_zone=UP_ZONE,
            order_block={'type': 'bearish', 'high': 1980, 'low': 1970, 'index': 0},
            liquidity_grab='bullish',
            structure=MarketStructure.BOS,
        )
        df = _df_with_close_at(UP_ZONE.level_618)

        result = strategy._fib_golden_zone_confluence(df, idx=0)

        assert result.triggered is False

    def test_grab_and_structure_within_the_confluence_window_still_triggers(self):
        """Regression: requiring liquidity grab + structure retest on the
        EXACT same candle as the 61.8% touch collapsed to ~0.15% of real
        candles (see strategy-ledger.md diagnostic) — they only need to
        have happened within the last `confluence_window` candles."""
        strategy = GoldStrategy(config={'confluence_window': 5})
        fake_ta = MagicMock()
        fake_ta.calculate_atr.return_value = pd.Series([5.0])
        strategy.ta = fake_ta
        strategy._get_fib_zones = lambda df, idx: UP_ZONE
        strategy._detect_order_block = lambda df, idx: {'type': 'bullish', 'high': 1980, 'low': 1970, 'index': 0}
        # Only true 3 candles back, not at idx itself.
        strategy._detect_liquidity_grab = lambda df, idx, lookback=10: 'bullish' if idx == 7 else None
        strategy._detect_market_structure = lambda df, idx, lookback=10: (
            MarketStructure.BOS if idx == 8 else MarketStructure.NONE
        )
        df = _df_with_close_at(UP_ZONE.level_618, rows=11)

        result = strategy._fib_golden_zone_confluence(df, idx=10)  # confluence_window pinned to 5 above

        assert result.triggered is True

    def test_grab_outside_the_confluence_window_does_not_trigger(self):
        strategy = GoldStrategy(config={'confluence_window': 5})
        fake_ta = MagicMock()
        fake_ta.calculate_atr.return_value = pd.Series([5.0])
        strategy.ta = fake_ta
        strategy._get_fib_zones = lambda df, idx: UP_ZONE
        strategy._detect_order_block = lambda df, idx: {'type': 'bullish', 'high': 1980, 'low': 1970, 'index': 0}
        strategy._detect_liquidity_grab = lambda df, idx, lookback=10: 'bullish' if idx == 2 else None  # too far back
        strategy._detect_market_structure = lambda df, idx, lookback=10: MarketStructure.BOS
        df = _df_with_close_at(UP_ZONE.level_618, rows=11)

        result = strategy._fib_golden_zone_confluence(df, idx=10)

        assert result.triggered is False

    def test_resulting_rr_below_minimum_does_not_trigger(self):
        """User's plan rule #6: minimum 1:2 R:R. Since TP is fixed at the
        38.2% level (not RR-derived), a zone shaped so the 38.2%..61.8%
        distance is less than 2x the 61.8%..78.6% distance must be rejected
        even though every other confluence condition is met."""
        skewed_zone = FibZone(
            swing_low=1900.0, swing_high=2100.0,
            level_236=2052.8, level_382=2010.0,  # unusually close to level_618
            level_500=2000.0, level_618=1976.4, level_786=1942.8,
            direction='up',
        )
        strategy = _stubbed_strategy(
            fib_zone=skewed_zone,
            order_block={'type': 'bullish', 'high': 1980, 'low': 1970, 'index': 0},
            liquidity_grab='bullish',
            structure=MarketStructure.BOS,
        )
        df = _df_with_close_at(skewed_zone.level_618)

        result = strategy._fib_golden_zone_confluence(df, idx=0)

        assert result.triggered is False

"""
Tests for ForexSessionStrategy._asian_range_london_breakout.

Hypothesis: GBP (and, more weakly, EUR) liquidity concentrates in the
London session, so price consolidates during the quiet Asian session
(00:00-07:00 UTC) and breaks out decisively at London open (07:00 UTC).
Validated on GBPUSD and EURUSD 1H via a real 70/30 train/test split before
this was implemented — see
docs/superpowers/specs/2026-09-09-gbpusd-asian-range-breakout-design.md.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from signals.forex_session_strategy import ForexSessionStrategy
from backtesting.engine import TradeDirection


TEST_CONFIG = {
    'asian_hours_start': 0,
    'asian_hours_end': 7,
    'entry_hour': 7,
    'lookback_candles': 12,
    'min_asian_candles': 5,
    'atr_period': 5,
    'breakout_buffer_atr': 0.1,
    'sl_buffer_atr': 0.3,
    'default_rr_ratio': 2.0,
}


def _build_session_df(entry_close: float, asian_high: float = 1.2010, asian_low: float = 1.1990,
                       lead_in_hours: int = 24, entry_hour: int = 7) -> pd.DataFrame:
    """
    Builds an hourly UTC-indexed df: `lead_in_hours` of volatile lead-in
    (so ATR has real history), then a tight Asian session (hours 0-6, high=
    asian_high, low=asian_low), then the entry candle at `entry_hour`
    closing at `entry_close`. Starts at a fixed date whose weekday doesn't
    matter — only .hour is used by the strategy.
    """
    dates = pd.date_range(start='2024-01-01 00:00:00', periods=lead_in_hours, freq='1h')
    rows = []
    for i in range(lead_in_hours):
        o = 1.2000 + (0.001 if i % 2 == 0 else -0.001)
        c = 1.2000 + (-0.001 if i % 2 == 0 else 0.001)
        h = max(o, c) + 0.003
        l = min(o, c) - 0.003
        rows.append((o, h, l, c))

    # Asian session: hours 0-6 of the "current" day, tight range.
    asian_dates = pd.date_range(start=dates[-1] + pd.Timedelta(hours=1), periods=7, freq='1h')
    for i in range(7):
        o = c = (asian_high + asian_low) / 2
        rows.append((o, asian_high, asian_low, c))

    all_dates = list(dates) + list(asian_dates)

    # Entry candle at entry_hour (immediately after the 7 Asian candles,
    # i.e. hour 7 given Asian session is hours 0-6).
    entry_date = asian_dates[-1] + pd.Timedelta(hours=1)
    all_dates.append(entry_date)
    rows.append((entry_close, entry_close + 0.0005, entry_close - 0.0005, entry_close))

    assert entry_date.hour == entry_hour, f"fixture bug: entry candle hour is {entry_date.hour}, expected {entry_hour}"

    df = pd.DataFrame(rows, columns=['open', 'high', 'low', 'close'], index=pd.DatetimeIndex(all_dates))
    return df


def _stubbed_strategy(atr=0.0005):
    strategy = ForexSessionStrategy(config=TEST_CONFIG)
    fake_ta = MagicMock()
    fake_ta.calculate_atr.return_value = pd.Series([atr])
    strategy.ta = fake_ta
    return strategy


class TestAsianRangeLondonBreakout:
    def test_breakout_above_asian_high_triggers_long(self):
        strategy = _stubbed_strategy()
        df = _build_session_df(entry_close=1.2030)  # well above asian_high=1.2010
        idx = len(df) - 1

        result = strategy._asian_range_london_breakout(df, idx)

        assert result.triggered is True
        assert result.direction == TradeDirection.LONG
        assert result.stop_loss < result.entry_price < result.take_profit

    def test_breakout_below_asian_low_triggers_short(self):
        strategy = _stubbed_strategy()
        df = _build_session_df(entry_close=1.1970)  # well below asian_low=1.1990
        idx = len(df) - 1

        result = strategy._asian_range_london_breakout(df, idx)

        assert result.triggered is True
        assert result.direction == TradeDirection.SHORT
        assert result.take_profit < result.entry_price < result.stop_loss

    def test_price_still_inside_asian_range_does_not_trigger(self):
        strategy = _stubbed_strategy()
        df = _build_session_df(entry_close=1.2000)  # inside [1.1990, 1.2010]
        idx = len(df) - 1

        result = strategy._asian_range_london_breakout(df, idx)

        assert result.triggered is False

    def test_marginal_break_within_buffer_does_not_trigger(self):
        """A close that pokes just past the range but not past the
        ATR-scaled buffer isn't a genuine breakout."""
        strategy = _stubbed_strategy(atr=0.01)  # large ATR -> large buffer
        df = _build_session_df(entry_close=1.2011)  # barely above asian_high=1.2010
        idx = len(df) - 1

        result = strategy._asian_range_london_breakout(df, idx)

        assert result.triggered is False

    def test_wrong_hour_does_not_trigger_even_with_a_real_breakout(self):
        strategy = _stubbed_strategy()
        df = _build_session_df(entry_close=1.2030)
        idx = len(df) - 2  # the candle before the entry-hour candle

        result = strategy._asian_range_london_breakout(df, idx)

        assert result.triggered is False

    def test_insufficient_asian_candles_does_not_trigger(self):
        """A weekend/holiday gap leaving too few Asian-hour candles in the
        lookback window must not produce a signal off an untrustworthy range."""
        strategy = _stubbed_strategy()
        df = _build_session_df(entry_close=1.2030)
        # Shrink the lookback window so it no longer reaches back far enough
        # to see the required minimum of Asian candles.
        strategy.config['lookback_candles'] = 3
        idx = len(df) - 1

        result = strategy._asian_range_london_breakout(df, idx)

        assert result.triggered is False

    def test_notes_and_confidence_are_set_on_trigger(self):
        strategy = _stubbed_strategy()
        df = _build_session_df(entry_close=1.2030)
        idx = len(df) - 1

        result = strategy._asian_range_london_breakout(df, idx)

        assert result.confidence > 0
        assert "asian" in result.notes.lower() or "london" in result.notes.lower()


class TestForexSessionStrategyEvaluate:
    def test_evaluate_returns_none_for_insufficient_data(self):
        strategy = ForexSessionStrategy(config=TEST_CONFIG)
        df = _build_session_df(entry_close=1.2030)
        result = strategy.evaluate(df, current_idx=2)  # far below the lookback+atr gate
        assert result is None

    def test_disabling_the_rule_suppresses_signals(self):
        strategy = ForexSessionStrategy(config=TEST_CONFIG)
        strategy.set_rule_enabled('asian_range_london_breakout', False)
        df = _build_session_df(entry_close=1.2030)
        idx = len(df) - 1

        result = strategy.evaluate(df, idx)

        assert result is None

    def test_evaluate_returns_a_signal_for_a_real_breakout(self):
        strategy = ForexSessionStrategy(config=TEST_CONFIG)
        df = _build_session_df(entry_close=1.2030)
        idx = len(df) - 1

        result = strategy.evaluate(df, idx)

        assert result is not None
        assert result.direction == TradeDirection.LONG
        assert result.signal_name == "Asian Range London Breakout"

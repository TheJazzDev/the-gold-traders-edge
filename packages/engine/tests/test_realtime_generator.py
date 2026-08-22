"""Tests for RealtimeSignalGenerator."""
import sys
from pathlib import Path
import logging

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from signals.gold_strategy import GoldStrategy
from signals.realtime_generator import RealtimeSignalGenerator, SignalValidator


class FakeDataFeed:
    """Minimal stand-in for RealtimeDataFeed, just enough to construct a generator."""
    symbol = "XAUUSD"
    timeframe = "1h"
    is_connected = True

    def connect(self):
        return True

    def disconnect(self):
        return True

    def get_latest_candles(self, count):
        import pandas as pd
        return pd.DataFrame()  # Empty DataFrame stops iteration

    def wait_for_candle_close(self, check_interval):
        raise StopIteration  # Exit loop immediately


class TestStrategyLogLine:
    def test_start_logs_actual_enabled_rules(self, caplog):
        strategy = GoldStrategy()
        for name in strategy.rules_enabled:
            strategy.rules_enabled[name] = False
        strategy.rules_enabled['london_session_breakout'] = True

        generator = RealtimeSignalGenerator(
            data_feed=FakeDataFeed(),
            strategy=strategy,
            validator=SignalValidator(),
        )

        with caplog.at_level(logging.INFO):
            generator.start(max_iterations=0)

        messages = [r.message for r in caplog.records]
        assert any("london_session_breakout" in m for m in messages), messages
        assert not any(m == "Strategy: Momentum Equilibrium" for m in messages), messages


import pandas as pd
from unittest.mock import MagicMock


class FakeDataFeedWithCandles:
    symbol = "XAUUSD"
    timeframe = "1h"
    is_connected = True

    def __init__(self, df):
        self._df = df

    def connect(self):
        return True

    def get_latest_candles(self, count):
        return self._df

    def wait_for_candle_close(self, check_interval=60):
        pass


class TestOutcomeTrackerWiring:
    def test_run_once_calls_outcome_tracker_with_latest_candle(self):
        dates = pd.date_range(start='2026-01-01', periods=5, freq='1h')
        df = pd.DataFrame({
            'open': [2000, 2001, 2002, 2003, 2004],
            'high': [2005, 2006, 2007, 2008, 2009],
            'low': [1995, 1996, 1997, 1998, 1999],
            'close': [2001, 2002, 2003, 2004, 2005],
        }, index=dates)

        strategy = GoldStrategy()
        for name in strategy.rules_enabled:
            strategy.rules_enabled[name] = False  # no new signals this test

        mock_tracker = MagicMock()
        generator = RealtimeSignalGenerator(
            data_feed=FakeDataFeedWithCandles(df),
            strategy=strategy,
            validator=SignalValidator(),
            outcome_tracker=mock_tracker,
        )

        generator.run_once()

        mock_tracker.check_candle.assert_called_once()
        call_args = mock_tracker.check_candle.call_args
        assert call_args[0][1] == dates[-1]  # candle_time

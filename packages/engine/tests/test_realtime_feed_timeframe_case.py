"""Regression coverage for the timeframe case-sensitivity bug in realtime_feed.py.

RealtimeDataFeed subclasses looked up self.timeframe (passed lowercase by
run_multi_timeframe_service.py, e.g. '1h') against dicts keyed with
uppercase strings ('1H', '4H', '1D'). Every lookup silently missed and fell
back to its 4-hour default, so a service configured for '1h' actually
fetched 4h Yahoo Finance candles and polled for candle closes on a 4-hour
cadence instead of hourly.
"""
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.realtime_feed import YahooFinanceDataFeed


def _connected_feed(timeframe):
    feed = YahooFinanceDataFeed(symbol="XAUUSD", timeframe=timeframe)
    feed.is_connected = True
    feed.yf_ticker = MagicMock()
    feed.yf_ticker.history.return_value = pd.DataFrame({
        "Open": [1.0], "High": [1.0], "Low": [1.0], "Close": [1.0], "Volume": [1.0],
    })
    return feed


class TestGetTimeframeMinutesCaseInsensitive:
    def test_lowercase_1h_returns_60_not_240(self):
        feed = YahooFinanceDataFeed(symbol="XAUUSD", timeframe="1h")
        assert feed.get_timeframe_minutes() == 60

    def test_uppercase_1h_still_returns_60(self):
        feed = YahooFinanceDataFeed(symbol="XAUUSD", timeframe="1H")
        assert feed.get_timeframe_minutes() == 60


class TestGetLatestCandlesUsesCorrectInterval:
    def test_lowercase_1h_requests_1h_interval_not_4h(self):
        feed = _connected_feed("1h")
        feed.get_latest_candles(count=10)
        _, kwargs = feed.yf_ticker.history.call_args
        assert kwargs["interval"] == "1h"

    def test_lowercase_15m_requests_15m_interval(self):
        feed = _connected_feed("15m")
        feed.get_latest_candles(count=10)
        _, kwargs = feed.yf_ticker.history.call_args
        assert kwargs["interval"] == "15m"


class TestWaitForCandleCloseUsesCorrectCadence:
    def test_lowercase_1h_schedules_next_close_one_hour_out(self, capsys):
        feed = YahooFinanceDataFeed(symbol="XAUUSD", timeframe="1h")
        fixed_now = datetime(2026, 8, 26, 12, 0, 25)
        past_close = datetime(2026, 8, 26, 13, 0, 1)

        with patch("src.data.realtime_feed.datetime") as mock_dt, \
             patch("src.data.realtime_feed.time.sleep"):
            # First call computes next_close; second (the while-loop guard)
            # is already past it, so the wait exits without looping again.
            mock_dt.now.side_effect = [fixed_now, past_close]

            feed.wait_for_candle_close(check_interval=1)

        # A 1h timeframe polled at 12:00 must target the 13:00 boundary,
        # not the old buggy 4h-aligned 16:00 boundary.
        output = capsys.readouterr().out
        assert "Next 1h candle closes at 2026-08-26 13:00:00 UTC" in output

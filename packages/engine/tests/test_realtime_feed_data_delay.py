"""Regression coverage for Yahoo's delayed gold feed.

GC=F (COMEX gold futures) on Yahoo runs ~11 minutes behind real time
(measured 2026-10-02: latest 1m bar 13:26 at 13:36:55 UTC), while
EURUSD=X / GBPUSD=X lag under a minute. The worker evaluated ~20s after
the hour, so every live gold candle was missing its last ~10 minutes: live
gold entries were off by up to ~20 points and four live gold signals
(09-08 16:00, 09-23 17:00, 09-24 01:00, 09-25 06:00) don't fire at all on
the complete candles the backtest scores.

Fix: each Yahoo ticker carries a publish delay. A candle only counts as
closed once its period plus that delay has elapsed, and the worker waits
for the same moment before evaluating.
"""
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.realtime_feed import YahooFinanceDataFeed


def _hourly_frame(last_hour: int, rows: int = 6) -> pd.DataFrame:
    index = pd.date_range(end=datetime(2026, 9, 24, last_hour, 0, 0), periods=rows, freq="h")
    return pd.DataFrame(
        {"Open": [1.0] * rows, "High": [1.0] * rows, "Low": [1.0] * rows,
         "Close": [1.0] * rows, "Volume": [0.0] * rows},
        index=index,
    )


def _connected_feed(symbol: str, df: pd.DataFrame) -> YahooFinanceDataFeed:
    feed = YahooFinanceDataFeed(symbol=symbol, timeframe="1h")
    feed.is_connected = True
    feed.yf_ticker = MagicMock()
    feed.yf_ticker.history.return_value = df
    return feed


def _fetch_at(feed, now: datetime):
    with patch("src.data.realtime_feed.datetime") as mock_dt:
        mock_dt.now.return_value = now
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        return feed.get_latest_candles(count=200)


class TestPublishDelayPerTicker:
    def test_gold_futures_carry_a_publish_delay(self):
        assert YahooFinanceDataFeed(symbol="XAUUSD", timeframe="1h").data_delay_minutes >= 12

    def test_forex_has_no_publish_delay(self):
        assert YahooFinanceDataFeed(symbol="EURUSD", timeframe="1h").data_delay_minutes == 0
        assert YahooFinanceDataFeed(symbol="GBPUSD", timeframe="1h").data_delay_minutes == 0


class TestDelayedCandleIsNotClosedYet:
    def test_gold_candle_is_dropped_until_the_delay_has_passed(self):
        # 17:00 bar ends at 18:00, but at 18:00:20 Yahoo only has GC=F data
        # through ~17:49 — that's what live evaluated on 09-24.
        feed = _connected_feed("XAUUSD", _hourly_frame(last_hour=17))

        df = _fetch_at(feed, now=datetime(2026, 9, 24, 18, 0, 20))

        assert df.index[-1] == datetime(2026, 9, 24, 16, 0, 0)

    def test_gold_candle_is_kept_once_the_delay_has_passed(self):
        feed = _connected_feed("XAUUSD", _hourly_frame(last_hour=17))

        df = _fetch_at(feed, now=datetime(2026, 9, 24, 18, 16, 0))

        assert df.index[-1] == datetime(2026, 9, 24, 17, 0, 0)

    def test_forex_candle_is_kept_right_after_the_hour(self):
        feed = _connected_feed("EURUSD", _hourly_frame(last_hour=17))

        df = _fetch_at(feed, now=datetime(2026, 9, 24, 18, 0, 20))

        assert df.index[-1] == datetime(2026, 9, 24, 17, 0, 0)


class TestNextEvaluationTime:
    def test_gold_waits_for_the_delay_after_the_hour(self):
        feed = YahooFinanceDataFeed(symbol="XAUUSD", timeframe="1h")
        delay = feed.data_delay_minutes

        assert feed.next_evaluation_time(datetime(2026, 9, 24, 17, 30)) == \
            datetime(2026, 9, 24, 18, delay)

    def test_gold_inside_the_delay_window_still_targets_this_hours_candle(self):
        # A restart at 18:05 must evaluate the 17:00 candle at 18:<delay>,
        # not skip it and wait for 19:<delay>.
        feed = YahooFinanceDataFeed(symbol="XAUUSD", timeframe="1h")
        delay = feed.data_delay_minutes

        assert feed.next_evaluation_time(datetime(2026, 9, 24, 18, 5)) == \
            datetime(2026, 9, 24, 18, delay)

    def test_forex_evaluates_on_the_hour(self):
        feed = YahooFinanceDataFeed(symbol="EURUSD", timeframe="1h")

        assert feed.next_evaluation_time(datetime(2026, 9, 24, 17, 30)) == datetime(2026, 9, 24, 18, 0)

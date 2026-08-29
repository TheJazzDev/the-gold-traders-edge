"""Regression coverage for the end-date exclusion bug in
YahooFinanceDataFeed.get_latest_candles().

get_latest_candles() computed `end=datetime.now().strftime("%Y-%m-%d")` — a
date-only string. Live-verified against Yahoo Finance (GC=F, 1h interval):
passing a date-only `end` excludes that entire calendar day from the
result, regardless of what time of day the call runs. Since `end_date` was
always "today", the live feed could never see today's candles — it was
permanently capped at yesterday's last close, and Yahoo's own backfill lag
for "yesterday" caused further multi-hour stalls on top of that. This is
why the deployed service processed ~65 hourly loop iterations with the
displayed "latest candle" barely advancing.

Fix: don't pass `end` at all — yfinance defaults to now when omitted,
which live-testing confirmed returns the actual latest available candle.
"""
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.realtime_feed import YahooFinanceDataFeed


def _connected_feed(timeframe="1h"):
    feed = YahooFinanceDataFeed(symbol="XAUUSD", timeframe=timeframe)
    feed.is_connected = True
    feed.yf_ticker = MagicMock()
    feed.yf_ticker.history.return_value = pd.DataFrame({
        "Open": [1.0], "High": [1.0], "Low": [1.0], "Close": [1.0], "Volume": [1.0],
    })
    return feed


class TestGetLatestCandlesDoesNotExcludeToday:
    def test_does_not_pass_an_end_date_that_would_exclude_today(self):
        feed = _connected_feed("1h")

        fixed_now = datetime(2026, 8, 27, 14, 0, 24)
        with patch("src.data.realtime_feed.datetime") as mock_dt:
            mock_dt.now.return_value = fixed_now
            # start_date subtraction still needs real timedelta arithmetic
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            feed.get_latest_candles(count=10)

        _, kwargs = feed.yf_ticker.history.call_args
        # A date-only end equal to "today" is exactly the value proven to
        # truncate all of today's candles from the Yahoo response.
        assert kwargs.get("end") is None, (
            f"end={kwargs.get('end')!r} would exclude every candle from "
            f"{fixed_now.strftime('%Y-%m-%d')} (see live-verified findings above)"
        )

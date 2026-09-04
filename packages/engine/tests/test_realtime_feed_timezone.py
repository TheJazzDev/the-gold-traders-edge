"""Regression coverage for the UTC mislabeling bug in
YahooFinanceDataFeed.get_latest_candles().

yfinance returns the candle index tz-aware in the exchange's local timezone
(America/New_York for GC=F), not UTC. Every downstream consumer — the
Telegram/console/logger signal formatters, and the DB's naive TIMESTAMP
column — treats candle timestamps as UTC without converting. Live-verified:
a 2026-09-04 08:00:00-04:00 (EDT) candle was reported to Telegram as
"08:00 UTC" while the DB stored the correctly-converted "12:00:00" UTC,
producing a 4-hour discrepancy between the notification and the record.

Fix: convert the index to UTC (and drop the tzinfo, matching the naive-UTC
convention the rest of the pipeline assumes) immediately after fetching from
yfinance, so every consumer sees a consistent, correctly-labeled value.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.realtime_feed import YahooFinanceDataFeed


def _connected_feed(timeframe="1h"):
    feed = YahooFinanceDataFeed(symbol="XAUUSD", timeframe=timeframe)
    feed.is_connected = True
    feed.yf_ticker = MagicMock()
    return feed


class TestGetLatestCandlesNormalizesToUtc:
    def test_converts_tz_aware_exchange_local_index_to_naive_utc(self):
        feed = _connected_feed("1h")

        # Mirrors what yfinance actually returns for GC=F: tz-aware in
        # America/New_York.
        local_index = pd.date_range(
            "2026-09-04 06:00:00", periods=3, freq="h", tz="America/New_York"
        )
        feed.yf_ticker.history.return_value = pd.DataFrame(
            {
                "Open": [1.0, 2.0, 3.0],
                "High": [1.0, 2.0, 3.0],
                "Low": [1.0, 2.0, 3.0],
                "Close": [1.0, 2.0, 3.0],
                "Volume": [1.0, 2.0, 3.0],
            },
            index=local_index,
        )

        result = feed.get_latest_candles(count=3)

        assert result.index.tz is None, (
            f"expected naive UTC index, got tz={result.index.tz!r}"
        )
        # 2026-09-04 08:00:00 EDT (-04:00) must become 12:00:00 UTC.
        assert result.index[-1] == pd.Timestamp("2026-09-04 12:00:00"), (
            f"expected last candle at 12:00:00 UTC, got {result.index[-1]}"
        )

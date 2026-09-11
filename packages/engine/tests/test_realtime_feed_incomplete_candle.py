"""Regression coverage for the in-progress-candle hazard in
YahooFinanceDataFeed.get_latest_candles().

get_latest_candles() returned yfinance's response verbatim, and yfinance
includes the *currently forming* bar as its last row (live-verified: at
10:24 UTC the last GBPUSD=X 1h row is the 10:00 bar, which has another
36 minutes to run). RealtimeSignalGenerator.generate_signal() evaluates
`df.iloc[-1]`, so whether the live worker sees a closed candle or a
seconds-old partial one depended entirely on a race: the worker wakes
~11s after the hour, and Yahoo happened not to have published the new bar
by then (logs: `08:00:11 - Candle close at 2026-09-11 07:00:00`).

That race is load-bearing for correctness. ForexSessionStrategy gates on
`df.index[idx].hour == entry_hour` (07:00 UTC, London open) and compares
that candle's *close* to the Asian range — exactly what the backtest
validated. If Yahoo ever publishes the new bar within those ~11 seconds,
the worker would silently evaluate a partial 08:00 candle instead, whose
"close" is a few seconds of price action: the 07:00 window would be
skipped entirely (hour == 8, never 7) and the strategy would go
permanently silent with no error anywhere.

Fix: drop any trailing candle whose period has not yet elapsed, so
`df.iloc[-1]` is always the most recent *closed* candle regardless of how
fast the upstream publishes.
"""
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.realtime_feed import YahooFinanceDataFeed


def _hourly_frame(last_hour: int, rows: int = 6) -> pd.DataFrame:
    """Hourly OHLCV bars ending at 2026-09-11 <last_hour>:00 UTC."""
    index = pd.date_range(
        end=datetime(2026, 9, 11, last_hour, 0, 0), periods=rows, freq="h"
    )
    return pd.DataFrame(
        {
            "Open": [1.35] * rows,
            "High": [1.36] * rows,
            "Low": [1.34] * rows,
            "Close": [1.35] * rows,
            "Volume": [0.0] * rows,
        },
        index=index,
    )


def _connected_feed(df: pd.DataFrame) -> YahooFinanceDataFeed:
    feed = YahooFinanceDataFeed(symbol="GBPUSD", timeframe="1h")
    feed.is_connected = True
    feed.yf_ticker = MagicMock()
    feed.yf_ticker.history.return_value = df
    return feed


def _fetch_at(feed: YahooFinanceDataFeed, now: datetime, count: int = 200):
    with patch("src.data.realtime_feed.datetime") as mock_dt:
        mock_dt.now.return_value = now
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        return feed.get_latest_candles(count=count)


class TestIncompleteCandleIsDropped:
    def test_drops_the_currently_forming_candle(self):
        # Yahoo published the 08:00 bar 5 seconds into the hour; it has
        # another 59m55s to run and its close is meaningless.
        feed = _connected_feed(_hourly_frame(last_hour=8))

        df = _fetch_at(feed, now=datetime(2026, 9, 11, 8, 0, 5))

        assert df.index[-1] == datetime(2026, 9, 11, 7, 0, 0), (
            f"last candle is {df.index[-1]}, but the 08:00 bar is still "
            f"forming — the strategy would evaluate a 5-second-old close "
            f"and skip the 07:00 London-open window entirely"
        )

    def test_keeps_the_last_candle_once_its_period_has_elapsed(self):
        # The live-observed happy path: worker wakes at 08:00:11, Yahoo's
        # latest bar is the now-closed 07:00 one. Must be left alone.
        feed = _connected_feed(_hourly_frame(last_hour=7))

        df = _fetch_at(feed, now=datetime(2026, 9, 11, 8, 0, 11))

        assert df.index[-1] == datetime(2026, 9, 11, 7, 0, 0)
        assert len(df) == 6

    def test_still_returns_count_closed_candles_when_one_is_dropped(self):
        # The drop must happen before the tail(count) trim, or every fetch
        # silently returns one fewer candle than the strategy asked for.
        feed = _connected_feed(_hourly_frame(last_hour=8, rows=10))

        df = _fetch_at(feed, now=datetime(2026, 9, 11, 8, 0, 5), count=6)

        assert len(df) == 6
        assert df.index[-1] == datetime(2026, 9, 11, 7, 0, 0)

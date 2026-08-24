"""Tests for fetch_metaapi_history.py's pure data-transformation functions.
No real MetaAPI network calls in this file — see test_fetch_metaapi_history.py's
TestFetchAllCandles for the mocked-client pagination tests."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from unittest.mock import AsyncMock

from fetch_metaapi_history import validate_candles, candles_to_dataframe, fetch_all_candles


def _candle(time, open_, high, low, close, volume=100):
    return {'time': time, 'open': open_, 'high': high, 'low': low, 'close': close, 'tickVolume': volume}


class TestValidateCandles:
    def test_keeps_valid_ohlc(self):
        candles = [_candle('2026-01-01T00:00:00.000Z', 2000.0, 2005.0, 1998.0, 2002.0)]
        valid, dropped = validate_candles(candles)
        assert valid == candles
        assert dropped == 0

    def test_drops_high_below_open_or_close(self):
        candles = [_candle('2026-01-01T00:00:00.000Z', 2000.0, 1999.0, 1998.0, 2002.0)]
        valid, dropped = validate_candles(candles)
        assert valid == []
        assert dropped == 1

    def test_drops_low_above_open_or_close(self):
        candles = [_candle('2026-01-01T00:00:00.000Z', 2000.0, 2005.0, 2001.0, 1999.0)]
        valid, dropped = validate_candles(candles)
        assert valid == []
        assert dropped == 1


class TestCandlesToDataframe:
    def test_produces_the_expected_schema(self):
        candles = [
            _candle('2026-01-01T01:00:00.000Z', 2001.0, 2006.0, 1999.0, 2003.0, volume=150),
            _candle('2026-01-01T00:00:00.000Z', 2000.0, 2005.0, 1998.0, 2002.0, volume=100),
        ]
        df = candles_to_dataframe(candles)
        assert list(df.columns) == ['open', 'high', 'low', 'close', 'volume']
        assert df.index.name == 'Datetime'
        assert df.index[0] < df.index[1]  # sorted ascending despite descending input
        assert df.iloc[0]['volume'] == 100

    def test_drops_duplicate_timestamps(self):
        candles = [
            _candle('2026-01-01T00:00:00.000Z', 2000.0, 2005.0, 1998.0, 2002.0),
            _candle('2026-01-01T00:00:00.000Z', 2000.0, 2005.0, 1998.0, 2002.0),
        ]
        df = candles_to_dataframe(candles)
        assert len(df) == 1

    def test_empty_candle_list_returns_empty_dataframe(self):
        df = candles_to_dataframe([])
        assert list(df.columns) == ['open', 'high', 'low', 'close', 'volume']
        assert df.index.name == 'Datetime'
        assert len(df) == 0


class TestFetchAllCandles:
    """No real MetaAPI network calls — `account` is an AsyncMock standing in
    for the SDK's MetatraderAccount, whose get_historical_candles() is a
    coroutine per the SDK's documented usage
    (await account.get_historical_candles(symbol=..., timeframe=..., start_time=..., limit=...))."""

    def test_pages_backward_until_a_short_page(self):
        account = AsyncMock()
        full_page = [
            _candle(f'2026-01-01T{h:02d}:00:00.000Z', 2000.0, 2005.0, 1998.0, 2002.0)
            for h in range(23, -1, -1)  # 24 candles — exactly one full page
        ]
        short_page = full_page[:5]
        account.get_historical_candles.side_effect = [full_page, short_page, []]

        candles = asyncio.run(fetch_all_candles(account, 'XAUUSD', '15m', page_limit=24))

        assert len(candles) == 24 + 5
        # stops after the short page (< page_limit signals end of history) —
        # never makes the third call
        assert account.get_historical_candles.call_count == 2

    def test_stops_immediately_on_empty_first_page(self):
        account = AsyncMock()
        account.get_historical_candles.side_effect = [[]]

        candles = asyncio.run(fetch_all_candles(account, 'XAUUSD', '15m', page_limit=1000))

        assert candles == []
        assert account.get_historical_candles.call_count == 1

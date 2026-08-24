"""Tests for fetch_metaapi_history.py's pure data-transformation functions.
No real MetaAPI network calls in this file — see test_fetch_metaapi_history.py's
TestFetchAllCandles for the mocked-client pagination tests."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fetch_metaapi_history import validate_candles, candles_to_dataframe


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

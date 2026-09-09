"""Regression coverage: YahooFinanceDataFeed.ticker_map silently fell back
to gold's ticker (GC=F) for any unmapped symbol — a real bug that would
have made a GBPUSD worker silently fetch gold data. See
docs/superpowers/specs/2026-09-09-gbpusd-eurusd-worker-wiring-design.md."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.realtime_feed import YahooFinanceDataFeed


class TestTickerMap:
    def test_gbpusd_maps_to_gbpusd_equals_x(self):
        feed = YahooFinanceDataFeed(symbol="GBPUSD", timeframe="1h")
        assert feed.ticker_map["GBPUSD"] == "GBPUSD=X"

    def test_eurusd_maps_to_eurusd_equals_x(self):
        feed = YahooFinanceDataFeed(symbol="EURUSD", timeframe="1h")
        assert feed.ticker_map["EURUSD"] == "EURUSD=X"

    def test_xauusd_still_maps_to_gc_equals_f(self):
        feed = YahooFinanceDataFeed(symbol="XAUUSD", timeframe="1h")
        assert feed.ticker_map["XAUUSD"] == "GC=F"

    def test_connect_raises_for_unmapped_symbol_instead_of_silently_using_gold(self):
        feed = YahooFinanceDataFeed(symbol="NOTASYMBOL", timeframe="1h")
        with pytest.raises(ValueError, match="NOTASYMBOL"):
            feed.connect()

"""Tests for mapping the market routes' `symbol` query to a Yahoo ticker.
/v1/market/price/latest and /v1/market/ohlcv used to fetch GC=F whatever
symbol was asked for, so EURUSD returned the gold price labelled EURUSD.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from market_symbols import UnknownSymbolError, yahoo_ticker


@pytest.mark.parametrize('symbol, ticker', [
    ('XAUUSD', 'GC=F'),
    ('EURUSD', 'EURUSD=X'),
    ('GBPUSD', 'GBPUSD=X'),
])
def test_each_live_symbol_maps_to_its_own_ticker(symbol, ticker):
    assert yahoo_ticker(symbol) == ticker


def test_symbol_is_case_insensitive():
    assert yahoo_ticker('eurusd') == 'EURUSD=X'


def test_unknown_symbol_raises_instead_of_falling_back_to_gold():
    with pytest.raises(UnknownSymbolError):
        yahoo_ticker('USDJPY')

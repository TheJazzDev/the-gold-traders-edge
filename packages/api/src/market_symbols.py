"""Map the API's trading symbols to Yahoo Finance tickers.

Mirrors the engine feed's ticker_map (packages/engine/src/data/realtime_feed.py).
No gold fallback: an unknown symbol must fail rather than return GC=F
labelled as something else.
"""

YAHOO_TICKERS = {
    "XAUUSD": "GC=F",
    "XAGUSD": "SI=F",
    "GBPUSD": "GBPUSD=X",
    "EURUSD": "EURUSD=X",
}


class UnknownSymbolError(ValueError):
    pass


def yahoo_ticker(symbol: str) -> str:
    try:
        return YAHOO_TICKERS[symbol.upper()]
    except KeyError:
        raise UnknownSymbolError(
            f"Unknown symbol '{symbol}' — known symbols: {sorted(YAHOO_TICKERS)}"
        ) from None

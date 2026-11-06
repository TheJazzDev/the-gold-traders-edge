"""
Put a signal's levels onto the broker's price.

Signals are built from Yahoo candles, and gold comes from GC=F futures, which
trade away from a broker's spot XAUUSD. The strategy's edge is in the stop and
target distances, so those are kept and moved to where the broker is trading.
"""
from typing import Tuple


def align_levels_to_broker(direction: str, entry: float, stop_loss: float, take_profit: float,
                           market_price: float, digits: int) -> Tuple[float, float, float]:
    """(entry, stop, target) at `market_price`: ask for a LONG, bid for a SHORT."""
    shift = market_price - entry
    return market_price, round(stop_loss + shift, digits), round(take_profit + shift, digits)

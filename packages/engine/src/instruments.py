"""
Per-symbol contract math: pip size, price precision, contract size.

The single source of truth for converting a price distance into pips or
dollars. Pip size used to be hardcoded as gold's 0.1 (`* 10`) in the
validator, the Signal model, the repository and the Telegram formatter, so
EURUSD/GBPUSD signals were published with their risk in hundred-thousandths
of a pip ("Risk: 0.0 pips").
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class Instrument:
    pip_size: float        # price move that counts as one pip
    price_decimals: int    # how many decimals a quote is shown with
    contract_size: float   # units of the base asset in one standard lot
    quote_currency: str = "USD"  # the currency a price move is paid in


INSTRUMENTS = {
    # 1 lot = 100 oz; a $1 move is $100 per lot, $1 per 0.01 lot.
    "XAUUSD": Instrument(pip_size=0.1, price_decimals=2, contract_size=100),
    # 1 lot = 100,000 units; one pip is $10 per lot, $0.10 per 0.01 lot.
    "EURUSD": Instrument(pip_size=0.0001, price_decimals=5, contract_size=100_000),
    "GBPUSD": Instrument(pip_size=0.0001, price_decimals=5, contract_size=100_000),
    # A move is paid in yen: one pip is 1,000 yen per lot, about $6.67 at 150.
    "USDJPY": Instrument(pip_size=0.01, price_decimals=3, contract_size=100_000,
                         quote_currency="JPY"),
}

# Lot sizes shown in Telegram messages as "what this would have made/lost".
REPORT_LOT_SIZES = (0.01, 0.05, 0.1, 0.5, 1.0)


def get_instrument(symbol: str) -> Instrument:
    """Raises KeyError for an unknown symbol — silently falling back to
    gold's numbers is exactly the bug this module exists to prevent."""
    return INSTRUMENTS[symbol.upper()]


def pip_size(symbol: str) -> float:
    return get_instrument(symbol).pip_size


def price_to_pips(symbol: str, price_distance: float) -> float:
    return price_distance / pip_size(symbol)


def format_price(symbol: str, price: float) -> str:
    return f"{price:.{get_instrument(symbol).price_decimals}f}"


def usd_per_quote(symbol: str, price: Optional[float] = None) -> float:
    """Dollars per unit of the symbol's quote currency. For USD/xxx pairs that
    is 1 / price, so a yen figure can't be converted without a price."""
    if get_instrument(symbol).quote_currency == "USD":
        return 1.0
    if not price:
        raise ValueError(f"{symbol} needs a price to convert its P&L to USD")
    return 1.0 / price


def usd_pnl(symbol: str, price_distance: float, lots: float,
            price: Optional[float] = None) -> float:
    """Dollar P&L of a `price_distance` move (signed, in the trade's favour)
    at `lots` standard lots. `price` is where the move ends; only pairs not
    quoted in USD need it."""
    instrument = get_instrument(symbol)
    return price_distance * instrument.contract_size * lots * usd_per_quote(symbol, price)


def lot_size_pnl(
    symbol: str, price_distance: float, lot_sizes=REPORT_LOT_SIZES,
    price: Optional[float] = None,
) -> List[Tuple[float, float]]:
    return [(lots, usd_pnl(symbol, price_distance, lots, price)) for lots in lot_sizes]

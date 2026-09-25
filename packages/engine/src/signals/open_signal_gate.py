"""
One open signal per symbol.

Every live rule was validated with BacktestEngine(max_open_trades=1), so
its stats describe a strategy that never holds two positions at once. Live
used to publish regardless of what was already open, and on 2026-09-23..25
that stacked up to five correlated XAUUSD shorts that one rally stopped out
together (see docs/superpowers/2026-09-25-weekly-signal-review.md). This
module supplies the check RealtimeSignalGenerator consults before
publishing, so live matches what was validated.
"""

from typing import Callable

from database.connection import DatabaseManager
from database.signal_repository import SignalRepository


def make_open_signal_checker(database_url: str, symbol: str) -> Callable[[], bool]:
    """
    Return a zero-arg callable that is True while the repository holds any
    open (PENDING/ACTIVE) signal for `symbol`, on any timeframe — the
    exposure is per instrument, not per worker.
    """
    db_manager = DatabaseManager(database_url)

    def has_open_signal() -> bool:
        with db_manager.session_scope() as session:
            return bool(SignalRepository(session).get_open_signals(symbol=symbol))

    return has_open_signal

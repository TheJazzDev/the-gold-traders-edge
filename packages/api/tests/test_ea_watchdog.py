"""The watchdog must speak once when the terminal goes quiet and once when it returns."""
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ea_watchdog import Watchdog

START = datetime(2026, 11, 20, 12, 0)


def _at(minutes):
    return START + timedelta(minutes=minutes)


def test_a_polling_terminal_raises_nothing():
    watchdog = Watchdog(START)
    assert watchdog.check(_at(30), last_seen=_at(29.9), live=True) is None


def test_silence_alerts_once_then_reports_the_return():
    watchdog = Watchdog(START)
    first = watchdog.check(_at(20), last_seen=_at(10), live=True)
    assert "has not contacted the server for 10 minutes" in first
    assert watchdog.check(_at(21), last_seen=_at(10), live=True) is None
    assert "is back" in watchdog.check(_at(22), last_seen=_at(21.9), live=True)
    assert watchdog.check(_at(23), last_seen=_at(22.9), live=True) is None


def test_no_alert_while_trading_is_off():
    watchdog = Watchdog(START)
    assert watchdog.check(_at(60), last_seen=None, live=False) is None


def test_a_terminal_that_never_polled_is_given_time_after_a_restart():
    watchdog = Watchdog(START)
    assert watchdog.check(_at(3), last_seen=None, live=True) is None
    assert watchdog.check(_at(7), last_seen=None, live=True) is not None

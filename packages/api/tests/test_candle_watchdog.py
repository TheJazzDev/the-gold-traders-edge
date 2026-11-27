"""The candle watchdog must speak once when a market stops getting candles and
once when they come back, counting only hours the market is open."""
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.candle_watchdog import CandleWatchdog

# Thursday 2026-11-26 12:00 UTC: a normal weekday, market open.
NOW = datetime(2026, 11, 26, 12, 0)
START = datetime(2026, 11, 24, 12, 0)


def heartbeat(worker='XAUUSD:1h', updated=NOW, start=START):
    return {
        'updated_at': updated.isoformat(),
        'start_time': start.isoformat(),
        'workers': {worker: {'is_running': True}},
    }


def candles(latest, worker='XAUUSD:1h'):
    return {worker: latest.isoformat() if latest else None}


def test_fresh_candles_raise_nothing():
    watchdog = CandleWatchdog()
    assert watchdog.check(NOW, heartbeat(), candles(NOW - timedelta(hours=1))) == []


def test_silence_alerts_once_then_reports_the_return():
    watchdog = CandleWatchdog()
    stale = candles(NOW - timedelta(hours=8))

    first = watchdog.check(NOW, heartbeat(), stale)
    assert len(first) == 1
    assert "XAUUSD 1h" in first[0]
    assert "8 market hours" in first[0]
    assert "2026-11-26 04:00 UTC" in first[0]

    assert watchdog.check(NOW + timedelta(minutes=5), heartbeat(), stale) == []

    back = watchdog.check(NOW + timedelta(minutes=10), heartbeat(), candles(NOW))
    assert len(back) == 1 and "XAUUSD 1h" in back[0] and "back" in back[0]
    assert watchdog.check(NOW + timedelta(minutes=15), heartbeat(), candles(NOW)) == []


def test_the_weekend_does_not_count():
    # Last candle Friday 20:00, now Sunday 23:00: only ~3 open hours have passed.
    watchdog = CandleWatchdog()
    friday = datetime(2026, 11, 27, 20, 0)
    sunday = datetime(2026, 11, 29, 23, 0)
    assert watchdog.check(sunday, heartbeat(updated=sunday), candles(friday)) == []


def test_each_worker_is_judged_on_its_own():
    watchdog = CandleWatchdog()
    beat = heartbeat()
    beat['workers']['GBPUSD:1h'] = {'is_running': True}
    latest = {**candles(NOW - timedelta(hours=8)), **candles(NOW - timedelta(hours=1), 'GBPUSD:1h')}
    messages = watchdog.check(NOW, beat, latest)
    assert len(messages) == 1 and "XAUUSD" in messages[0]


def test_a_restarted_worker_is_given_time_before_its_first_candle():
    watchdog = CandleWatchdog()
    just_started = heartbeat(start=NOW - timedelta(hours=1))
    assert watchdog.check(NOW, just_started, candles(None)) == []
    long_ago = heartbeat(start=NOW - timedelta(hours=8))
    assert len(watchdog.check(NOW, long_ago, candles(None))) == 1


def test_a_worker_missing_from_the_candles_setting_counts_from_its_start():
    # The first deploy: the heartbeat is old and the setting not written yet.
    # Counting from start_time, not from nothing, gives the worker its grace.
    watchdog = CandleWatchdog()
    assert watchdog.check(NOW, heartbeat(start=NOW - timedelta(hours=1)), {}) == []


def test_no_heartbeat_says_nothing():
    assert CandleWatchdog().check(NOW, {}, {}) == []


def test_limit_comes_from_the_environment(monkeypatch):
    monkeypatch.setenv("CANDLE_SILENCE_ALERT_HOURS", "10")
    watchdog = CandleWatchdog()
    assert watchdog.check(NOW, heartbeat(), candles(NOW - timedelta(hours=8))) == []

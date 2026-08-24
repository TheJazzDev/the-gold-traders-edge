"""Tests for TimeframeWorker.restart_if_needed.

Regression coverage for the fix: the monitor loop used to only log
"Worker {timeframe} has stopped, restarting..." without ever actually
restarting it, so a dead worker (e.g. a data feed hiccup) stayed dead
until a full manual redeploy while /health kept reporting healthy.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from run_multi_timeframe_service import TimeframeWorker


def _worker():
    return TimeframeWorker(
        timeframe='1h',
        database_url='sqlite:///:memory:',
        shared_dedup_subscriber=MagicMock(),
    )


class TestRestartIfNeeded:
    def test_does_nothing_while_still_running(self):
        worker = _worker()
        worker.is_running = True
        worker.start = MagicMock()

        restarted = worker.restart_if_needed()

        assert restarted is False
        worker.start.assert_not_called()

    def test_restarts_a_dead_worker(self):
        worker = _worker()
        worker.is_running = False
        worker.last_start_time = None  # never started — treat as a fresh failure
        worker.start = MagicMock()

        restarted = worker.restart_if_needed()

        assert restarted is True
        worker.start.assert_called_once()

    def test_resets_backoff_after_a_healthy_uptime(self):
        worker = _worker()
        worker.is_running = False
        worker.restart_backoff_seconds = 80  # simulate prior backoff growth
        worker.last_start_time = 0.0  # "ran a long time ago" relative to time.monotonic()
        worker.start = MagicMock()

        worker.restart_if_needed(min_uptime_seconds=60)

        assert worker.restart_backoff_seconds == 10

    def test_doubles_backoff_on_immediate_repeated_failure(self):
        import time
        worker = _worker()
        worker.is_running = False
        worker.restart_backoff_seconds = 10
        worker.last_start_time = time.monotonic()  # just started, died immediately
        worker.start = MagicMock()

        worker.restart_if_needed(min_uptime_seconds=60)

        assert worker.restart_backoff_seconds == 20

    def test_caps_backoff_at_max(self):
        import time
        worker = _worker()
        worker.is_running = False
        worker.restart_backoff_seconds = 250
        worker.last_start_time = time.monotonic()
        worker.start = MagicMock()

        worker.restart_if_needed(min_uptime_seconds=60, max_backoff_seconds=300)

        assert worker.restart_backoff_seconds == 300

    def test_does_not_restart_again_before_backoff_elapses(self):
        worker = _worker()
        worker.is_running = False
        worker.last_start_time = None
        worker.start = MagicMock()

        first = worker.restart_if_needed()
        # Still "dead" immediately after — the restart_if_needed caller
        # doesn't know start() actually flips is_running (it's mocked),
        # so simulate that here to test the cooldown gate specifically.
        second = worker.restart_if_needed()

        assert first is True
        assert second is False
        worker.start.assert_called_once()

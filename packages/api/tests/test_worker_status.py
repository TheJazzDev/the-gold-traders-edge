"""Tests for deriving live worker status from the engine's persisted
heartbeat (see packages/engine/run_multi_timeframe_service.py's
_save_heartbeat). Pure logic, no DB/FastAPI needed.
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from worker_status import derive_worker_status


NOW = datetime(2026, 9, 7, 22, 0, 0)


def heartbeat_at(age_seconds, worker_id='XAUUSD:1h', **worker_kwargs):
    updated_at = NOW - timedelta(seconds=age_seconds)
    worker = {'is_running': True, 'candles_processed': 80, 'signals_generated': 1}
    worker.update(worker_kwargs)
    return {
        'updated_at': updated_at.isoformat(),
        'start_time': datetime(2026, 9, 4, 12, 0, 0).isoformat(),
        'workers': {worker_id: worker},
    }


class TestDeriveWorkerStatus:
    def test_no_heartbeat_yet_reports_unknown_not_running(self):
        result = derive_worker_status({}, worker_id='XAUUSD:1h', now=NOW)
        assert result.is_running is False
        assert result.candles_processed == 0
        assert result.signals_generated == 0
        assert result.uptime_hours is None

    def test_fresh_heartbeat_with_running_worker_reports_running(self):
        heartbeat = heartbeat_at(age_seconds=10)
        result = derive_worker_status(heartbeat, worker_id='XAUUSD:1h', now=NOW)
        assert result.is_running is True
        assert result.candles_processed == 80
        assert result.signals_generated == 1
        assert result.uptime_hours == expected_uptime_hours(NOW, datetime(2026, 9, 4, 12, 0, 0))

    def test_stale_heartbeat_reports_not_running_even_if_worker_said_running(self):
        heartbeat = heartbeat_at(age_seconds=999, is_running=True)
        result = derive_worker_status(heartbeat, worker_id='XAUUSD:1h', now=NOW, stale_after_seconds=120)
        assert result.is_running is False
        # counts still reported — last known values, just not "live"
        assert result.candles_processed == 80

    def test_stale_heartbeat_reports_no_uptime(self):
        """A crashed worker shouldn't show an ever-growing uptime next to status=stopped."""
        heartbeat = heartbeat_at(age_seconds=999, is_running=True)
        result = derive_worker_status(heartbeat, worker_id='XAUUSD:1h', now=NOW, stale_after_seconds=120)
        assert result.uptime_hours is None

    def test_worker_reporting_itself_stopped_is_not_running_even_if_heartbeat_fresh(self):
        heartbeat = heartbeat_at(age_seconds=5, is_running=False)
        result = derive_worker_status(heartbeat, worker_id='XAUUSD:1h', now=NOW)
        assert result.is_running is False

    def test_worker_reporting_itself_stopped_reports_no_uptime(self):
        heartbeat = heartbeat_at(age_seconds=5, is_running=False)
        result = derive_worker_status(heartbeat, worker_id='XAUUSD:1h', now=NOW)
        assert result.uptime_hours is None

    def test_unknown_worker_id_reports_not_running_no_arbitrary_fallback(self):
        """Regression: with more than one worker in the heartbeat, a
        worker_id miss must report 'not running', never silently grab a
        different worker's data (the old bare-timeframe fallback's own
        comment flagged this exact gap)."""
        heartbeat = heartbeat_at(age_seconds=5, worker_id='GBPUSD:1h')
        result = derive_worker_status(heartbeat, worker_id='XAUUSD:1h', now=NOW)
        assert result.is_running is False
        assert result.candles_processed == 0

    def test_distinguishes_two_workers_in_the_same_heartbeat(self):
        heartbeat = {
            'updated_at': NOW.isoformat(),
            'start_time': datetime(2026, 9, 4, 12, 0, 0).isoformat(),
            'workers': {
                'XAUUSD:1h': {'is_running': True, 'candles_processed': 80, 'signals_generated': 1},
                'GBPUSD:1h': {'is_running': True, 'candles_processed': 12, 'signals_generated': 0},
            },
        }
        gold = derive_worker_status(heartbeat, worker_id='XAUUSD:1h', now=NOW)
        gbp = derive_worker_status(heartbeat, worker_id='GBPUSD:1h', now=NOW)
        assert gold.candles_processed == 80
        assert gbp.candles_processed == 12


def expected_uptime_hours(now, start_time):
    return (now - start_time).total_seconds() / 3600

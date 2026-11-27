"""Tests for persisting live worker status so the API can report real state
instead of guessing liveness from signal staleness (see MEMORY: the
/v1/signals/service/status and /v1/settings/service/status endpoints used to
report "stopped" for a perfectly healthy worker that simply hadn't generated
a new signal recently).
"""
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import run_multi_timeframe_service as svc_module


class FakeGenerator:
    def __init__(self, candles, signals):
        self.total_candles_processed = candles
        self.total_signals_generated = signals


class FakeWorker:
    def __init__(self, is_running, candles, signals):
        self.is_running = is_running
        self.generator = FakeGenerator(candles, signals)

    def stop(self):
        self.is_running = False


def make_service(db_url):
    service = svc_module.MultiTimeframeService.__new__(svc_module.MultiTimeframeService)
    service.database_url = db_url
    service.start_time = datetime(2026, 1, 1, 0, 0, 0)
    service.workers = {}
    return service


def read_heartbeat(db_url):
    from database.connection import DatabaseManager
    from database.settings_repository import SettingsRepository

    db_manager = DatabaseManager(db_url)
    with db_manager.session_scope() as session:
        repo = SettingsRepository(session)
        return repo.get('worker_heartbeat', default={})


class TestHeartbeatWriteIsCheap:
    """
    _save_heartbeat runs every 15s for the life of the process — it must not
    re-run the full defaults sync (Base.metadata.create_all +
    SettingsRepository.initialize_defaults, a query per DEFAULT_SETTINGS row)
    or open a fresh DatabaseManager/engine on every call.
    """

    def test_initialize_defaults_runs_once_across_many_heartbeat_writes(self, tmp_path, monkeypatch):
        from database.settings_repository import SettingsRepository

        db_url = f"sqlite:///{tmp_path / 'heartbeat.db'}"
        service = make_service(db_url)
        service.workers = {'1h': FakeWorker(is_running=True, candles=1, signals=0)}

        call_count = {'n': 0}
        original = SettingsRepository.initialize_defaults

        def counting_initialize_defaults(self):
            call_count['n'] += 1
            return original(self)

        monkeypatch.setattr(SettingsRepository, 'initialize_defaults', counting_initialize_defaults)

        service._save_heartbeat()
        service._save_heartbeat()
        service._save_heartbeat()

        assert call_count['n'] == 1

    def test_reuses_the_same_database_manager_across_calls(self, tmp_path):
        db_url = f"sqlite:///{tmp_path / 'heartbeat.db'}"
        service = make_service(db_url)
        service.workers = {'1h': FakeWorker(is_running=True, candles=1, signals=0)}

        service._save_heartbeat()
        first_manager = service._db_manager
        service._save_heartbeat()

        assert first_manager is not None
        assert service._db_manager is first_manager


class TestSaveHeartbeat:
    def test_creates_settings_table_if_missing(self, tmp_path):
        """Regression: the settings table may not exist yet in a fresh DB."""
        db_url = f"sqlite:///{tmp_path / 'fresh.db'}"
        service = make_service(db_url)
        service._save_heartbeat()

        # Not just "didn't raise" — the row must actually have been written.
        payload = read_heartbeat(db_url)
        assert 'updated_at' in payload

    def test_persists_per_worker_counts_readable_back(self, tmp_path):
        db_url = f"sqlite:///{tmp_path / 'heartbeat.db'}"
        service = make_service(db_url)
        service.workers = {'1h': FakeWorker(is_running=True, candles=80, signals=1)}

        service._save_heartbeat()

        payload = read_heartbeat(db_url)
        assert payload['workers']['1h'] == {
            'is_running': True,
            'candles_processed': 80,
            'signals_generated': 1,
        }
        assert payload['start_time'] == '2026-01-01T00:00:00'
        assert 'updated_at' in payload

    def test_overwrites_previous_heartbeat_on_each_call(self, tmp_path):
        db_url = f"sqlite:///{tmp_path / 'heartbeat.db'}"
        service = make_service(db_url)

        service.workers = {'1h': FakeWorker(is_running=True, candles=10, signals=0)}
        service._save_heartbeat()

        service.workers = {'1h': FakeWorker(is_running=False, candles=20, signals=1)}
        service._save_heartbeat()

        payload = read_heartbeat(db_url)
        assert payload['workers']['1h'] == {
            'is_running': False,
            'candles_processed': 20,
            'signals_generated': 1,
        }


class TestStopFlushesFinalHeartbeat:
    """
    Regression: stop() used to leave the last-written heartbeat (up to 15s
    old, showing every worker is_running=True) in place, so a gracefully
    stopped service kept reporting "running" via the API until the
    heartbeat aged past the staleness threshold.
    """

    def test_stop_persists_is_running_false_for_every_worker(self, tmp_path):
        db_url = f"sqlite:///{tmp_path / 'heartbeat.db'}"
        service = make_service(db_url)
        worker = FakeWorker(is_running=True, candles=50, signals=2)
        service.workers = {'1h': worker}

        service.stop()

        payload = read_heartbeat(db_url)
        assert payload['workers']['1h']['is_running'] is False
        # counts as of the moment of shutdown are preserved, not reset
        assert payload['workers']['1h']['candles_processed'] == 50
        assert payload['workers']['1h']['signals_generated'] == 2

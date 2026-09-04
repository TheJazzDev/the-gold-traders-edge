"""Tests for persisting the weekly report timer across service restarts."""
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import run_multi_timeframe_service as svc_module


def make_service(db_url):
    service = svc_module.MultiTimeframeService.__new__(svc_module.MultiTimeframeService)
    service.database_url = db_url
    return service


class TestLoadLastReportTime:
    def test_returns_none_when_never_sent(self, tmp_path):
        service = make_service(f"sqlite:///{tmp_path / 'timer.db'}")
        assert service._load_last_report_time() is None

    def test_creates_settings_table_if_missing(self, tmp_path):
        """Regression: the settings table may not exist yet in a fresh DB."""
        service = make_service(f"sqlite:///{tmp_path / 'fresh.db'}")
        # Should not raise even though nothing has ever touched this DB.
        assert service._load_last_report_time() is None


class TestSaveAndLoadRoundTrip:
    def test_persists_across_separate_service_instances(self, tmp_path):
        db_url = f"sqlite:///{tmp_path / 'timer.db'}"
        writer = make_service(db_url)
        when = datetime(2026, 1, 1, 12, 0, 0)

        # First load initializes the settings row (simulates first startup).
        assert writer._load_last_report_time() is None
        writer._save_last_report_time(when)

        # A brand new service instance (simulating a restart) should see it.
        reader = make_service(db_url)
        loaded = reader._load_last_report_time()
        assert loaded == when

    def test_recent_report_time_means_not_due_yet(self, tmp_path):
        db_url = f"sqlite:///{tmp_path / 'timer.db'}"
        service = make_service(db_url)
        recent = datetime.now() - timedelta(days=1)
        service._save_last_report_time(recent)

        loaded = service._load_last_report_time()
        report_interval = 7 * 24 * 3600
        assert (datetime.now() - loaded).total_seconds() < report_interval

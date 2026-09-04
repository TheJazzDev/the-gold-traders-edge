"""
Regression coverage for the disconnect between the `enabled_strategies` /
`min_confidence` / `min_rr_ratio` settings and what the live worker actually
runs.

Before this fix, TimeframeWorker._run() applied the tuned config's
`enabled_rules` exactly once at thread start and never looked at the
settings table again — flipping a strategy's toggle in the admin UI (which
writes `enabled_strategies`) had no effect on a running worker. This test
verifies TimeframeWorker wires a `pre_run_hook` into RealtimeSignalGenerator
that re-reads those settings and mutates the live strategy/validator.
"""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import run_multi_timeframe_service as svc_module
from signals.gold_strategy import GoldStrategy
from database.connection import DatabaseManager
from database.models import Base
from database.settings_repository import SettingsRepository


def make_worker(tmp_path, timeframe="1h"):
    worker = svc_module.TimeframeWorker.__new__(svc_module.TimeframeWorker)
    worker.timeframe = timeframe
    worker.database_url = f"sqlite:///{tmp_path / 'settings.db'}"
    worker.shared_dedup_subscriber = MagicMock()
    worker.telegram_subscriber = MagicMock()
    worker.enable_trading = False
    worker.mt5_config = None
    return worker


def seed_settings(database_url, **overrides):
    db_manager = DatabaseManager(database_url)
    with db_manager.session_scope() as session:
        Base.metadata.create_all(bind=session.get_bind())
        repo = SettingsRepository(session)
        repo.initialize_defaults()
        for key, value in overrides.items():
            repo.set(key, value)


def run_worker_and_capture_hook(worker, tmp_path):
    tuned_dir = tmp_path / "tuned_configs"
    tuned_dir.mkdir(exist_ok=True)
    (tuned_dir / f"{worker.timeframe}.json").write_text(json.dumps({
        "config": {**GoldStrategy.DEFAULT_CONFIG, "trend_lookback": 200},
        "enabled_rules": ["order_block_retest"],
        "expiry_hours": 143,
    }))

    with patch.object(svc_module, "__file__", str(tmp_path / "run_multi_timeframe_service.py")), \
         patch.object(svc_module, "create_datafeed"), \
         patch.object(svc_module, "RealtimeSignalGenerator") as mock_generator_cls, \
         patch.object(svc_module, "SignalOutcomeTracker"):
        worker._run()

    kwargs = mock_generator_cls.call_args.kwargs
    return kwargs["strategy"], kwargs["validator"], kwargs["pre_run_hook"]


class TestSettingsDrivenRuleEnabling:
    def test_pre_run_hook_applies_enabled_strategies_from_settings(self, tmp_path):
        worker = make_worker(tmp_path)
        seed_settings(
            worker.database_url,
            enabled_strategies=["momentum_equilibrium", "london_session_breakout"],
        )

        strategy, _validator, refresh = run_worker_and_capture_hook(worker, tmp_path)

        # Tuned config alone would have left only order_block_retest on.
        assert strategy.rules_enabled["order_block_retest"] is True

        refresh()

        assert strategy.rules_enabled["momentum_equilibrium"] is True
        assert strategy.rules_enabled["london_session_breakout"] is True
        assert strategy.rules_enabled["order_block_retest"] is False
        assert strategy.rules_enabled["golden_fibonacci"] is False
        assert strategy.rules_enabled["ath_retest"] is False

    def test_pre_run_hook_applies_min_confidence_and_min_rr_ratio(self, tmp_path):
        worker = make_worker(tmp_path)
        seed_settings(worker.database_url, min_confidence=0.75, min_rr_ratio=2.5)

        _strategy, validator, refresh = run_worker_and_capture_hook(worker, tmp_path)
        refresh()

        assert validator.min_confidence == 0.75
        assert validator.min_rr_ratio == 2.5

    def test_pre_run_hook_reflects_toggling_a_strategy_off_live(self, tmp_path):
        """The whole point: flipping the setting after the worker has
        started must change behavior on the next refresh, with no restart."""
        worker = make_worker(tmp_path)
        seed_settings(worker.database_url, enabled_strategies=["order_block_retest"])

        strategy, _validator, refresh = run_worker_and_capture_hook(worker, tmp_path)
        refresh()
        assert strategy.rules_enabled["order_block_retest"] is True

        seed_settings(worker.database_url, enabled_strategies=[])
        refresh()
        assert strategy.rules_enabled["order_block_retest"] is False

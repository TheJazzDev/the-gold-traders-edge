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
from datetime import datetime
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


def run_worker_and_capture_all_kwargs(worker, tmp_path):
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

    return mock_generator_cls.call_args.kwargs


class TestSettingsDrivenRuleEnabling:
    def test_pre_run_hook_ignores_ruled_out_rule_names_still_listed_in_settings(self, tmp_path):
        """Order Block Retest is the only rule GoldStrategy knows about now
        (see docs/superpowers/specs/strategy-ledger.md) — a settings row
        still listing a ruled-out legacy rule name must not error, it's
        simply not something `rules_enabled` has a key for."""
        worker = make_worker(tmp_path)
        seed_settings(
            worker.database_url,
            enabled_strategies=["momentum_equilibrium", "order_block_retest"],
        )

        strategy, _validator, refresh = run_worker_and_capture_hook(worker, tmp_path)
        refresh()

        assert strategy.rules_enabled == {"order_block_retest": True}

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


class TestLastProcessedCandlePersistence:
    """Regression coverage for the 2026-09-08 duplicate-signal incident: a
    deploy restarted the worker mid-candle, and the fresh worker instance —
    with no memory of which candle had already been evaluated — immediately
    re-signaled on it. TimeframeWorker must wire last_processed_candle_getter/
    setter into RealtimeSignalGenerator, persisted (per timeframe) so it
    survives exactly this kind of restart. See
    docs/superpowers/specs/strategy-ledger.md."""

    def test_getter_returns_none_before_anything_is_recorded(self, tmp_path):
        worker = make_worker(tmp_path)
        kwargs = run_worker_and_capture_all_kwargs(worker, tmp_path)

        assert kwargs["last_processed_candle_getter"]() is None

    def test_setter_persists_and_getter_reflects_it_on_the_same_worker(self, tmp_path):
        worker = make_worker(tmp_path)
        kwargs = run_worker_and_capture_all_kwargs(worker, tmp_path)

        when = datetime(2026, 9, 8, 18, 0, 0)
        kwargs["last_processed_candle_setter"](when)

        assert kwargs["last_processed_candle_getter"]() == when

    def test_survives_a_simulated_restart_a_fresh_worker_instance_sees_it(self, tmp_path):
        """The actual bug scenario: worker A processes candle X, then dies
        (deploy). Worker B starts fresh (a brand new TimeframeWorker/thread)
        against the SAME database — it must see that X was already
        processed, not just the in-memory state of worker A (which is
        gone)."""
        worker_a = make_worker(tmp_path)
        kwargs_a = run_worker_and_capture_all_kwargs(worker_a, tmp_path)
        when = datetime(2026, 9, 8, 18, 0, 0)
        kwargs_a["last_processed_candle_setter"](when)

        worker_b = make_worker(tmp_path)  # simulates the post-restart process
        kwargs_b = run_worker_and_capture_all_kwargs(worker_b, tmp_path)

        assert kwargs_b["last_processed_candle_getter"]() == when

    def test_keyed_by_timeframe_independently(self, tmp_path):
        worker_1h = make_worker(tmp_path, timeframe="1h")
        kwargs_1h = run_worker_and_capture_all_kwargs(worker_1h, tmp_path)
        kwargs_1h["last_processed_candle_setter"](datetime(2026, 9, 8, 18, 0, 0))

        worker_15m = make_worker(tmp_path, timeframe="15m")
        kwargs_15m = run_worker_and_capture_all_kwargs(worker_15m, tmp_path)

        # A different timeframe's worker must not see 1h's recorded candle.
        assert kwargs_15m["last_processed_candle_getter"]() is None

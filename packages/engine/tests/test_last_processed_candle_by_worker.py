"""Regression coverage: last_processed_candle must be keyed by worker_id
(symbol:timeframe), not bare timeframe — two workers sharing a timeframe
string (e.g. XAUUSD:1h and GBPUSD:1h) must not corrupt each other's
restart-duplicate-signal protection. See the 2026-09-08 duplicate-signal
incident and docs/superpowers/specs/2026-09-09-gbpusd-eurusd-worker-wiring-design.md."""
import json
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import run_multi_timeframe_service as svc_module
from signals.gold_strategy import GoldStrategy
from signals.forex_session_strategy import ForexSessionStrategy
from database.connection import DatabaseManager
from database.models import Base
from database.settings_models import Setting, SettingCategory
from database.settings_repository import SettingsRepository


def make_worker(spec, tmp_path):
    worker = svc_module.TimeframeWorker.__new__(svc_module.TimeframeWorker)
    worker.spec = spec
    worker.database_url = f"sqlite:///{tmp_path / 'settings.db'}"
    worker.shared_dedup_subscriber = MagicMock()
    worker.telegram_subscriber = MagicMock()
    worker.enable_trading = False
    worker.mt5_config = None
    return worker


def run_and_capture_candle_kwargs(worker, tmp_path):
    tuned_dir = tmp_path / "tuned_configs"
    tuned_dir.mkdir(exist_ok=True)
    if worker.spec.strategy_class is GoldStrategy:
        config = {**GoldStrategy.DEFAULT_CONFIG, "trend_lookback": 200}
        extra = {"enabled_rules": ["order_block_retest"], "expiry_hours": 143}
    else:
        config = ForexSessionStrategy.DEFAULT_CONFIG
        extra = {}
    (tuned_dir / worker.spec.tuned_config_filename).write_text(json.dumps({"config": config, **extra}))

    with patch.object(svc_module, "__file__", str(tmp_path / "run_multi_timeframe_service.py")), \
         patch.object(svc_module, "create_datafeed"), \
         patch.object(svc_module, "RealtimeSignalGenerator") as mock_generator_cls, \
         patch.object(svc_module, "SignalOutcomeTracker"):
        worker._run()

    kwargs = mock_generator_cls.call_args.kwargs
    return kwargs["last_processed_candle_getter"], kwargs["last_processed_candle_setter"]


class TestLastProcessedCandleKeyedByWorkerId:
    def test_same_timeframe_different_symbols_do_not_collide(self, tmp_path):
        gold_worker = make_worker(svc_module.XAUUSD_1H_SPEC, tmp_path)
        gold_get, gold_set = run_and_capture_candle_kwargs(gold_worker, tmp_path)
        gold_set(datetime(2026, 9, 8, 18, 0, 0))

        gbp_worker = make_worker(svc_module.GBPUSD_1H_SPEC, tmp_path)
        gbp_get, gbp_set = run_and_capture_candle_kwargs(gbp_worker, tmp_path)

        # GBPUSD:1h must not see XAUUSD:1h's recorded candle.
        assert gbp_get() is None
        assert gold_get() == datetime(2026, 9, 8, 18, 0, 0)

        gbp_set(datetime(2026, 9, 9, 7, 0, 0))
        # And setting GBPUSD's must not disturb gold's.
        assert gold_get() == datetime(2026, 9, 8, 18, 0, 0)
        assert gbp_get() == datetime(2026, 9, 9, 7, 0, 0)


class TestLastProcessedCandleSeedMigration:
    def _seed_old_setting(self, db_url, timeframe_value):
        db_manager = DatabaseManager(db_url)
        with db_manager.session_scope() as session:
            Base.metadata.create_all(bind=session.get_bind())
            repo = SettingsRepository(session)
            repo.initialize_defaults()
            setting = repo.get_setting('last_processed_candle_by_timeframe')
            setting.set_typed_value({'1h': timeframe_value})
            session.commit()

    def test_seeds_xauusd_1h_from_old_bare_timeframe_key(self, tmp_path):
        db_url = f"sqlite:///{tmp_path / 'migrate.db'}"
        self._seed_old_setting(db_url, '2026-09-08T18:00:00')

        db_manager = DatabaseManager(db_url)
        with db_manager.session_scope() as session:
            # A fresh SettingsRepository (simulating the next process
            # startup) re-running initialize_defaults() must perform the
            # seed migration.
            repo = SettingsRepository(session)
            repo.initialize_defaults()
            by_worker = repo.get('last_processed_candle_by_worker', default={})

        assert by_worker == {'XAUUSD:1h': '2026-09-08T18:00:00'}

    def test_seeds_correctly_on_the_very_first_initialize_defaults_call_ever(self, tmp_path):
        """Finding 2 (2026-09-09 final whole-branch review): reproduces the
        true production first-run shape — last_processed_candle_by_worker
        does not exist as a row AT ALL yet (not even the default '{}' row),
        because initialize_defaults() has never run before. The two other
        tests in this class both call initialize_defaults() once in setup
        (via _seed_old_setting -> repo.initialize_defaults()), which itself
        creates the by_worker row on that call — so neither of them
        exercises this scenario; this is the test that would have caught
        the bug. Without SettingsRepository.initialize_defaults()'s
        self.session.flush() (added before _migrate_last_processed_candle_by_worker()
        runs), the same-call `session.add(Setting(key='last_processed_candle_by_worker', ...))`
        is not yet queryable under DatabaseManager's autoflush=False
        sessionmaker, so the migration's own query for that row returns
        None, hits its `if not by_worker_setting: return` guard, and
        silently skips the seed on this first run — verified empirically
        against a reconstructed production-shaped DB."""
        db_url = f"sqlite:///{tmp_path / 'migrate3.db'}"

        # Seed ONLY the old setting, bypassing initialize_defaults() entirely
        # (direct Setting row creation + commit), matching production: real
        # last_processed_candle_by_timeframe data, but the new
        # last_processed_candle_by_worker setting has never been created.
        db_manager = DatabaseManager(db_url)
        with db_manager.session_scope() as session:
            Base.metadata.create_all(bind=session.get_bind())
            old_setting = Setting(
                key='last_processed_candle_by_timeframe',
                category=SettingCategory.SYSTEM,
                value='{}',
                value_type='json',
                default_value='{}',
                editable=False,
                requires_restart=False,
            )
            old_setting.set_typed_value({'1h': '2026-09-08T18:00:00'})
            session.add(old_setting)
            session.commit()

        with db_manager.session_scope() as session:
            # Confirm the precondition: last_processed_candle_by_worker
            # truly does not exist as a row before this call.
            assert session.query(Setting).filter_by(key='last_processed_candle_by_worker').first() is None

            repo = SettingsRepository(session)
            repo.initialize_defaults()  # THE call under test — the very first ever
            by_worker = repo.get('last_processed_candle_by_worker', default={})

        assert by_worker == {'XAUUSD:1h': '2026-09-08T18:00:00'}

    def test_does_not_reset_once_real_worker_data_exists(self, tmp_path):
        db_url = f"sqlite:///{tmp_path / 'migrate2.db'}"
        self._seed_old_setting(db_url, '2026-09-08T18:00:00')

        db_manager = DatabaseManager(db_url)
        with db_manager.session_scope() as session:
            repo = SettingsRepository(session)
            repo.initialize_defaults()  # first run performs the seed
            setting = repo.get_setting('last_processed_candle_by_worker')
            setting.set_typed_value({'XAUUSD:1h': '2026-09-09T07:00:00'})  # real data written since
            session.commit()

        with db_manager.session_scope() as session:
            repo = SettingsRepository(session)
            repo.initialize_defaults()  # second run must not clobber it
            by_worker = repo.get('last_processed_candle_by_worker', default={})

        assert by_worker == {'XAUUSD:1h': '2026-09-09T07:00:00'}

"""Regression coverage: TimeframeWorker._run() must dispatch on the
WorkerSpec's symbol/strategy_class instead of hardcoding XAUUSD/GoldStrategy,
and must tolerate GBPUSD/EURUSD's tuned config shape (no enabled_rules or
expiry_hours keys — confirmed by inspection, see
docs/superpowers/specs/2026-09-09-gbpusd-eurusd-worker-wiring-design.md)."""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import run_multi_timeframe_service as svc_module
from signals.forex_session_strategy import ForexSessionStrategy


def make_worker(spec, tmp_path):
    worker = svc_module.TimeframeWorker.__new__(svc_module.TimeframeWorker)
    worker.spec = spec
    worker.database_url = f"sqlite:///{tmp_path / 'settings.db'}"
    worker.shared_dedup_subscriber = MagicMock()
    worker.telegram_subscriber = MagicMock()
    worker.enable_trading = False
    worker.mt5_config = None
    return worker


class TestForexWorkerDispatch:
    def test_gbpusd_worker_creates_datafeed_for_gbpusd_not_gold(self, tmp_path, monkeypatch):
        monkeypatch.setattr(svc_module, "__file__", str(tmp_path / "run_multi_timeframe_service.py"))
        worker = make_worker(svc_module.GBPUSD_1H_SPEC, tmp_path)
        fake_generator = MagicMock()

        with patch.object(svc_module, "create_datafeed") as mock_create_feed, \
             patch.object(svc_module, "RealtimeSignalGenerator", return_value=fake_generator) as mock_generator_cls, \
             patch.object(svc_module, "SignalOutcomeTracker") as mock_tracker_cls:
            worker._run()

        assert mock_create_feed.call_args.kwargs["symbol"] == "GBPUSD"
        assert mock_tracker_cls.call_args.kwargs["symbol"] == "GBPUSD"
        assert isinstance(mock_generator_cls.call_args.kwargs["strategy"], ForexSessionStrategy)

    def test_gbpusd_tuned_config_without_enabled_rules_does_not_raise(self, tmp_path, monkeypatch):
        """gbpusd_1h.json has no `enabled_rules` key (unlike gold's 1h.json)
        — the loader must not KeyError."""
        monkeypatch.setattr(svc_module, "__file__", str(tmp_path / "run_multi_timeframe_service.py"))
        tuned_dir = tmp_path / "tuned_configs"
        tuned_dir.mkdir()
        (tuned_dir / "gbpusd_1h.json").write_text(json.dumps({
            "config": ForexSessionStrategy.DEFAULT_CONFIG,
            "enabled": True,
            "train": {"profit_factor": 1.1},
            "test": {"profit_factor": 1.58},
        }))
        worker = make_worker(svc_module.GBPUSD_1H_SPEC, tmp_path)
        fake_generator = MagicMock()

        with patch.object(svc_module, "create_datafeed"), \
             patch.object(svc_module, "RealtimeSignalGenerator", return_value=fake_generator), \
             patch.object(svc_module, "SignalOutcomeTracker") as mock_tracker_cls:
            worker._run()

        # No KeyError raised (test passing at all is the primary assertion);
        # also confirm the 48.0-hour fallback expiry was used.
        assert mock_tracker_cls.call_args.kwargs["expiry_hours"] == 48.0

    def test_gbpusd_tuned_config_without_enabled_rules_fails_closed(self, tmp_path, monkeypatch):
        """Finding 1 (2026-09-09 final whole-branch review): ForexSessionStrategy's
        own constructor default for its one rule is True, and gbpusd_1h.json
        has no enabled_rules key to override it with. If TimeframeWorker._run()
        left the strategy at that constructor default, the rule would be LIVE
        from construction until refresh_settings() (the pre_run_hook) first
        succeeds — and RealtimeSignalGenerator.start() only logs a
        pre_run_hook failure, it still calls run_once() regardless. A
        transient DB error on the very first candle (e.g. a fresh deploy
        racing Postgres) would let GBPUSD/EURUSD signal live before
        enabled_forex_symbols is ever consulted. _run() must therefore force
        every rule to False right after construction whenever there's no
        enabled_rules key to read — fail CLOSED at construction time, never
        rely on a later successful settings read to be the only thing that
        disables it. This test calls worker._run() directly and never invokes
        the pre_run_hook/refresh_settings — it proves the construction-time
        default alone, not the settings-driven override (which is covered by
        test_settings_driven_rules.py::TestForexSymbolEnabling)."""
        monkeypatch.setattr(svc_module, "__file__", str(tmp_path / "run_multi_timeframe_service.py"))
        tuned_dir = tmp_path / "tuned_configs"
        tuned_dir.mkdir()
        (tuned_dir / "gbpusd_1h.json").write_text(json.dumps({
            "config": ForexSessionStrategy.DEFAULT_CONFIG,
            "enabled": True,
            "train": {"profit_factor": 1.1},
            "test": {"profit_factor": 1.58},
        }))
        worker = make_worker(svc_module.GBPUSD_1H_SPEC, tmp_path)
        fake_generator = MagicMock()

        with patch.object(svc_module, "create_datafeed"), \
             patch.object(svc_module, "RealtimeSignalGenerator", return_value=fake_generator) as mock_generator_cls, \
             patch.object(svc_module, "SignalOutcomeTracker"):
            worker._run()

        strategy = mock_generator_cls.call_args.kwargs["strategy"]
        assert strategy.rules_enabled == {"asian_range_london_breakout": False}

    def test_gbpusd_no_tuned_config_file_at_all_also_fails_closed(self, tmp_path, monkeypatch):
        """Finding 1's fail-closed fix must also cover the fallback branch
        (no tuned config file on disk at all, not just one missing
        enabled_rules) — same unsafe constructor-default exposure otherwise.
        No pre_run_hook/refresh_settings is invoked here either."""
        monkeypatch.setattr(svc_module, "__file__", str(tmp_path / "run_multi_timeframe_service.py"))
        worker = make_worker(svc_module.GBPUSD_1H_SPEC, tmp_path)  # no tuned_configs dir
        fake_generator = MagicMock()

        with patch.object(svc_module, "create_datafeed"), \
             patch.object(svc_module, "RealtimeSignalGenerator", return_value=fake_generator) as mock_generator_cls, \
             patch.object(svc_module, "SignalOutcomeTracker"):
            worker._run()

        strategy = mock_generator_cls.call_args.kwargs["strategy"]
        assert strategy.rules_enabled == {"asian_range_london_breakout": False}

    def test_xauusd_worker_still_loads_1h_json_by_filename(self, tmp_path, monkeypatch):
        """Regression: tuned config path must come from
        spec.tuned_config_filename, not f'{timeframe}.json' derivation."""
        from signals.gold_strategy import GoldStrategy
        monkeypatch.setattr(svc_module, "__file__", str(tmp_path / "run_multi_timeframe_service.py"))
        tuned_dir = tmp_path / "tuned_configs"
        tuned_dir.mkdir()
        (tuned_dir / "1h.json").write_text(json.dumps({
            "config": {**GoldStrategy.DEFAULT_CONFIG, "trend_lookback": 200},
            "enabled_rules": ["order_block_retest"],
            "expiry_hours": 143,
        }))
        worker = make_worker(svc_module.XAUUSD_1H_SPEC, tmp_path)
        fake_generator = MagicMock()

        with patch.object(svc_module, "create_datafeed"), \
             patch.object(svc_module, "RealtimeSignalGenerator", return_value=fake_generator), \
             patch.object(svc_module, "SignalOutcomeTracker") as mock_tracker_cls:
            worker._run()

        assert mock_tracker_cls.call_args.kwargs["expiry_hours"] == 143

    def test_gbpusd_lookback_periods_does_not_crash_on_missing_trend_lookback(self, tmp_path, monkeypatch):
        """ForexSessionStrategy.config has no trend_lookback key at all (its
        own gate is lookback_candles + atr_period) — the existing
        lookback_periods calculation assumed every strategy has
        trend_lookback and would KeyError here without the fix."""
        monkeypatch.setattr(svc_module, "__file__", str(tmp_path / "run_multi_timeframe_service.py"))
        worker = make_worker(svc_module.GBPUSD_1H_SPEC, tmp_path)  # no tuned_configs dir — untuned default branch
        fake_generator = MagicMock()

        with patch.object(svc_module, "create_datafeed") as mock_create_feed, \
             patch.object(svc_module, "RealtimeSignalGenerator", return_value=fake_generator) as mock_generator_cls, \
             patch.object(svc_module, "SignalOutcomeTracker"):
            worker._run()  # must not raise KeyError

        # lookback_candles=12 + atr_period=14 + 50 = 76, floored to 200 by max(200, ...).
        assert mock_create_feed.call_args.kwargs["lookback_periods"] == 200
        assert mock_generator_cls.call_args.kwargs["lookback_periods"] == 200

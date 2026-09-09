"""
Regression test for the zero-live-signals bug: GoldStrategy.evaluate() silently
returns None whenever current_idx < max(config['trend_lookback'], 60), but the
data feed/generator defaulted lookback_periods to 200 regardless of what the
loaded tuned config actually required, which happened to exactly equal the 1h
tuned config's trend_lookback=200 -- current_idx maxes out at 199, so no rule
could ever fire.
"""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import run_multi_timeframe_service as svc_module
from signals.gold_strategy import GoldStrategy


def make_worker(timeframe="1h"):
    worker = svc_module.TimeframeWorker.__new__(svc_module.TimeframeWorker)
    worker.timeframe = timeframe
    worker.database_url = "sqlite:///:memory:"
    worker.shared_dedup_subscriber = MagicMock()
    worker.telegram_subscriber = MagicMock()
    worker.enable_trading = False
    worker.mt5_config = None
    return worker


class TestLookbackPeriodsSizing:
    def test_sized_above_tuned_trend_lookback(self, tmp_path, monkeypatch):
        """The 1h tuned config's trend_lookback=200 must not be met exactly by
        lookback_periods=200, since current_idx tops out at count - 1."""
        tuned_dir = tmp_path / "tuned_configs"
        tuned_dir.mkdir()
        (tuned_dir / "1h.json").write_text(json.dumps({
            "config": {**GoldStrategy.DEFAULT_CONFIG, "trend_lookback": 200},
            "enabled_rules": ["order_block_retest"],
            "expiry_hours": 143,
        }))
        monkeypatch.setattr(svc_module, "__file__", str(tmp_path / "run_multi_timeframe_service.py"))

        worker = make_worker("1h")
        fake_generator = MagicMock()

        with patch.object(svc_module, "create_datafeed") as mock_create_feed, \
             patch.object(svc_module, "RealtimeSignalGenerator", return_value=fake_generator) as mock_generator_cls, \
             patch.object(svc_module, "SignalOutcomeTracker"):
            worker._run()

        assert mock_create_feed.call_args.kwargs["lookback_periods"] > 200
        assert mock_generator_cls.call_args.kwargs["lookback_periods"] > 200
        assert mock_create_feed.call_args.kwargs["lookback_periods"] == \
            mock_generator_cls.call_args.kwargs["lookback_periods"]
        fake_generator.start.assert_called_once()

    def test_no_tuned_config_still_covers_default_gate(self, tmp_path, monkeypatch):
        """With no tuned config, GoldStrategy defaults trend_lookback=50 (gate floors at 60),
        so lookback_periods must stay comfortably above that too."""
        monkeypatch.setattr(svc_module, "__file__", str(tmp_path / "run_multi_timeframe_service.py"))

        worker = make_worker("4h")  # no tuned_configs/4h.json exists
        fake_generator = MagicMock()

        with patch.object(svc_module, "create_datafeed") as mock_create_feed, \
             patch.object(svc_module, "RealtimeSignalGenerator", return_value=fake_generator), \
             patch.object(svc_module, "SignalOutcomeTracker"):
            worker._run()

        assert mock_create_feed.call_args.kwargs["lookback_periods"] >= 200

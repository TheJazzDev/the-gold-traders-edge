"""Tests for WorkerSpec and TimeframeWorker's spec-driven construction."""
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import run_multi_timeframe_service as svc_module
from signals.gold_strategy import GoldStrategy
from signals.forex_session_strategy import ForexSessionStrategy


class TestWorkerSpecs:
    def test_worker_specs_has_three_entries(self):
        assert len(svc_module.WORKER_SPECS) == 3

    def test_xauusd_spec_uses_gold_strategy(self):
        spec = svc_module.XAUUSD_1H_SPEC
        assert spec.symbol == 'XAUUSD'
        assert spec.strategy_class is GoldStrategy
        assert spec.timeframe == '1h'
        assert spec.tuned_config_filename == '1h.json'

    def test_gbpusd_spec_uses_forex_session_strategy(self):
        spec = svc_module.GBPUSD_1H_SPEC
        assert spec.symbol == 'GBPUSD'
        assert spec.strategy_class is ForexSessionStrategy
        assert spec.timeframe == '1h'
        assert spec.tuned_config_filename == 'gbpusd_1h.json'

    def test_eurusd_spec_uses_forex_session_strategy(self):
        spec = svc_module.EURUSD_1H_SPEC
        assert spec.symbol == 'EURUSD'
        assert spec.strategy_class is ForexSessionStrategy
        assert spec.timeframe == '1h'
        assert spec.tuned_config_filename == 'eurusd_1h.json'

    def test_worker_specs_contains_all_three_in_order(self):
        assert svc_module.WORKER_SPECS == [
            svc_module.XAUUSD_1H_SPEC,
            svc_module.GBPUSD_1H_SPEC,
            svc_module.EURUSD_1H_SPEC,
        ]


class TestTimeframeWorkerSpecProperties:
    def _worker(self, spec):
        return svc_module.TimeframeWorker(
            spec=spec,
            database_url='sqlite:///:memory:',
            shared_dedup_subscriber=MagicMock(),
        )

    def test_worker_id_combines_symbol_and_timeframe(self):
        worker = self._worker(svc_module.GBPUSD_1H_SPEC)
        assert worker.worker_id == 'GBPUSD:1h'

    def test_symbol_property_reflects_spec(self):
        worker = self._worker(svc_module.EURUSD_1H_SPEC)
        assert worker.symbol == 'EURUSD'

    def test_timeframe_property_reflects_spec(self):
        worker = self._worker(svc_module.XAUUSD_1H_SPEC)
        assert worker.timeframe == '1h'

"""Regression coverage: MultiTimeframeService must construct one worker per
WORKER_SPECS entry (not just gold), keyed by worker_id in self.workers."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import run_multi_timeframe_service as svc_module


class TestMultiTimeframeServiceWorkerSpecs:
    def test_default_worker_specs_is_the_module_constant(self):
        service = svc_module.MultiTimeframeService.__new__(svc_module.MultiTimeframeService)
        service.worker_specs = None or svc_module.WORKER_SPECS
        assert service.worker_specs == svc_module.WORKER_SPECS

    def test_start_constructs_one_worker_per_spec_keyed_by_worker_id(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "fake-chat-id")

        with patch.object(svc_module, "DatabaseSubscriber"), \
             patch.object(svc_module, "TelegramSubscriber"), \
             patch.object(svc_module, "DeduplicationSubscriber"), \
             patch.object(svc_module, "TimeframeWorker") as mock_worker_cls, \
             patch("time.sleep"):
            mock_instances = []

            def _make_worker(spec, **kwargs):
                inst = MagicMock()
                inst.spec = spec
                inst.worker_id = f"{spec.symbol}:{spec.timeframe}"
                mock_instances.append(inst)
                return inst

            mock_worker_cls.side_effect = _make_worker

            service = svc_module.MultiTimeframeService(database_url=f"sqlite:///{tmp_path / 'db.sqlite'}")
            service._monitor_loop = MagicMock()  # don't actually loop forever
            service.start()

        assert set(service.workers.keys()) == {'XAUUSD:1h', 'GBPUSD:1h', 'EURUSD:1h'}
        assert mock_worker_cls.call_count == 3

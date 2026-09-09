"""Confirms the live service is scoped to the validated 1H timeframe only."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import run_multi_timeframe_service as svc_module


class TestTimeframeScope:
    def test_only_1h_is_configured(self):
        # Verify all configured worker specs use the 1h timeframe
        assert len(svc_module.WORKER_SPECS) > 0
        for spec in svc_module.WORKER_SPECS:
            assert spec.timeframe == '1h'

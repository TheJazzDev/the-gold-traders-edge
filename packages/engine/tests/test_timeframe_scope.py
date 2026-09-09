"""Confirms every configured worker runs the validated 1H timeframe, and
exactly the three instruments this design wires in."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import run_multi_timeframe_service as svc_module


class TestTimeframeScope:
    def test_every_worker_spec_is_1h(self):
        assert all(spec.timeframe == '1h' for spec in svc_module.WORKER_SPECS)

    def test_worker_specs_cover_exactly_these_symbols(self):
        assert {spec.symbol for spec in svc_module.WORKER_SPECS} == {'XAUUSD', 'GBPUSD', 'EURUSD'}

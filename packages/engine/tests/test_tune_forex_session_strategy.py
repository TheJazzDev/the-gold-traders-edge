"""B5 for the forex tuner: live gates and a warmed-up test slice."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from signals.forex_session_strategy import ForexSessionStrategy
from tune_forex_session_strategy import slice_warmup_candles


class TestSliceWarmup:
    def test_covers_the_strategy_gate(self):
        config = dict(ForexSessionStrategy.DEFAULT_CONFIG)
        assert slice_warmup_candles(config) == 12 + 14 + 50

    def test_covers_the_trend_gate_when_on(self):
        config = {**ForexSessionStrategy.DEFAULT_CONFIG, 'htf_trend_filter': True}
        assert slice_warmup_candles(config) == 600 + 50

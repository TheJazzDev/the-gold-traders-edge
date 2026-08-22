"""Tests for RealtimeSignalGenerator."""
import sys
from pathlib import Path
import logging

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from signals.gold_strategy import GoldStrategy
from signals.realtime_generator import RealtimeSignalGenerator, SignalValidator


class FakeDataFeed:
    """Minimal stand-in for RealtimeDataFeed, just enough to construct a generator."""
    symbol = "XAUUSD"
    timeframe = "1h"
    is_connected = True

    def connect(self):
        return True

    def disconnect(self):
        return True

    def get_latest_candles(self, count):
        import pandas as pd
        return pd.DataFrame()  # Empty DataFrame stops iteration

    def wait_for_candle_close(self, check_interval):
        raise StopIteration  # Exit loop immediately


class TestStrategyLogLine:
    def test_start_logs_actual_enabled_rules(self, caplog):
        strategy = GoldStrategy()
        for name in strategy.rules_enabled:
            strategy.rules_enabled[name] = False
        strategy.rules_enabled['london_session_breakout'] = True

        generator = RealtimeSignalGenerator(
            data_feed=FakeDataFeed(),
            strategy=strategy,
            validator=SignalValidator(),
        )

        with caplog.at_level(logging.INFO):
            generator.start(max_iterations=0)

        messages = [r.message for r in caplog.records]
        assert any("london_session_breakout" in m for m in messages), messages
        assert not any(m == "Strategy: Momentum Equilibrium" for m in messages), messages

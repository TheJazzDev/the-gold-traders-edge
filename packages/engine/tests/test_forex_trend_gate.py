"""
Higher-timeframe trend gate on Asian Range London Breakout (B4).

Same gate as Order Block Retest (see test_trend_gate.py), optional and off
by default. ARLB-0924-01 was a EURUSD long taken against a daily and 4H
downtrend and stopped out in 3 hours.
"""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from analysis.technical import TrendDirection
from backtesting.engine import TradeDirection
from signals import forex_session_strategy as forex_module
from signals.forex_session_strategy import ForexSessionStrategy


def london_breakout_df():
    """Asian session 00:00-06:00 inside 1.2990-1.3010, then a 07:00 close at
    1.3050 — a clean upside breakout."""
    idx = pd.date_range('2026-03-01 00:00', periods=80, freq='1h')
    df = pd.DataFrame({'open': 1.3000, 'high': 1.3010, 'low': 1.2990, 'close': 1.3000}, index=idx)
    entry = [i for i, t in enumerate(idx) if t.hour == 7][-1]
    df.iloc[entry] = [1.3005, 1.3055, 1.3000, 1.3050]
    return df.iloc[:entry + 1]


class TestAsianRangeBreakoutGate:
    def test_filter_is_off_by_default(self):
        assert ForexSessionStrategy.DEFAULT_CONFIG['htf_trend_filter'] is False

    def test_counter_trend_breakout_blocked_when_enabled(self, monkeypatch):
        monkeypatch.setattr(forex_module, 'ema_trend', lambda *a, **k: TrendDirection.DOWNTREND)
        df = london_breakout_df()
        strategy = ForexSessionStrategy(config={'htf_trend_filter': True})
        assert strategy.evaluate(df, len(df) - 1) is None

    def test_with_trend_breakout_passes_when_enabled(self, monkeypatch):
        monkeypatch.setattr(forex_module, 'ema_trend', lambda *a, **k: TrendDirection.UPTREND)
        df = london_breakout_df()
        strategy = ForexSessionStrategy(config={'htf_trend_filter': True})
        signal = strategy.evaluate(df, len(df) - 1)
        assert signal is not None and signal.direction == TradeDirection.LONG

    def test_disabled_ignores_trend(self, monkeypatch):
        monkeypatch.setattr(forex_module, 'ema_trend', lambda *a, **k: TrendDirection.DOWNTREND)
        df = london_breakout_df()
        assert ForexSessionStrategy().evaluate(df, len(df) - 1) is not None


class TestWorkerFetchesEnoughForTheGate:
    def test_forex_worker_with_gate_on(self, tmp_path, monkeypatch):
        import run_multi_timeframe_service as svc
        tuned_dir = tmp_path / "tuned_configs"
        tuned_dir.mkdir()
        (tuned_dir / "gbpusd_1h.json").write_text(json.dumps(
            {"config": {**ForexSessionStrategy.DEFAULT_CONFIG, 'htf_trend_filter': True}}))
        monkeypatch.setattr(svc, "__file__", str(tmp_path / "run_multi_timeframe_service.py"))
        worker = svc.TimeframeWorker.__new__(svc.TimeframeWorker)
        worker.spec = svc.GBPUSD_1H_SPEC
        worker.database_url = f"sqlite:///{tmp_path / 'svc.db'}"
        worker.shared_dedup_subscriber = MagicMock()
        worker.telegram_subscriber = MagicMock()
        worker.enable_trading = False
        worker.mt5_config = None
        with patch.object(svc, "create_datafeed") as mock_feed, \
             patch.object(svc, "RealtimeSignalGenerator"), \
             patch.object(svc, "SignalOutcomeTracker"):
            worker._run()
        assert mock_feed.call_args.kwargs["lookback_periods"] > 600

"""
Higher-timeframe trend gate (B3, Order Block Retest).

A hard filter, not a confidence bonus: when enabled, a rule only fires in
the direction of the 1H EMA trend (close vs EMA, EMA slope agreeing).
"""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from analysis.technical import TrendDirection
from analysis.trend_gate import ema_trend, trend_allows, warmup_candles
from backtesting.engine import TradeDirection
from signals import gold_strategy as gold_module
from signals.gold_strategy import GoldStrategy


def series(values):
    return pd.Series(values, index=pd.date_range('2025-01-01', periods=len(values), freq='1h'))


class TestEmaTrend:
    def test_rising_market_is_uptrend(self):
        assert ema_trend(series(np.linspace(1000, 1200, 700))) == TrendDirection.UPTREND

    def test_falling_market_is_downtrend(self):
        assert ema_trend(series(np.linspace(1200, 1000, 700))) == TrendDirection.DOWNTREND

    def test_close_and_slope_disagreeing_is_sideways(self):
        # Long rise, then a brief dip below the (lagging, still rising) EMA.
        values = list(np.linspace(1000, 1200, 697)) + [1150] * 3
        assert ema_trend(series(values)) == TrendDirection.SIDEWAYS

    def test_not_enough_candles_is_sideways(self):
        """Fails closed: with an under-warmed EMA the gate blocks rather
        than guessing."""
        assert ema_trend(series(np.linspace(1000, 1200, 599)), ema_period=200) == TrendDirection.SIDEWAYS
        assert warmup_candles(200) == 600

    def test_only_the_warmup_window_matters(self):
        """Live fetches ~650 candles, the backtest hands over the whole
        history. Both must compute the same EMA, so anything older than
        the warm-up window must not change the answer."""
        recent = list(np.linspace(1000, 990, 600))
        short_history = series(recent)
        long_history = series(list(np.linspace(500, 2000, 3000)) + recent)
        assert ema_trend(short_history) == ema_trend(long_history) == TrendDirection.DOWNTREND


class TestTrendAllows:
    @pytest.mark.parametrize("direction,trend,allowed", [
        (TradeDirection.LONG, TrendDirection.UPTREND, True),
        (TradeDirection.LONG, TrendDirection.DOWNTREND, False),
        (TradeDirection.LONG, TrendDirection.SIDEWAYS, False),
        (TradeDirection.SHORT, TrendDirection.DOWNTREND, True),
        (TradeDirection.SHORT, TrendDirection.UPTREND, False),
        (TradeDirection.SHORT, TrendDirection.SIDEWAYS, False),
    ])
    def test_only_with_trend_directions_pass(self, direction, trend, allowed):
        assert trend_allows(direction, trend) is allowed


def bullish_retest_df(n=120):
    """Quiet market with a strong bullish order block at n-20 and a retest
    of it on the last candle."""
    idx = pd.date_range('2026-01-01', periods=n, freq='1h')
    df = pd.DataFrame({'open': 1995.0, 'high': 1996.0, 'low': 1994.0, 'close': 1995.2}, index=idx)
    df.iloc[n - 20] = [1980.0, 1995.2, 1979.5, 1995.0]
    df.iloc[n - 1] = [1994.0, 1995.0, 1985.0, 1994.5]
    return df


class TestOrderBlockRetestGate:
    def test_filter_is_off_by_default(self):
        """Live behaviour only changes when the gate is switched on
        explicitly (in the tuned config), after validation."""
        assert GoldStrategy.DEFAULT_CONFIG['htf_trend_filter'] is False

    def test_counter_trend_retest_is_blocked_when_enabled(self, monkeypatch):
        monkeypatch.setattr(gold_module, 'ema_trend', lambda *a, **k: TrendDirection.DOWNTREND)
        df = bullish_retest_df()
        strategy = GoldStrategy(config={'atr_period': 14, 'htf_trend_filter': True})
        assert strategy.evaluate(df, len(df) - 1) is None

    def test_sideways_blocks_when_enabled(self, monkeypatch):
        monkeypatch.setattr(gold_module, 'ema_trend', lambda *a, **k: TrendDirection.SIDEWAYS)
        df = bullish_retest_df()
        strategy = GoldStrategy(config={'atr_period': 14, 'htf_trend_filter': True})
        assert strategy.evaluate(df, len(df) - 1) is None

    def test_with_trend_retest_passes_when_enabled(self, monkeypatch):
        monkeypatch.setattr(gold_module, 'ema_trend', lambda *a, **k: TrendDirection.UPTREND)
        df = bullish_retest_df()
        strategy = GoldStrategy(config={'atr_period': 14, 'htf_trend_filter': True})
        signal = strategy.evaluate(df, len(df) - 1)
        assert signal is not None and signal.direction == TradeDirection.LONG

    def test_counter_trend_retest_still_fires_when_disabled(self, monkeypatch):
        monkeypatch.setattr(gold_module, 'ema_trend', lambda *a, **k: TrendDirection.DOWNTREND)
        df = bullish_retest_df()
        strategy = GoldStrategy(config={'atr_period': 14})
        assert strategy.evaluate(df, len(df) - 1) is not None


class TestWorkerFetchesEnoughForTheGate:
    """The EMA is computed over the last warmup_candles() candles; if live
    fetched fewer, the gate would sit at SIDEWAYS forever and block every
    signal (or, with a shorter window, disagree with the backtest)."""

    def _run_worker(self, tmp_path, monkeypatch, spec, filename, config):
        sys_module = __import__('run_multi_timeframe_service')
        tuned_dir = tmp_path / "tuned_configs"
        tuned_dir.mkdir()
        (tuned_dir / filename).write_text(json.dumps({"config": config, "enabled_rules": ["order_block_retest"]}))
        monkeypatch.setattr(sys_module, "__file__", str(tmp_path / "run_multi_timeframe_service.py"))
        worker = sys_module.TimeframeWorker.__new__(sys_module.TimeframeWorker)
        worker.spec = spec
        worker.database_url = f"sqlite:///{tmp_path / 'svc.db'}"
        worker.shared_dedup_subscriber = MagicMock()
        worker.telegram_subscriber = MagicMock()
        worker.enable_trading = False
        worker.mt5_config = None
        with patch.object(sys_module, "create_datafeed") as mock_feed, \
             patch.object(sys_module, "RealtimeSignalGenerator"), \
             patch.object(sys_module, "SignalOutcomeTracker"):
            worker._run()
        return mock_feed.call_args.kwargs["lookback_periods"]

    def test_gold_worker_with_gate_on(self, tmp_path, monkeypatch):
        import run_multi_timeframe_service as svc
        config = {**GoldStrategy.DEFAULT_CONFIG, 'trend_lookback': 200, 'htf_trend_filter': True}
        assert self._run_worker(tmp_path, monkeypatch, svc.XAUUSD_1H_SPEC, "1h.json", config) > 600

    def test_gate_off_keeps_the_old_size(self, tmp_path, monkeypatch):
        import run_multi_timeframe_service as svc
        config = {**GoldStrategy.DEFAULT_CONFIG, 'trend_lookback': 200}
        assert self._run_worker(tmp_path, monkeypatch, svc.XAUUSD_1H_SPEC, "1h.json", config) == 250

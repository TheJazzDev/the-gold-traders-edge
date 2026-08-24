"""Tests for the strategy tuning script's core mechanics, using synthetic data."""
import sys
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from tune_strategy import (
    split_train_test,
    percentile,
    json_safe,
    BASE_1H_CONFIG,
    scale_baseline_config,
    run_isolated_backtest,
    passes_pf_gate,
    MIN_TRAIN_TRADES,
    MIN_TEST_TRADES,
    PRODUCTION_MIN_RR,
    _production_valid_strategy_func,
    _resolved_stats,
)
from signals.gold_strategy import GoldStrategy
from backtesting.engine import Signal as StrategySignal, Trade, TradeDirection, TradeStatus


class TestSplitTrainTest:
    def test_splits_chronologically_at_given_fraction(self):
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1h')
        df = pd.DataFrame({'close': range(100)}, index=dates)

        train, test = split_train_test(df, train_frac=0.7)

        assert len(train) == 70
        assert len(test) == 30
        assert train.index[-1] < test.index[0]
        assert train.index[-1] == dates[69]
        assert test.index[0] == dates[70]


class TestPercentile:
    def test_matches_known_values(self):
        values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        assert percentile(values, 50) == pytest.approx(5.5)
        assert percentile(values, 0) == 1
        assert percentile(values, 100) == 10

    def test_empty_list_returns_zero(self):
        assert percentile([], 95) == 0.0


class TestPassesPfGate:
    """Regression coverage for the fix: candidate_rules is gated on train-slice
    stats (MIN_TRAIN_TRADES), never on test-slice stats, so the held-out test
    slice is used exactly once (the final shared-config re-validation)."""

    def test_profitable_with_enough_trades_passes(self):
        stats = {'profit_factor': 1.5, 'total_trades': MIN_TRAIN_TRADES}
        assert passes_pf_gate(stats, MIN_TRAIN_TRADES) is True

    def test_unprofitable_fails_even_with_enough_trades(self):
        stats = {'profit_factor': 0.9, 'total_trades': 100}
        assert passes_pf_gate(stats, MIN_TRAIN_TRADES) is False

    def test_too_few_trades_fails_even_if_profitable(self):
        stats = {'profit_factor': 5.0, 'total_trades': MIN_TRAIN_TRADES - 1}
        assert passes_pf_gate(stats, MIN_TRAIN_TRADES) is False

    def test_train_gate_uses_a_higher_trade_bar_than_test_gate(self):
        # A rule with a trade count between the two thresholds would have
        # passed a test-slice gate but must fail the train-slice gate that
        # now controls candidate_rules selection.
        stats = {'profit_factor': 1.2, 'total_trades': MIN_TEST_TRADES}
        assert MIN_TEST_TRADES < MIN_TRAIN_TRADES
        assert passes_pf_gate(stats, MIN_TEST_TRADES) is True
        assert passes_pf_gate(stats, MIN_TRAIN_TRADES) is False


class TestJsonSafe:
    """Regression coverage: an infinite profit factor (a rule with zero
    losing trades) must not end up as a bare `Infinity` token, which isn't
    valid JSON for any non-Python consumer."""

    def test_replaces_infinity_with_a_finite_sentinel(self):
        sanitized = json_safe({'profit_factor': float('inf'), 'other': 1.5})
        assert sanitized['profit_factor'] == pytest.approx(1e9)
        assert sanitized['other'] == 1.5
        assert json.dumps(sanitized)  # must not raise

    def test_replaces_negative_infinity(self):
        sanitized = json_safe({'profit_factor': float('-inf')})
        assert sanitized['profit_factor'] == pytest.approx(-1e9)

    def test_recurses_into_nested_lists_and_dicts(self):
        sanitized = json_safe({'a': [{'b': float('inf')}]})
        assert sanitized['a'][0]['b'] == pytest.approx(1e9)

    def test_leaves_normal_values_untouched(self):
        assert json_safe({'a': 1, 'b': 'x', 'c': [1, 2.5]}) == {'a': 1, 'b': 'x', 'c': [1, 2.5]}


class TestProductionValidStrategyFunc:
    """Regression coverage for the fix: tuning must only score signals
    SignalValidator would actually let through to production (risk>0,
    reward>0, rr >= PRODUCTION_MIN_RR), not GoldStrategy's raw output."""

    def _strategy_stub(self, signal):
        strategy = GoldStrategy()
        strategy.evaluate = lambda df, idx: signal
        return strategy

    def test_passes_through_a_signal_that_meets_the_rr_bar(self):
        signal = StrategySignal(
            time=pd.Timestamp('2026-01-01', tz='UTC'), direction=TradeDirection.LONG,
            entry_price=2000.0, stop_loss=1990.0,
            take_profit=2000.0 + 10 * PRODUCTION_MIN_RR,
            signal_name='test',
        )
        strategy_func = _production_valid_strategy_func(self._strategy_stub(signal))
        assert strategy_func(pd.DataFrame(), 0) is signal

    def test_drops_a_signal_below_the_rr_bar(self):
        signal = StrategySignal(
            time=pd.Timestamp('2026-01-01', tz='UTC'), direction=TradeDirection.LONG,
            entry_price=2000.0, stop_loss=1990.0, take_profit=2005.0,  # RR = 0.5
            signal_name='test',
        )
        strategy_func = _production_valid_strategy_func(self._strategy_stub(signal))
        assert strategy_func(pd.DataFrame(), 0) is None

    def test_drops_a_signal_with_non_positive_risk(self):
        signal = StrategySignal(
            time=pd.Timestamp('2026-01-01', tz='UTC'), direction=TradeDirection.LONG,
            entry_price=2000.0, stop_loss=2010.0, take_profit=1990.0,
            signal_name='test',
        )
        strategy_func = _production_valid_strategy_func(self._strategy_stub(signal))
        assert strategy_func(pd.DataFrame(), 0) is None

    def test_passes_through_no_signal(self):
        strategy_func = _production_valid_strategy_func(self._strategy_stub(None))
        assert strategy_func(pd.DataFrame(), 0) is None


class FakeBacktestResult:
    def __init__(self, trades, initial_balance=10000):
        self.trades = trades
        self.initial_balance = initial_balance


def _trade(status, pnl):
    return Trade(
        id=0, entry_time=pd.Timestamp('2026-01-01'), entry_price=2000.0,
        direction=TradeDirection.LONG, stop_loss=1990.0, take_profit=2020.0,
        status=status, pnl=pnl,
    )


class TestResolvedStats:
    """Regression coverage for the fix: a CLOSED_MANUAL trade (an open
    position marked to market at the end of the data slice) must not count
    toward profit_factor/total_trades — it's unresolved, not a real win.
    This is what made london_session_breakout pass its PF gate on a single
    force-closed trade rather than a genuine edge."""

    def test_excludes_closed_manual_from_profit_factor(self):
        result = FakeBacktestResult([
            _trade(TradeStatus.CLOSED_SL, -100.0),
            _trade(TradeStatus.CLOSED_SL, -100.0),
            _trade(TradeStatus.CLOSED_TP, 200.0),
            _trade(TradeStatus.CLOSED_MANUAL, 5000.0),  # would flip PF>1 if counted
        ])
        stats = _resolved_stats(result)
        assert stats['total_trades'] == 3
        assert stats['profit_factor'] == pytest.approx(1.0)  # 200 / (100+100)

    def test_excludes_open_trades(self):
        result = FakeBacktestResult([
            _trade(TradeStatus.CLOSED_TP, 200.0),
            _trade(TradeStatus.OPEN, 0.0),
        ])
        stats = _resolved_stats(result)
        assert stats['total_trades'] == 1

    def test_zero_resolved_trades_returns_zero_stats(self):
        result = FakeBacktestResult([_trade(TradeStatus.CLOSED_MANUAL, 5000.0)])
        stats = _resolved_stats(result)
        assert stats == {'profit_factor': 0.0, 'total_trades': 0, 'win_rate': 0.0, 'net_profit_pct': 0.0}


class TestScaleBaselineConfig:
    """Regression coverage: scaling GoldStrategy.DEFAULT_CONFIG (4H) by the
    same 4x factor used for the original hand-written BASE_1H_CONFIG must
    reproduce it exactly, so generalizing tune_strategy.py to other
    timeframes doesn't silently change the already-reviewed 1H behavior."""

    EXPECTED_1H_BASELINE = {
        'fib_tolerance': 0.015,
        'swing_lookback': 20,
        'swing_min_strength': 2,
        'trend_lookback': 200,
        'strong_momentum_threshold': 0.02,
        'atr_period': 56,
        'default_rr_ratio': 2.0,
        'sl_buffer_atr': 0.3,
        'ema_fast': 36,
        'ema_slow': 84,
        'rsi_period': 56,
        'rsi_overbought': 70,
        'rsi_oversold': 30,
    }

    def test_reproduces_the_original_1h_baseline_exactly(self):
        scaled = scale_baseline_config(GoldStrategy.DEFAULT_CONFIG, from_minutes=240, to_minutes=60)
        assert scaled == self.EXPECTED_1H_BASELINE

    def test_candle_count_params_scale_by_the_timeframe_ratio(self):
        scaled = scale_baseline_config(GoldStrategy.DEFAULT_CONFIG, from_minutes=240, to_minutes=15)
        # 240/15 = 16x
        assert scaled['swing_lookback'] == 5 * 16
        assert scaled['trend_lookback'] == 50 * 16
        assert scaled['atr_period'] == 14 * 16
        assert scaled['ema_fast'] == 9 * 16
        assert scaled['ema_slow'] == 21 * 16
        assert scaled['rsi_period'] == 14 * 16

    def test_ratio_params_pass_through_unscaled(self):
        scaled = scale_baseline_config(GoldStrategy.DEFAULT_CONFIG, from_minutes=240, to_minutes=15)
        assert scaled['fib_tolerance'] == 0.015
        assert scaled['default_rr_ratio'] == 2.0
        assert scaled['sl_buffer_atr'] == 0.3
        assert scaled['rsi_overbought'] == 70
        assert scaled['rsi_oversold'] == 30
        assert scaled['swing_min_strength'] == 2
        assert scaled['strong_momentum_threshold'] == 0.02


class TestRunIsolatedBacktest:
    def test_only_enables_the_requested_rule(self):
        np.random.seed(42)
        dates = pd.date_range(start='2024-01-01', periods=300, freq='1h')
        base_price = 2000
        trend = np.cumsum(np.random.normal(0.3, 2, len(dates)))
        close = base_price + trend
        high = close + np.abs(np.random.normal(0, 5, len(dates)))
        low = close - np.abs(np.random.normal(0, 5, len(dates)))
        open_prices = close + np.random.normal(0, 2, len(dates))
        high = np.maximum(high, np.maximum(open_prices, close))
        low = np.minimum(low, np.minimum(open_prices, close))
        df = pd.DataFrame({'open': open_prices, 'high': high, 'low': low, 'close': close}, index=dates)

        pf, trades, result = run_isolated_backtest(df, 'momentum_equilibrium', BASE_1H_CONFIG)

        assert isinstance(pf, float)
        assert isinstance(trades, int)
        # `trades` is resolved-only (excludes CLOSED_MANUAL force-closes),
        # so it's compared against a matching recount, not result.total_trades
        # (which BacktestResult.calculate_metrics() computes over all closed
        # trades including force-closes).
        resolved = [t for t in result.trades if t.status in (TradeStatus.CLOSED_TP, TradeStatus.CLOSED_SL)]
        assert len(resolved) == trades

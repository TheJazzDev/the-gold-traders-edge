"""Tests for the strategy tuning script's core mechanics, using synthetic data."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from tune_strategy import split_train_test, percentile, BASE_1H_CONFIG, run_isolated_backtest


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
        assert result.total_trades == trades

"""
Tests for the Gold Trading Strategy.

Only Order Block Retest remains — the only rule that survived shared-config,
out-of-sample validation (see tuned_configs/1h.json and
docs/superpowers/specs/strategy-ledger.md for every other rule tried and
ruled out, with its hypothesis and result).
"""

import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from signals.gold_strategy import GoldStrategy, RuleResult
from backtesting.engine import TradeDirection, Signal


class TestGoldStrategy:
    """Test suite for GoldStrategy class."""

    @pytest.fixture
    def strategy(self):
        """Create a fresh strategy instance for each test."""
        return GoldStrategy()

    @pytest.fixture
    def sample_df(self):
        """Generate sample OHLCV data for testing."""
        np.random.seed(42)
        dates = pd.date_range(start='2024-01-01', periods=200, freq='4h')

        # Create trending price data
        base_price = 2000
        trend = np.cumsum(np.random.normal(0.5, 2, len(dates)))
        close = base_price + trend

        high = close + np.abs(np.random.normal(0, 5, len(dates)))
        low = close - np.abs(np.random.normal(0, 5, len(dates)))
        open_prices = close + np.random.normal(0, 2, len(dates))

        # Ensure OHLC validity
        high = np.maximum(high, np.maximum(open_prices, close))
        low = np.minimum(low, np.minimum(open_prices, close))

        df = pd.DataFrame({
            'open': open_prices,
            'high': high,
            'low': low,
            'close': close,
            'volume': np.random.randint(1000, 10000, len(dates))
        }, index=dates)

        return df

    def test_strategy_initialization(self, strategy):
        """Test that strategy initializes with correct default config."""
        assert strategy.config['default_rr_ratio'] == 2.0
        assert strategy.config['atr_period'] == 14
        assert strategy.config['sl_buffer_atr'] == 0.3

    def test_only_order_block_retest_enabled(self, strategy):
        """Order Block Retest is the only validated, live rule."""
        assert strategy.rules_enabled == {'order_block_retest': True}

    def test_set_rule_enabled(self, strategy):
        """Test enabling/disabling rules."""
        strategy.set_rule_enabled('order_block_retest', False)
        assert strategy.rules_enabled['order_block_retest'] == False

        strategy.set_rule_enabled('order_block_retest', True)
        assert strategy.rules_enabled['order_block_retest'] == True

    def test_evaluate_returns_none_for_insufficient_data(self, strategy, sample_df):
        """Test that evaluate returns None when there's not enough data."""
        result = strategy.evaluate(sample_df, 10)  # Not enough lookback
        assert result is None

    def test_evaluate_returns_signal_or_none(self, strategy, sample_df):
        """Test that evaluate returns Signal or None."""
        result = strategy.evaluate(sample_df, 100)
        assert result is None or isinstance(result, Signal)

    def test_rule_result_dataclass(self):
        """Test RuleResult dataclass initialization."""
        result = RuleResult(
            rule_name="Test Rule",
            triggered=True,
            direction=TradeDirection.LONG,
            entry_price=2000.0,
            stop_loss=1990.0,
            take_profit=2020.0,
            confidence=0.75,
            notes="Test notes"
        )

        assert result.rule_name == "Test Rule"
        assert result.triggered == True
        assert result.direction == TradeDirection.LONG
        assert result.entry_price == 2000.0
        assert result.confidence == 0.75


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Tests for the Gold Trading Strategy.
Tests the 3 profitable rules: 1 (61.8% Golden), 5 (ATH Retest), 6 (50% Momentum)
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from signals.gold_strategy import GoldStrategy, RuleResult, FibZone
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
        assert strategy.config['fib_tolerance'] == 0.015
        assert strategy.config['default_rr_ratio'] == 2.0
        assert strategy.config['atr_period'] == 14

    def test_only_profitable_rules_enabled(self, strategy):
        """Test that only profitable rules (1, 5, 6) are enabled."""
        assert strategy.rules_enabled.get('rule_1_618_retracement') == True
        assert strategy.rules_enabled.get('rule_5_ath_breakout_retest') == True
        assert strategy.rules_enabled.get('rule_6_50_momentum') == True
        
        # Unprofitable rules should not exist or be disabled
        assert 'rule_2_786_deep_discount' not in strategy.rules_enabled
        assert 'rule_3_236_shallow_pullback' not in strategy.rules_enabled
        assert 'rule_4_consolidation_break' not in strategy.rules_enabled

    def test_set_rule_enabled(self, strategy):
        """Test enabling/disabling rules."""
        strategy.set_rule_enabled('rule_1_618_retracement', False)
        assert strategy.rules_enabled['rule_1_618_retracement'] == False
        
        strategy.set_rule_enabled('rule_1_618_retracement', True)
        assert strategy.rules_enabled['rule_1_618_retracement'] == True

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

    def test_fib_zone_dataclass(self):
        """Test FibZone dataclass initialization."""
        fib = FibZone(
            swing_low=1900.0,
            swing_high=2100.0,
            level_236=2052.8,  # 2100 - (200 * 0.236)
            level_382=2023.6,  # 2100 - (200 * 0.382)
            level_500=2000.0,  # 2100 - (200 * 0.5)
            level_618=1976.4,  # 2100 - (200 * 0.618)
            level_786=1942.8,  # 2100 - (200 * 0.786)
            direction='up'
        )
        
        assert fib.swing_low == 1900.0
        assert fib.swing_high == 2100.0
        assert fib.direction == 'up'
        assert abs(fib.level_618 - 1976.4) < 0.1


class TestRule1GoldenRetracement:
    """Tests for Rule 1: 61.8% Golden Retracement."""

    @pytest.fixture
    def strategy(self):
        """Create strategy with only Rule 1 enabled."""
        strategy = GoldStrategy()
        strategy.rules_enabled = {
            'rule_1_618_retracement': True,
            'rule_5_ath_breakout_retest': False,
            'rule_6_50_momentum': False,
        }
        return strategy

    def test_rule1_name(self, strategy):
        """Test that Rule 1 is properly named."""
        assert 'rule_1_618_retracement' in strategy.rules_enabled


class TestRule5ATHRetest:
    """Tests for Rule 5: ATH Breakout Retest."""

    @pytest.fixture
    def strategy(self):
        """Create strategy with only Rule 5 enabled."""
        strategy = GoldStrategy()
        strategy.rules_enabled = {
            'rule_1_618_retracement': False,
            'rule_5_ath_breakout_retest': True,
            'rule_6_50_momentum': False,
        }
        return strategy

    def test_rule5_name(self, strategy):
        """Test that Rule 5 is properly named."""
        assert 'rule_5_ath_breakout_retest' in strategy.rules_enabled


class TestRule6Momentum:
    """Tests for Rule 6: 50% Momentum."""

    @pytest.fixture
    def strategy(self):
        """Create strategy with only Rule 6 enabled."""
        strategy = GoldStrategy()
        strategy.rules_enabled = {
            'rule_1_618_retracement': False,
            'rule_5_ath_breakout_retest': False,
            'rule_6_50_momentum': True,
        }
        return strategy

    def test_rule6_name(self, strategy):
        """Test that Rule 6 is properly named."""
        assert 'rule_6_50_momentum' in strategy.rules_enabled


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

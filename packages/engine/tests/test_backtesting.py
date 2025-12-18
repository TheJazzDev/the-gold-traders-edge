"""
Tests for the Backtesting Engine.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from backtesting.engine import (
    BacktestEngine, BacktestResult, Trade, Signal,
    TradeDirection, TradeStatus
)


class TestTradeClass:
    """Tests for the Trade class."""

    def test_trade_creation(self):
        """Test basic trade creation."""
        trade = Trade(
            id=1,
            entry_time=pd.Timestamp('2024-01-01 10:00:00'),
            entry_price=2000.0,
            direction=TradeDirection.LONG,
            stop_loss=1990.0,
            take_profit=2020.0,
            position_size=1.0
        )
        
        assert trade.id == 1
        assert trade.entry_price == 2000.0
        assert trade.direction == TradeDirection.LONG
        assert trade.status == TradeStatus.OPEN

    def test_trade_close_long_profit(self):
        """Test closing a long trade in profit."""
        trade = Trade(
            id=1,
            entry_time=pd.Timestamp('2024-01-01'),
            entry_price=2000.0,
            direction=TradeDirection.LONG,
            stop_loss=1990.0,
            take_profit=2020.0,
            position_size=1.0
        )
        
        trade.close(
            exit_time=pd.Timestamp('2024-01-02'),
            exit_price=2020.0,
            status=TradeStatus.CLOSED_TP
        )
        
        assert trade.pnl == 20.0
        assert trade.status == TradeStatus.CLOSED_TP

    def test_trade_close_long_loss(self):
        """Test closing a long trade in loss."""
        trade = Trade(
            id=1,
            entry_time=pd.Timestamp('2024-01-01'),
            entry_price=2000.0,
            direction=TradeDirection.LONG,
            stop_loss=1990.0,
            take_profit=2020.0,
            position_size=1.0
        )
        
        trade.close(
            exit_time=pd.Timestamp('2024-01-02'),
            exit_price=1990.0,
            status=TradeStatus.CLOSED_SL
        )
        
        assert trade.pnl == -10.0
        assert trade.status == TradeStatus.CLOSED_SL

    def test_trade_close_short_profit(self):
        """Test closing a short trade in profit."""
        trade = Trade(
            id=1,
            entry_time=pd.Timestamp('2024-01-01'),
            entry_price=2000.0,
            direction=TradeDirection.SHORT,
            stop_loss=2010.0,
            take_profit=1980.0,
            position_size=1.0
        )
        
        trade.close(
            exit_time=pd.Timestamp('2024-01-02'),
            exit_price=1980.0,
            status=TradeStatus.CLOSED_TP
        )
        
        assert trade.pnl == 20.0

    def test_trade_risk_reward(self):
        """Test risk/reward calculation."""
        trade = Trade(
            id=1,
            entry_time=pd.Timestamp('2024-01-01'),
            entry_price=2000.0,
            direction=TradeDirection.LONG,
            stop_loss=1990.0,  # 10 point risk
            take_profit=2020.0,  # 20 point reward
            position_size=1.0
        )
        
        assert trade.risk_reward == 2.0

    def test_trade_to_dict(self):
        """Test trade serialization to dict."""
        trade = Trade(
            id=1,
            entry_time=pd.Timestamp('2024-01-01'),
            entry_price=2000.0,
            direction=TradeDirection.LONG,
            stop_loss=1990.0,
            take_profit=2020.0,
            position_size=1.0,
            signal_name="Test Signal"
        )
        
        data = trade.to_dict()
        
        assert data['id'] == 1
        assert data['entry_price'] == 2000.0
        assert data['direction'] == 'long'
        assert data['signal_name'] == 'Test Signal'


class TestBacktestEngine:
    """Tests for the BacktestEngine class."""

    @pytest.fixture
    def engine(self):
        """Create a fresh engine for each test."""
        return BacktestEngine(
            initial_balance=10000,
            position_size_pct=2.0,
            commission=0.0,
            slippage=0.0
        )

    @pytest.fixture
    def sample_df(self):
        """Generate sample OHLCV data."""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='4h')
        
        # Simple uptrending data
        close = 2000 + np.arange(100) * 2
        high = close + 5
        low = close - 5
        open_prices = close - 1
        
        df = pd.DataFrame({
            'open': open_prices,
            'high': high,
            'low': low,
            'close': close,
            'volume': np.ones(100) * 1000
        }, index=dates)
        
        return df

    def test_engine_initialization(self, engine):
        """Test engine initialization."""
        assert engine.initial_balance == 10000
        assert engine.position_size_pct == 2.0
        assert engine.balance == 10000

    def test_engine_reset(self, engine):
        """Test engine reset."""
        engine.balance = 5000
        engine.trades = [1, 2, 3]
        
        engine.reset()
        
        assert engine.balance == 10000
        assert engine.trades == []

    def test_calculate_position_size(self, engine):
        """Test position size calculation."""
        # Risk 2% of 10000 = 200
        # Risk per unit (entry - sl) = 2000 - 1990 = 10
        # Position size = 200 / 10 = 20
        
        position_size = engine.calculate_position_size(
            entry_price=2000.0,
            stop_loss=1990.0
        )
        
        assert position_size == 20.0

    def test_open_trade(self, engine):
        """Test opening a trade."""
        signal = Signal(
            time=pd.Timestamp('2024-01-01'),
            direction=TradeDirection.LONG,
            entry_price=2000.0,
            stop_loss=1990.0,
            take_profit=2020.0,
            signal_name="Test Signal"
        )
        
        trade = engine.open_trade(signal, pd.Timestamp('2024-01-01'))
        
        assert trade is not None
        assert trade.direction == TradeDirection.LONG
        assert trade.entry_price == 2000.0
        assert len(engine.open_trades) == 1

    def test_run_backtest_empty_result(self, engine, sample_df):
        """Test backtest with no signals."""
        def no_signal_strategy(df, idx):
            return None
        
        result = engine.run(sample_df, no_signal_strategy)
        
        assert isinstance(result, BacktestResult)
        assert result.total_trades == 0


class TestBacktestResult:
    """Tests for BacktestResult class."""

    def test_result_metrics_calculation(self):
        """Test metrics calculation."""
        trades = [
            Trade(
                id=1,
                entry_time=pd.Timestamp('2024-01-01'),
                entry_price=2000.0,
                direction=TradeDirection.LONG,
                stop_loss=1990.0,
                take_profit=2020.0,
                position_size=1.0
            ),
            Trade(
                id=2,
                entry_time=pd.Timestamp('2024-01-02'),
                entry_price=2010.0,
                direction=TradeDirection.LONG,
                stop_loss=2000.0,
                take_profit=2030.0,
                position_size=1.0
            )
        ]
        
        # Close trades
        trades[0].close(pd.Timestamp('2024-01-01 12:00'), 2020.0, TradeStatus.CLOSED_TP)
        trades[1].close(pd.Timestamp('2024-01-02 12:00'), 2000.0, TradeStatus.CLOSED_SL)
        
        result = BacktestResult(
            trades=trades,
            start_date=pd.Timestamp('2024-01-01'),
            end_date=pd.Timestamp('2024-01-03'),
            initial_balance=10000,
            final_balance=10010,
            equity_curve=[10000, 10020, 10010]
        )
        
        result.calculate_metrics()
        
        assert result.total_trades == 2
        assert result.winning_trades == 1
        assert result.losing_trades == 1
        assert result.win_rate == 50.0

    def test_result_summary(self):
        """Test summary generation."""
        result = BacktestResult(
            trades=[],
            start_date=pd.Timestamp('2024-01-01'),
            end_date=pd.Timestamp('2024-01-31'),
            initial_balance=10000,
            final_balance=11000,
            equity_curve=[10000, 10500, 11000]
        )
        
        summary = result.summary()
        
        assert 'BACKTEST RESULTS' in summary
        assert '2024-01-01' in summary


class TestSignalClass:
    """Tests for Signal class."""

    def test_signal_creation(self):
        """Test signal creation."""
        signal = Signal(
            time=pd.Timestamp('2024-01-01'),
            direction=TradeDirection.LONG,
            entry_price=2000.0,
            stop_loss=1990.0,
            take_profit=2020.0,
            signal_name="Test Signal",
            confidence=0.8,
            notes="Test notes"
        )
        
        assert signal.direction == TradeDirection.LONG
        assert signal.entry_price == 2000.0
        assert signal.confidence == 0.8
        assert signal.signal_name == "Test Signal"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Backtesting Engine
Core backtesting functionality for evaluating trading strategies.
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable
from datetime import datetime
from enum import Enum
import json


class TradeDirection(Enum):
    LONG = "long"
    SHORT = "short"


class TradeStatus(Enum):
    OPEN = "open"
    CLOSED_TP = "closed_tp"  # Closed at take profit
    CLOSED_SL = "closed_sl"  # Closed at stop loss
    CLOSED_MANUAL = "closed_manual"  # Manual close


@dataclass
class Trade:
    """Represents a single trade."""
    id: int
    entry_time: pd.Timestamp
    entry_price: float
    direction: TradeDirection
    stop_loss: float
    take_profit: Optional[float]
    position_size: float = 1.0
    
    # Filled when trade closes
    exit_time: Optional[pd.Timestamp] = None
    exit_price: Optional[float] = None
    status: TradeStatus = TradeStatus.OPEN
    pnl: float = 0.0
    pnl_pips: float = 0.0
    
    # Metadata
    signal_name: str = ""
    notes: str = ""
    
    def close(self, exit_time: pd.Timestamp, exit_price: float, status: TradeStatus):
        """Close the trade and calculate P&L."""
        self.exit_time = exit_time
        self.exit_price = exit_price
        self.status = status
        
        # Calculate P&L
        if self.direction == TradeDirection.LONG:
            self.pnl = (exit_price - self.entry_price) * self.position_size
            self.pnl_pips = (exit_price - self.entry_price) * 10  # For gold, 1 pip = $0.10
        else:
            self.pnl = (self.entry_price - exit_price) * self.position_size
            self.pnl_pips = (self.entry_price - exit_price) * 10
    
    @property
    def risk_reward(self) -> Optional[float]:
        """Calculate risk/reward ratio."""
        if self.take_profit is None:
            return None
        
        if self.direction == TradeDirection.LONG:
            risk = self.entry_price - self.stop_loss
            reward = self.take_profit - self.entry_price
        else:
            risk = self.stop_loss - self.entry_price
            reward = self.entry_price - self.take_profit
        
        if risk <= 0:
            return None
        return reward / risk
    
    def to_dict(self) -> Dict:
        """Convert trade to dictionary."""
        return {
            'id': self.id,
            'entry_time': str(self.entry_time),
            'entry_price': self.entry_price,
            'direction': self.direction.value,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'exit_time': str(self.exit_time) if self.exit_time else None,
            'exit_price': self.exit_price,
            'status': self.status.value,
            'pnl': self.pnl,
            'pnl_pips': self.pnl_pips,
            'signal_name': self.signal_name,
            'risk_reward': self.risk_reward
        }


@dataclass
class Signal:
    """Represents a trading signal."""
    time: pd.Timestamp
    direction: TradeDirection
    entry_price: float
    stop_loss: float
    take_profit: Optional[float]
    signal_name: str
    confidence: float = 1.0  # 0.0 to 1.0
    notes: str = ""


@dataclass
class BacktestResult:
    """Results of a backtest run."""
    trades: List[Trade]
    start_date: pd.Timestamp
    end_date: pd.Timestamp
    initial_balance: float
    final_balance: float
    
    # Calculated metrics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    avg_rr: float = 0.0
    sharpe_ratio: float = 0.0
    
    # Equity curve
    equity_curve: List[float] = field(default_factory=list)
    
    def calculate_metrics(self):
        """Calculate all performance metrics."""
        if not self.trades:
            return
        
        closed_trades = [t for t in self.trades if t.status != TradeStatus.OPEN]
        self.total_trades = len(closed_trades)
        
        if self.total_trades == 0:
            return
        
        # Win/Loss stats
        winning = [t for t in closed_trades if t.pnl > 0]
        losing = [t for t in closed_trades if t.pnl <= 0]
        
        self.winning_trades = len(winning)
        self.losing_trades = len(losing)
        self.win_rate = self.winning_trades / self.total_trades * 100
        
        # P&L stats
        total_profit = sum(t.pnl for t in winning) if winning else 0
        total_loss = abs(sum(t.pnl for t in losing)) if losing else 0
        
        self.profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        self.avg_win = total_profit / len(winning) if winning else 0
        self.avg_loss = total_loss / len(losing) if losing else 0
        
        self.largest_win = max(t.pnl for t in winning) if winning else 0
        self.largest_loss = min(t.pnl for t in losing) if losing else 0
        
        # Risk/Reward
        rr_values = [t.risk_reward for t in closed_trades if t.risk_reward is not None]
        self.avg_rr = np.mean(rr_values) if rr_values else 0
        
        # Drawdown calculation
        if self.equity_curve:
            equity = np.array(self.equity_curve)
            peak = np.maximum.accumulate(equity)
            drawdown = (peak - equity)
            self.max_drawdown = np.max(drawdown)
            self.max_drawdown_pct = (self.max_drawdown / np.max(peak)) * 100 if np.max(peak) > 0 else 0
        
        # Sharpe Ratio (simplified, assuming risk-free rate = 0)
        returns = [t.pnl / self.initial_balance for t in closed_trades]
        if len(returns) > 1:
            self.sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
    
    def summary(self) -> str:
        """Generate a text summary of the backtest results."""
        self.calculate_metrics()
        
        return f"""
╔══════════════════════════════════════════════════════════════╗
║                    BACKTEST RESULTS                          ║
╠══════════════════════════════════════════════════════════════╣
║  Period: {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}
║  
║  PERFORMANCE
║  ───────────────────────────────────────────────────────────
║  Initial Balance:     ${self.initial_balance:,.2f}
║  Final Balance:       ${self.final_balance:,.2f}
║  Net Profit:          ${self.final_balance - self.initial_balance:,.2f} ({((self.final_balance/self.initial_balance)-1)*100:.2f}%)
║  
║  TRADE STATISTICS
║  ───────────────────────────────────────────────────────────
║  Total Trades:        {self.total_trades}
║  Winning Trades:      {self.winning_trades}
║  Losing Trades:       {self.losing_trades}
║  Win Rate:            {self.win_rate:.2f}%
║  
║  PROFIT METRICS
║  ───────────────────────────────────────────────────────────
║  Profit Factor:       {self.profit_factor:.2f}
║  Average Win:         ${self.avg_win:.2f}
║  Average Loss:        ${self.avg_loss:.2f}
║  Largest Win:         ${self.largest_win:.2f}
║  Largest Loss:        ${self.largest_loss:.2f}
║  Average R:R:         {self.avg_rr:.2f}
║  
║  RISK METRICS
║  ───────────────────────────────────────────────────────────
║  Max Drawdown:        ${self.max_drawdown:.2f} ({self.max_drawdown_pct:.2f}%)
║  Sharpe Ratio:        {self.sharpe_ratio:.2f}
╚══════════════════════════════════════════════════════════════╝
"""
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert trades to DataFrame for analysis."""
        return pd.DataFrame([t.to_dict() for t in self.trades])
    
    def export_to_json(self, filepath: str):
        """Export results to JSON file."""
        data = {
            'summary': {
                'start_date': str(self.start_date),
                'end_date': str(self.end_date),
                'initial_balance': self.initial_balance,
                'final_balance': self.final_balance,
                'total_trades': self.total_trades,
                'win_rate': self.win_rate,
                'profit_factor': self.profit_factor,
                'max_drawdown': self.max_drawdown,
                'sharpe_ratio': self.sharpe_ratio
            },
            'trades': [t.to_dict() for t in self.trades]
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)


class BacktestEngine:
    """
    Main backtesting engine.
    
    Simulates trading on historical data using a provided strategy.
    """
    
    def __init__(
        self,
        initial_balance: float = 10000,
        position_size_pct: float = 2.0,  # Risk 2% per trade
        commission: float = 0.0,  # Commission per trade
        slippage: float = 0.0,  # Slippage in price units
    ):
        self.initial_balance = initial_balance
        self.position_size_pct = position_size_pct
        self.commission = commission
        self.slippage = slippage
        
        self.balance = initial_balance
        self.trades: List[Trade] = []
        self.open_trades: List[Trade] = []
        self.trade_counter = 0
        self.equity_curve: List[float] = []
    
    def reset(self):
        """Reset the engine for a new backtest."""
        self.balance = self.initial_balance
        self.trades = []
        self.open_trades = []
        self.trade_counter = 0
        self.equity_curve = []
    
    def calculate_position_size(self, entry_price: float, stop_loss: float) -> float:
        """
        Calculate position size based on risk percentage.
        
        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
        
        Returns:
            Position size (number of units/lots)
        """
        risk_amount = self.balance * (self.position_size_pct / 100)
        risk_per_unit = abs(entry_price - stop_loss)
        
        if risk_per_unit <= 0:
            return 0
        
        position_size = risk_amount / risk_per_unit
        return position_size
    
    def open_trade(self, signal: Signal, current_time: pd.Timestamp) -> Optional[Trade]:
        """
        Open a new trade based on a signal.
        
        Args:
            signal: Trading signal
            current_time: Current timestamp
        
        Returns:
            Trade object if opened, None otherwise
        """
        # Apply slippage
        if signal.direction == TradeDirection.LONG:
            entry_price = signal.entry_price + self.slippage
        else:
            entry_price = signal.entry_price - self.slippage
        
        # Calculate position size
        position_size = self.calculate_position_size(entry_price, signal.stop_loss)
        
        if position_size <= 0:
            return None
        
        self.trade_counter += 1
        
        trade = Trade(
            id=self.trade_counter,
            entry_time=current_time,
            entry_price=entry_price,
            direction=signal.direction,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            position_size=position_size,
            signal_name=signal.signal_name,
            notes=signal.notes
        )
        
        # Deduct commission
        self.balance -= self.commission
        
        self.open_trades.append(trade)
        self.trades.append(trade)
        
        return trade
    
    def check_and_close_trades(self, candle: pd.Series, current_time: pd.Timestamp):
        """
        Check if any open trades should be closed.
        
        Args:
            candle: Current OHLCV candle
            current_time: Current timestamp
        """
        trades_to_remove = []
        
        for trade in self.open_trades:
            exit_price = None
            status = None
            
            if trade.direction == TradeDirection.LONG:
                # Check stop loss first (assume it's hit at low)
                if candle['low'] <= trade.stop_loss:
                    exit_price = trade.stop_loss - self.slippage
                    status = TradeStatus.CLOSED_SL
                # Then check take profit (hit at high)
                elif trade.take_profit and candle['high'] >= trade.take_profit:
                    exit_price = trade.take_profit - self.slippage
                    status = TradeStatus.CLOSED_TP
            
            else:  # SHORT
                # Check stop loss first (hit at high)
                if candle['high'] >= trade.stop_loss:
                    exit_price = trade.stop_loss + self.slippage
                    status = TradeStatus.CLOSED_SL
                # Then check take profit (hit at low)
                elif trade.take_profit and candle['low'] <= trade.take_profit:
                    exit_price = trade.take_profit + self.slippage
                    status = TradeStatus.CLOSED_TP
            
            if exit_price is not None:
                trade.close(current_time, exit_price, status)
                self.balance += trade.pnl - self.commission
                trades_to_remove.append(trade)
        
        for trade in trades_to_remove:
            self.open_trades.remove(trade)
    
    def run(
        self,
        df: pd.DataFrame,
        strategy_func: Callable[[pd.DataFrame, int], Optional[Signal]],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_open_trades: int = 1
    ) -> BacktestResult:
        """
        Run the backtest.
        
        Args:
            df: OHLCV DataFrame
            strategy_func: Function that takes (df, current_index) and returns Signal or None
            start_date: Start date for backtest (optional)
            end_date: End date for backtest (optional)
            max_open_trades: Maximum concurrent open trades
        
        Returns:
            BacktestResult object
        """
        self.reset()
        
        # Filter data by date range
        if start_date:
            df = df[df.index >= start_date]
        if end_date:
            df = df[df.index <= end_date]
        
        if len(df) == 0:
            raise ValueError("No data in specified date range")
        
        print(f"Running backtest on {len(df)} candles...")
        print(f"Period: {df.index[0]} to {df.index[-1]}")
        
        # Main backtest loop
        for i in range(len(df)):
            current_time = df.index[i]
            candle = df.iloc[i]
            
            # Check and close existing trades
            self.check_and_close_trades(candle, current_time)
            
            # Record equity
            open_pnl = sum(
                (candle['close'] - t.entry_price) * t.position_size 
                if t.direction == TradeDirection.LONG 
                else (t.entry_price - candle['close']) * t.position_size
                for t in self.open_trades
            )
            self.equity_curve.append(self.balance + open_pnl)
            
            # Check for new signals (only if we can open more trades)
            if len(self.open_trades) < max_open_trades:
                signal = strategy_func(df, i)
                
                if signal is not None:
                    self.open_trade(signal, current_time)
        
        # Close any remaining open trades at market
        final_candle = df.iloc[-1]
        for trade in self.open_trades[:]:
            trade.close(
                df.index[-1], 
                final_candle['close'], 
                TradeStatus.CLOSED_MANUAL
            )
            self.balance += trade.pnl
            self.open_trades.remove(trade)
        
        # Create result
        result = BacktestResult(
            trades=self.trades,
            start_date=df.index[0],
            end_date=df.index[-1],
            initial_balance=self.initial_balance,
            final_balance=self.balance,
            equity_curve=self.equity_curve
        )
        
        result.calculate_metrics()
        
        return result


if __name__ == "__main__":
    # Example: Simple moving average crossover strategy
    import sys
    sys.path.insert(0, '..')
    from data.loader import generate_sample_data
    
    # Generate sample data
    df = generate_sample_data(start_date="2023-01-01", end_date="2024-01-01", timeframe="4h")
    
    # Add moving averages
    df['sma_fast'] = df['close'].rolling(window=10).mean()
    df['sma_slow'] = df['close'].rolling(window=30).mean()
    
    def simple_ma_strategy(data: pd.DataFrame, idx: int) -> Optional[Signal]:
        """Simple MA crossover strategy for testing."""
        if idx < 31:  # Need enough data for MAs
            return None
        
        current = data.iloc[idx]
        previous = data.iloc[idx - 1]
        
        # Bullish crossover
        if (previous['sma_fast'] <= previous['sma_slow'] and 
            current['sma_fast'] > current['sma_slow']):
            
            atr = (data['high'] - data['low']).iloc[idx-14:idx].mean()
            
            return Signal(
                time=data.index[idx],
                direction=TradeDirection.LONG,
                entry_price=current['close'],
                stop_loss=current['close'] - (atr * 2),
                take_profit=current['close'] + (atr * 3),
                signal_name="MA_Crossover_Long",
                confidence=0.7
            )
        
        # Bearish crossover
        elif (previous['sma_fast'] >= previous['sma_slow'] and 
              current['sma_fast'] < current['sma_slow']):
            
            atr = (data['high'] - data['low']).iloc[idx-14:idx].mean()
            
            return Signal(
                time=data.index[idx],
                direction=TradeDirection.SHORT,
                entry_price=current['close'],
                stop_loss=current['close'] + (atr * 2),
                take_profit=current['close'] - (atr * 3),
                signal_name="MA_Crossover_Short",
                confidence=0.7
            )
        
        return None
    
    # Run backtest
    engine = BacktestEngine(initial_balance=10000, position_size_pct=2.0)
    result = engine.run(df, simple_ma_strategy)
    
    print(result.summary())

"""
SQLAlchemy database models for The Gold Trader's Edge.
"""

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean,
    ForeignKey, Enum as SQLEnum, Text, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

from .connection import Base


class TradeDirection(str, enum.Enum):
    """Trade direction enum."""
    LONG = "long"
    SHORT = "short"


class TradeStatus(str, enum.Enum):
    """Trade status enum."""
    OPEN = "open"
    CLOSED_TP = "closed_tp"
    CLOSED_SL = "closed_sl"
    CLOSED_MANUAL = "closed_manual"


class Signal(Base):
    """
    Trading signal model.
    
    Represents a generated trading signal from the strategy.
    """
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, index=True)
    
    # Signal identification
    rule_name = Column(String(100), nullable=False, index=True)
    direction = Column(SQLEnum(TradeDirection), nullable=False)
    
    # Price levels
    entry_price = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False)
    take_profit = Column(Float, nullable=True)
    
    # Metadata
    confidence = Column(Float, default=0.0)
    timeframe = Column(String(10), nullable=False, default="4h")
    notes = Column(Text, nullable=True)
    
    # Timestamps
    signal_time = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    
    # Status
    is_executed = Column(Boolean, default=False)
    
    # Relationship to trade (if executed)
    trade = relationship("Trade", back_populates="signal", uselist=False)

    def __repr__(self):
        return f"<Signal(id={self.id}, rule={self.rule_name}, direction={self.direction})>"


class Trade(Base):
    """
    Trade model.
    
    Represents an executed trade from a signal.
    """
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    
    # Link to signal
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=True)
    signal = relationship("Signal", back_populates="trade")
    
    # Trade details
    rule_name = Column(String(100), nullable=False, index=True)
    direction = Column(SQLEnum(TradeDirection), nullable=False)
    
    # Entry
    entry_time = Column(DateTime, nullable=False)
    entry_price = Column(Float, nullable=False)
    
    # Risk levels
    stop_loss = Column(Float, nullable=False)
    take_profit = Column(Float, nullable=True)
    
    # Position
    position_size = Column(Float, default=1.0)
    
    # Exit (filled when trade closes)
    exit_time = Column(DateTime, nullable=True)
    exit_price = Column(Float, nullable=True)
    status = Column(SQLEnum(TradeStatus), default=TradeStatus.OPEN)
    
    # P&L
    pnl = Column(Float, default=0.0)
    pnl_pips = Column(Float, default=0.0)
    pnl_percent = Column(Float, default=0.0)
    
    # Metadata
    timeframe = Column(String(10), default="4h")
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Link to backtest run (for backtest trades)
    backtest_run_id = Column(Integer, ForeignKey("backtest_runs.id"), nullable=True)
    backtest_run = relationship("BacktestRun", back_populates="trades")

    @property
    def risk_reward(self) -> float:
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

    def __repr__(self):
        return f"<Trade(id={self.id}, rule={self.rule_name}, pnl={self.pnl:.2f})>"


class BacktestRun(Base):
    """
    Backtest run model.
    
    Represents a single backtest execution with its results.
    """
    __tablename__ = "backtest_runs"

    id = Column(Integer, primary_key=True, index=True)
    
    # Configuration
    timeframe = Column(String(10), nullable=False)
    rules_used = Column(String(50), nullable=False)  # e.g., "1,5,6"
    initial_balance = Column(Float, nullable=False)
    risk_per_trade = Column(Float, default=2.0)
    
    # Date range
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    
    # Results
    final_balance = Column(Float, nullable=False)
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    
    # Metrics
    win_rate = Column(Float, default=0.0)
    profit_factor = Column(Float, default=0.0)
    total_return_pct = Column(Float, default=0.0)
    max_drawdown = Column(Float, default=0.0)
    max_drawdown_pct = Column(Float, default=0.0)
    sharpe_ratio = Column(Float, default=0.0)
    avg_win = Column(Float, default=0.0)
    avg_loss = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    
    # Additional data (JSON for flexibility)
    extra_data = Column(JSON, nullable=True)
    
    # Relationship to trades
    trades = relationship("Trade", back_populates="backtest_run")

    def __repr__(self):
        return f"<BacktestRun(id={self.id}, return={self.total_return_pct:.2f}%, trades={self.total_trades})>"

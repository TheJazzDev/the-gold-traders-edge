"""Signal Models - Pydantic schemas for signal data"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class SignalResponse(BaseModel):
    """Single signal response model"""
    id: int
    timestamp: datetime
    symbol: str
    timeframe: str
    strategy_name: str
    direction: str  # LONG or SHORT
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float = Field(ge=0, le=1)
    status: str  # pending, active, closed_tp, closed_sl, closed_manual, cancelled

    # Risk metrics
    risk_reward_ratio: Optional[float] = None
    risk_pips: Optional[float] = None
    reward_pips: Optional[float] = None

    # MT5 execution data
    mt5_ticket: Optional[int] = None
    actual_entry: Optional[float] = None
    actual_exit: Optional[float] = None
    executed_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None

    # Performance
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    pnl_pips: Optional[float] = None

    # Additional info
    notes: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # For SQLAlchemy compatibility


class SignalList(BaseModel):
    """List of signals with metadata"""
    total: int
    signals: List[SignalResponse]
    page: int = 1
    page_size: int = 50


class PriceUpdate(BaseModel):
    """Real-time price update"""
    symbol: str
    price: float
    timestamp: datetime
    change: Optional[float] = None
    change_pct: Optional[float] = None


class ServiceStatus(BaseModel):
    """Signal service status"""
    status: str  # running, stopped, error
    uptime_hours: Optional[float] = None
    candles_processed: int = 0
    signals_generated: int = 0
    signal_rate: Optional[float] = None
    last_candle_time: Optional[datetime] = None
    next_candle_time: Optional[datetime] = None
    current_price: Optional[float] = None
    datafeed_type: Optional[str] = None
    symbol: Optional[str] = None
    timeframe: Optional[str] = None


class PerformanceStats(BaseModel):
    """Signal performance statistics"""
    total_signals: int
    total_closed: int
    win_count: int
    loss_count: int
    win_rate: float
    total_pnl: float
    total_pnl_pct: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    largest_win: float
    largest_loss: float

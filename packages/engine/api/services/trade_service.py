"""
Trade service - Business logic for trade operations.
"""

from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import List, Optional
from datetime import datetime

from ..database.models import Trade, Signal, TradeDirection, TradeStatus


class TradeService:
    """Service for trade-related database operations."""

    def __init__(self, db: Session):
        self.db = db

    # ==================== Signal Operations ====================

    def create_signal(
        self,
        rule_name: str,
        direction: str,
        entry_price: float,
        stop_loss: float,
        take_profit: Optional[float],
        signal_time: datetime,
        timeframe: str = "4h",
        confidence: float = 0.0,
        notes: str = ""
    ) -> Signal:
        """Create a new trading signal."""
        signal = Signal(
            rule_name=rule_name,
            direction=TradeDirection(direction),
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            signal_time=signal_time,
            timeframe=timeframe,
            confidence=confidence,
            notes=notes
        )
        self.db.add(signal)
        self.db.commit()
        self.db.refresh(signal)
        return signal

    def get_signals(
        self,
        timeframe: Optional[str] = None,
        rule_name: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Signal]:
        """Get signals with optional filtering."""
        query = self.db.query(Signal)
        
        if timeframe:
            query = query.filter(Signal.timeframe == timeframe)
        if rule_name:
            query = query.filter(Signal.rule_name == rule_name)
        
        return query.order_by(desc(Signal.signal_time)).offset(offset).limit(limit).all()

    def get_latest_signal(self, timeframe: str = "4h") -> Optional[Signal]:
        """Get the most recent signal."""
        return self.db.query(Signal).filter(
            Signal.timeframe == timeframe
        ).order_by(desc(Signal.signal_time)).first()

    # ==================== Trade Operations ====================

    def create_trade(
        self,
        rule_name: str,
        direction: str,
        entry_time: datetime,
        entry_price: float,
        stop_loss: float,
        take_profit: Optional[float] = None,
        position_size: float = 1.0,
        timeframe: str = "4h",
        signal_id: Optional[int] = None,
        backtest_run_id: Optional[int] = None,
        notes: str = ""
    ) -> Trade:
        """Create a new trade."""
        trade = Trade(
            signal_id=signal_id,
            rule_name=rule_name,
            direction=TradeDirection(direction),
            entry_time=entry_time,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size=position_size,
            timeframe=timeframe,
            backtest_run_id=backtest_run_id,
            notes=notes
        )
        self.db.add(trade)
        self.db.commit()
        self.db.refresh(trade)
        return trade

    def close_trade(
        self,
        trade_id: int,
        exit_time: datetime,
        exit_price: float,
        status: str
    ) -> Optional[Trade]:
        """Close an existing trade."""
        trade = self.db.query(Trade).filter(Trade.id == trade_id).first()
        if not trade:
            return None
        
        trade.exit_time = exit_time
        trade.exit_price = exit_price
        trade.status = TradeStatus(status)
        
        # Calculate P&L
        if trade.direction == TradeDirection.LONG:
            trade.pnl = (exit_price - trade.entry_price) * trade.position_size
        else:
            trade.pnl = (trade.entry_price - exit_price) * trade.position_size
        
        trade.pnl_percent = (trade.pnl / (trade.entry_price * trade.position_size)) * 100
        
        self.db.commit()
        self.db.refresh(trade)
        return trade

    def get_trades(
        self,
        timeframe: Optional[str] = None,
        rule_name: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        backtest_run_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Trade]:
        """Get trades with optional filtering."""
        query = self.db.query(Trade)
        
        if timeframe:
            query = query.filter(Trade.timeframe == timeframe)
        if rule_name:
            query = query.filter(Trade.rule_name == rule_name)
        if status:
            query = query.filter(Trade.status == TradeStatus(status))
        if start_date:
            query = query.filter(Trade.entry_time >= start_date)
        if end_date:
            query = query.filter(Trade.entry_time <= end_date)
        if backtest_run_id:
            query = query.filter(Trade.backtest_run_id == backtest_run_id)
        
        return query.order_by(desc(Trade.entry_time)).offset(offset).limit(limit).all()

    def get_trade_by_id(self, trade_id: int) -> Optional[Trade]:
        """Get a trade by ID."""
        return self.db.query(Trade).filter(Trade.id == trade_id).first()

    def get_open_trades(self, timeframe: Optional[str] = None) -> List[Trade]:
        """Get all open trades."""
        query = self.db.query(Trade).filter(Trade.status == TradeStatus.OPEN)
        if timeframe:
            query = query.filter(Trade.timeframe == timeframe)
        return query.all()

    # ==================== Statistics ====================

    def get_trade_statistics(
        self,
        timeframe: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> dict:
        """Get aggregate trade statistics."""
        query = self.db.query(Trade).filter(Trade.status != TradeStatus.OPEN)
        
        if timeframe:
            query = query.filter(Trade.timeframe == timeframe)
        if start_date:
            query = query.filter(Trade.entry_time >= start_date)
        if end_date:
            query = query.filter(Trade.entry_time <= end_date)
        
        trades = query.all()
        
        if not trades:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "avg_pnl": 0.0,
                "profit_factor": 0.0
            }
        
        total = len(trades)
        winners = [t for t in trades if t.pnl > 0]
        losers = [t for t in trades if t.pnl <= 0]
        
        gross_profit = sum(t.pnl for t in winners)
        gross_loss = abs(sum(t.pnl for t in losers))
        
        return {
            "total_trades": total,
            "winning_trades": len(winners),
            "losing_trades": len(losers),
            "win_rate": (len(winners) / total) * 100 if total > 0 else 0,
            "total_pnl": sum(t.pnl for t in trades),
            "avg_pnl": sum(t.pnl for t in trades) / total if total > 0 else 0,
            "profit_factor": gross_profit / gross_loss if gross_loss > 0 else float('inf')
        }

    def get_performance_by_rule(
        self,
        timeframe: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[dict]:
        """Get performance breakdown by rule."""
        query = self.db.query(Trade).filter(Trade.status != TradeStatus.OPEN)
        
        if timeframe:
            query = query.filter(Trade.timeframe == timeframe)
        if start_date:
            query = query.filter(Trade.entry_time >= start_date)
        if end_date:
            query = query.filter(Trade.entry_time <= end_date)
        
        trades = query.all()
        
        # Group by rule
        rule_stats = {}
        for trade in trades:
            if trade.rule_name not in rule_stats:
                rule_stats[trade.rule_name] = {
                    "total": 0,
                    "wins": 0,
                    "gross_profit": 0,
                    "gross_loss": 0,
                    "pnl": 0
                }
            
            rule_stats[trade.rule_name]["total"] += 1
            rule_stats[trade.rule_name]["pnl"] += trade.pnl
            
            if trade.pnl > 0:
                rule_stats[trade.rule_name]["wins"] += 1
                rule_stats[trade.rule_name]["gross_profit"] += trade.pnl
            else:
                rule_stats[trade.rule_name]["gross_loss"] += abs(trade.pnl)
        
        # Build response
        result = []
        for rule, stats in rule_stats.items():
            win_rate = (stats["wins"] / stats["total"]) * 100 if stats["total"] > 0 else 0
            pf = stats["gross_profit"] / stats["gross_loss"] if stats["gross_loss"] > 0 else float('inf')
            
            result.append({
                "rule_name": rule,
                "total_trades": stats["total"],
                "win_rate": win_rate,
                "profit_factor": pf if pf != float('inf') else 99.99,
                "net_pnl": stats["pnl"],
                "avg_return": stats["pnl"] / stats["total"] if stats["total"] > 0 else 0
            })
        
        return sorted(result, key=lambda x: x["net_pnl"], reverse=True)

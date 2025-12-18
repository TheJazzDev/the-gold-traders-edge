"""
Backtest service - Business logic for backtest operations.
"""

from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime

from ..database.models import BacktestRun, Trade, TradeDirection, TradeStatus


class BacktestService:
    """Service for backtest-related database operations."""

    def __init__(self, db: Session):
        self.db = db

    def create_backtest_run(
        self,
        timeframe: str,
        rules_used: str,
        initial_balance: float,
        risk_per_trade: float,
        start_date: datetime,
        end_date: datetime,
        final_balance: float,
        total_trades: int,
        winning_trades: int,
        losing_trades: int,
        win_rate: float,
        profit_factor: float,
        total_return_pct: float,
        max_drawdown: float,
        max_drawdown_pct: float,
        sharpe_ratio: float,
        avg_win: float,
        avg_loss: float,
        metadata: Optional[dict] = None
    ) -> BacktestRun:
        """Create a new backtest run record."""
        backtest_run = BacktestRun(
            timeframe=timeframe,
            rules_used=rules_used,
            initial_balance=initial_balance,
            risk_per_trade=risk_per_trade,
            start_date=start_date,
            end_date=end_date,
            final_balance=final_balance,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_return_pct=total_return_pct,
            max_drawdown=max_drawdown,
            max_drawdown_pct=max_drawdown_pct,
            sharpe_ratio=sharpe_ratio,
            avg_win=avg_win,
            avg_loss=avg_loss,
            metadata=metadata
        )
        self.db.add(backtest_run)
        self.db.commit()
        self.db.refresh(backtest_run)
        return backtest_run

    def save_backtest_trades(
        self,
        backtest_run_id: int,
        trades: List[dict]
    ) -> List[Trade]:
        """Save trades from a backtest run."""
        saved_trades = []
        
        for trade_data in trades:
            trade = Trade(
                backtest_run_id=backtest_run_id,
                rule_name=trade_data["rule_name"],
                direction=TradeDirection(trade_data["direction"]),
                entry_time=trade_data["entry_time"],
                entry_price=trade_data["entry_price"],
                stop_loss=trade_data["stop_loss"],
                take_profit=trade_data.get("take_profit"),
                position_size=trade_data.get("position_size", 1.0),
                exit_time=trade_data.get("exit_time"),
                exit_price=trade_data.get("exit_price"),
                status=TradeStatus(trade_data.get("status", "closed_manual")),
                pnl=trade_data.get("pnl", 0.0),
                pnl_percent=trade_data.get("pnl_percent", 0.0),
                timeframe=trade_data.get("timeframe", "4h"),
                notes=trade_data.get("notes", "")
            )
            self.db.add(trade)
            saved_trades.append(trade)
        
        self.db.commit()
        return saved_trades

    def get_backtest_runs(
        self,
        timeframe: Optional[str] = None,
        rules_used: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[BacktestRun]:
        """Get backtest runs with optional filtering."""
        query = self.db.query(BacktestRun)
        
        if timeframe:
            query = query.filter(BacktestRun.timeframe == timeframe)
        if rules_used:
            query = query.filter(BacktestRun.rules_used == rules_used)
        
        return query.order_by(desc(BacktestRun.created_at)).offset(offset).limit(limit).all()

    def get_backtest_run_by_id(self, run_id: int) -> Optional[BacktestRun]:
        """Get a backtest run by ID."""
        return self.db.query(BacktestRun).filter(BacktestRun.id == run_id).first()

    def get_backtest_trades(
        self,
        backtest_run_id: int,
        limit: int = 500
    ) -> List[Trade]:
        """Get trades for a specific backtest run."""
        return self.db.query(Trade).filter(
            Trade.backtest_run_id == backtest_run_id
        ).order_by(Trade.entry_time).limit(limit).all()

    def get_latest_backtest(
        self,
        timeframe: str = "4h",
        rules_used: str = "1,5,6"
    ) -> Optional[BacktestRun]:
        """Get the most recent backtest run for given parameters."""
        return self.db.query(BacktestRun).filter(
            BacktestRun.timeframe == timeframe,
            BacktestRun.rules_used == rules_used
        ).order_by(desc(BacktestRun.created_at)).first()

    def get_backtest_history_summary(
        self,
        timeframe: Optional[str] = None,
        limit: int = 10
    ) -> List[dict]:
        """Get a summary of recent backtests."""
        query = self.db.query(BacktestRun)
        
        if timeframe:
            query = query.filter(BacktestRun.timeframe == timeframe)
        
        runs = query.order_by(desc(BacktestRun.created_at)).limit(limit).all()
        
        return [
            {
                "id": run.id,
                "timeframe": run.timeframe,
                "rules": run.rules_used,
                "period": f"{run.start_date.strftime('%Y-%m-%d')} to {run.end_date.strftime('%Y-%m-%d')}",
                "total_return_pct": run.total_return_pct,
                "win_rate": run.win_rate,
                "total_trades": run.total_trades,
                "created_at": run.created_at.isoformat()
            }
            for run in runs
        ]

    def delete_backtest_run(self, run_id: int) -> bool:
        """Delete a backtest run and its trades."""
        run = self.db.query(BacktestRun).filter(BacktestRun.id == run_id).first()
        if not run:
            return False
        
        # Delete associated trades first
        self.db.query(Trade).filter(Trade.backtest_run_id == run_id).delete()
        
        # Delete the run
        self.db.delete(run)
        self.db.commit()
        return True

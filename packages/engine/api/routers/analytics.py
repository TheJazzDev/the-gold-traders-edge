"""
Analytics router - Performance analytics endpoints.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from data.loader import GoldDataLoader
from signals.gold_strategy import GoldStrategy, create_strategy_function
from backtesting.engine import BacktestEngine

from ..database.connection import get_db
from ..services.backtest_service import BacktestService

router = APIRouter()

# Rule name mapping for human-readable names (only profitable rules)
RULE_DISPLAY_NAMES = {
    'Rule1_618_Golden': '61.8% Golden Retracement',
    'Rule5_ATH_Retest': 'ATH Breakout Retest',
    'Rule6_50_Momentum': '50% Momentum',
}


class PerformanceSummary(BaseModel):
    """Performance summary model."""
    period: str
    timeframe: str
    total_signals: int
    winning_signals: int
    losing_signals: int
    win_rate: float
    profit_factor: float
    total_return_pct: float
    sharpe_ratio: float
    max_drawdown_pct: float
    avg_win: float
    avg_loss: float
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class RulePerformance(BaseModel):
    """Rule performance model."""
    name: str
    total_signals: int
    win_rate: float
    profit_factor: float
    net_pnl: float
    avg_return: float


class TradeDetail(BaseModel):
    """Individual trade detail model."""
    id: int
    signal_name: str
    direction: str
    entry_time: str
    entry_price: float
    exit_time: Optional[str]
    exit_price: Optional[float]
    stop_loss: float
    take_profit: Optional[float]
    status: str
    pnl: float
    pnl_pct: float
    risk_reward: Optional[float]


class BacktestHistoryItem(BaseModel):
    """Backtest history item model."""
    id: int
    timeframe: str
    rules: str
    period: str
    total_return_pct: float
    win_rate: float
    total_trades: int
    created_at: str


class SaveBacktestRequest(BaseModel):
    """Request to save a backtest run."""
    timeframe: str = "4h"
    rules: str = "1,5,6"
    start_date: Optional[str] = None
    end_date: Optional[str] = None


@router.get("/summary", response_model=PerformanceSummary)
async def get_performance_summary(
    timeframe: str = Query("4h", description="Timeframe: 4h or 1d"),
    rules: Optional[str] = Query("1,5,6", description="Comma-separated rule numbers (optimized: 1,5,6)"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD) for backtest range"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD) for backtest range")
):
    """
    Get overall strategy performance summary.

    Returns aggregated performance metrics for the trading strategy.
    Supports date range filtering for backtesting specific periods.
    """
    try:
        # Load data
        loader = GoldDataLoader()
        processed_dir = Path("data/processed")
        pattern = f"xauusd_{timeframe}_*.csv"
        matching_files = list(processed_dir.glob(pattern))

        if not matching_files:
            raise HTTPException(
                status_code=404,
                detail=f"No data available for timeframe {timeframe}"
            )

        data_file = sorted(matching_files)[-1]
        df = loader.load_from_csv(str(data_file))

        # Initialize strategy
        strategy = GoldStrategy()

        # Configure rules
        if rules:
            for rule in strategy.rules_enabled:
                strategy.rules_enabled[rule] = False

            rule_map = {
                '1': 'rule_1_618_retracement',
                '5': 'rule_5_ath_breakout_retest',
                '6': 'rule_6_50_momentum',
            }

            for rule_num in rules.split(','):
                rule_num = rule_num.strip()
                if rule_num in rule_map:
                    strategy.rules_enabled[rule_map[rule_num]] = True

        # Run backtest with date range
        engine = BacktestEngine(initial_balance=10000, position_size_pct=2.0)
        result = engine.run(
            df=df,
            strategy_func=create_strategy_function(strategy),
            start_date=start_date,
            end_date=end_date
        )

        # Calculate return percentage
        net_profit = result.final_balance - result.initial_balance
        return_pct = (net_profit / result.initial_balance) * 100

        # Determine period description
        period_str = "custom" if start_date or end_date else "all"

        return PerformanceSummary(
            period=period_str,
            timeframe=timeframe,
            total_signals=result.total_trades,
            winning_signals=result.winning_trades,
            losing_signals=result.losing_trades,
            win_rate=result.win_rate,
            profit_factor=result.profit_factor,
            total_return_pct=return_pct,
            sharpe_ratio=result.sharpe_ratio,
            max_drawdown_pct=result.max_drawdown_pct,
            avg_win=result.avg_win,
            avg_loss=abs(result.avg_loss),
            start_date=str(result.start_date.date()) if result.start_date else None,
            end_date=str(result.end_date.date()) if result.end_date else None
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating performance: {str(e)}")


@router.get("/by-rule", response_model=List[RulePerformance])
async def get_performance_by_rule(
    timeframe: str = Query("4h", description="Timeframe: 4h or 1d"),
    rules: Optional[str] = Query("1,5,6", description="Comma-separated rule numbers (optimized: 1,5,6)"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD) for backtest range"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD) for backtest range")
):
    """
    Get performance breakdown by individual rules.

    Returns performance metrics for each trading rule separately.
    Supports date range filtering for backtesting specific periods.
    """
    try:
        # Load data
        loader = GoldDataLoader()
        processed_dir = Path("data/processed")
        pattern = f"xauusd_{timeframe}_*.csv"
        matching_files = list(processed_dir.glob(pattern))

        if not matching_files:
            raise HTTPException(
                status_code=404,
                detail=f"No data available for timeframe {timeframe}"
            )

        data_file = sorted(matching_files)[-1]
        df = loader.load_from_csv(str(data_file))

        # Initialize strategy
        strategy = GoldStrategy()

        # Configure rules
        if rules:
            for rule in strategy.rules_enabled:
                strategy.rules_enabled[rule] = False

            rule_map = {
                '1': 'rule_1_618_retracement',
                '5': 'rule_5_ath_breakout_retest',
                '6': 'rule_6_50_momentum',
            }

            for rule_num in rules.split(','):
                rule_num = rule_num.strip()
                if rule_num in rule_map:
                    strategy.rules_enabled[rule_map[rule_num]] = True

        # Run backtest with date range
        engine = BacktestEngine(initial_balance=10000, position_size_pct=2.0)
        result = engine.run(
            df=df,
            strategy_func=create_strategy_function(strategy),
            start_date=start_date,
            end_date=end_date
        )

        # Calculate performance by rule
        rule_stats = {}
        for trade in result.trades:
            rule = trade.signal_name
            if rule not in rule_stats:
                rule_stats[rule] = {
                    'count': 0,
                    'wins': 0,
                    'gross_profit': 0,
                    'gross_loss': 0,
                    'pnl': 0
                }

            rule_stats[rule]['count'] += 1
            rule_stats[rule]['pnl'] += trade.pnl

            if trade.pnl > 0:
                rule_stats[rule]['wins'] += 1
                rule_stats[rule]['gross_profit'] += trade.pnl
            else:
                rule_stats[rule]['gross_loss'] += abs(trade.pnl)

        # Build response
        performances = []
        for rule, stats in sorted(rule_stats.items(), key=lambda x: x[1]['pnl'], reverse=True):
            win_rate = (stats['wins'] / stats['count'] * 100) if stats['count'] > 0 else 0
            pf = stats['gross_profit'] / stats['gross_loss'] if stats['gross_loss'] > 0 else float('inf')
            avg_return = stats['pnl'] / stats['count'] if stats['count'] > 0 else 0

            # Use display name if available, otherwise use original
            display_name = RULE_DISPLAY_NAMES.get(rule, rule.replace('_', ' ').title())

            performances.append(RulePerformance(
                name=display_name,
                total_signals=stats['count'],
                win_rate=win_rate,
                profit_factor=pf if pf != float('inf') else 99.99,
                net_pnl=stats['pnl'],
                avg_return=avg_return
            ))

        return performances

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating rule performance: {str(e)}")


@router.get("/trades", response_model=List[TradeDetail])
async def get_trade_history(
    timeframe: str = Query("4h", description="Timeframe: 4h or 1d"),
    rules: Optional[str] = Query("1,5,6", description="Comma-separated rule numbers (optimized: 1,5,6)"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD) for backtest range"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD) for backtest range")
):
    """
    Get individual trade history with entry, SL, TP details.

    Returns all trades executed during the backtest.
    Supports date range filtering for backtesting specific periods.
    """
    try:
        # Load data
        loader = GoldDataLoader()
        processed_dir = Path("data/processed")
        pattern = f"xauusd_{timeframe}_*.csv"
        matching_files = list(processed_dir.glob(pattern))

        if not matching_files:
            raise HTTPException(
                status_code=404,
                detail=f"No data available for timeframe {timeframe}"
            )

        data_file = sorted(matching_files)[-1]
        df = loader.load_from_csv(str(data_file))

        # Initialize strategy
        strategy = GoldStrategy()

        # Configure rules
        if rules:
            for rule in strategy.rules_enabled:
                strategy.rules_enabled[rule] = False

            rule_map = {
                '1': 'rule_1_618_retracement',
                '5': 'rule_5_ath_breakout_retest',
                '6': 'rule_6_50_momentum',
            }

            for rule_num in rules.split(','):
                rule_num = rule_num.strip()
                if rule_num in rule_map:
                    strategy.rules_enabled[rule_map[rule_num]] = True

        # Run backtest with date range
        engine = BacktestEngine(initial_balance=10000, position_size_pct=2.0)
        result = engine.run(
            df=df,
            strategy_func=create_strategy_function(strategy),
            start_date=start_date,
            end_date=end_date
        )

        # Build trade details
        trades = []
        for trade in result.trades:
            # Calculate P&L percentage
            pnl_pct = (trade.pnl / (trade.entry_price * trade.position_size)) * 100 if trade.entry_price and trade.position_size else 0

            # Use display name if available
            display_name = RULE_DISPLAY_NAMES.get(trade.signal_name, trade.signal_name.replace('_', ' ').title())

            trades.append(TradeDetail(
                id=trade.id,
                signal_name=display_name,
                direction=trade.direction.value,
                entry_time=str(trade.entry_time),
                entry_price=trade.entry_price,
                exit_time=str(trade.exit_time) if trade.exit_time else None,
                exit_price=trade.exit_price,
                stop_loss=trade.stop_loss,
                take_profit=trade.take_profit,
                status=trade.status.value.replace('_', ' ').title(),
                pnl=trade.pnl,
                pnl_pct=pnl_pct,
                risk_reward=trade.risk_reward
            ))

        return trades

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving trade history: {str(e)}")


@router.post("/backtest/save")
async def save_backtest_run(
    request: SaveBacktestRequest,
    db: Session = Depends(get_db)
):
    """
    Run a backtest and save results to database.

    This persists the backtest run and all trades for historical analysis.
    """
    try:
        # Load data
        loader = GoldDataLoader()
        processed_dir = Path("data/processed")
        pattern = f"xauusd_{request.timeframe}_*.csv"
        matching_files = list(processed_dir.glob(pattern))

        if not matching_files:
            raise HTTPException(
                status_code=404,
                detail=f"No data available for timeframe {request.timeframe}"
            )

        data_file = sorted(matching_files)[-1]
        df = loader.load_from_csv(str(data_file))

        # Initialize strategy
        strategy = GoldStrategy()

        # Configure rules
        if request.rules:
            for rule in strategy.rules_enabled:
                strategy.rules_enabled[rule] = False

            rule_map = {
                '1': 'rule_1_618_retracement',
                '5': 'rule_5_ath_breakout_retest',
                '6': 'rule_6_50_momentum',
            }

            for rule_num in request.rules.split(','):
                rule_num = rule_num.strip()
                if rule_num in rule_map:
                    strategy.rules_enabled[rule_map[rule_num]] = True

        # Run backtest
        engine = BacktestEngine(initial_balance=10000, position_size_pct=2.0)
        result = engine.run(
            df=df,
            strategy_func=create_strategy_function(strategy),
            start_date=request.start_date,
            end_date=request.end_date
        )

        # Calculate return percentage
        net_profit = result.final_balance - result.initial_balance
        return_pct = (net_profit / result.initial_balance) * 100

        # Save to database
        service = BacktestService(db)
        backtest_run = service.create_backtest_run(
            timeframe=request.timeframe,
            rules_used=request.rules,
            initial_balance=result.initial_balance,
            risk_per_trade=2.0,
            start_date=result.start_date,
            end_date=result.end_date,
            final_balance=result.final_balance,
            total_trades=result.total_trades,
            winning_trades=result.winning_trades,
            losing_trades=result.losing_trades,
            win_rate=result.win_rate,
            profit_factor=result.profit_factor,
            total_return_pct=return_pct,
            max_drawdown=result.max_drawdown,
            max_drawdown_pct=result.max_drawdown_pct,
            sharpe_ratio=result.sharpe_ratio,
            avg_win=result.avg_win,
            avg_loss=abs(result.avg_loss)
        )

        # Save trades
        trades_data = []
        for trade in result.trades:
            trades_data.append({
                "rule_name": trade.signal_name,
                "direction": trade.direction.value,
                "entry_time": trade.entry_time,
                "entry_price": trade.entry_price,
                "stop_loss": trade.stop_loss,
                "take_profit": trade.take_profit,
                "position_size": trade.position_size,
                "exit_time": trade.exit_time,
                "exit_price": trade.exit_price,
                "status": trade.status.value,
                "pnl": trade.pnl,
                "pnl_percent": (trade.pnl / (trade.entry_price * trade.position_size)) * 100 if trade.entry_price and trade.position_size else 0,
                "timeframe": request.timeframe
            })

        service.save_backtest_trades(backtest_run.id, trades_data)

        return {
            "success": True,
            "backtest_id": backtest_run.id,
            "total_return_pct": return_pct,
            "win_rate": result.win_rate,
            "total_trades": result.total_trades,
            "message": f"Backtest saved successfully with {result.total_trades} trades"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving backtest: {str(e)}")


@router.get("/backtest/history", response_model=List[BacktestHistoryItem])
async def get_backtest_history(
    timeframe: Optional[str] = Query(None, description="Filter by timeframe"),
    limit: int = Query(10, ge=1, le=100, description="Number of results"),
    db: Session = Depends(get_db)
):
    """
    Get historical backtest runs.

    Returns a list of previous backtest runs for comparison.
    """
    try:
        service = BacktestService(db)
        history = service.get_backtest_history_summary(timeframe=timeframe, limit=limit)

        return [
            BacktestHistoryItem(
                id=item["id"],
                timeframe=item["timeframe"],
                rules=item["rules"],
                period=item["period"],
                total_return_pct=item["total_return_pct"],
                win_rate=item["win_rate"],
                total_trades=item["total_trades"],
                created_at=item["created_at"]
            )
            for item in history
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving backtest history: {str(e)}")


@router.get("/backtest/{backtest_id}")
async def get_backtest_details(
    backtest_id: int,
    db: Session = Depends(get_db)
):
    """
    Get detailed results for a specific backtest run.

    Returns full metrics and trade list for a saved backtest.
    """
    try:
        service = BacktestService(db)
        backtest = service.get_backtest_run_by_id(backtest_id)

        if not backtest:
            raise HTTPException(status_code=404, detail="Backtest not found")

        trades = service.get_backtest_trades(backtest_id)

        return {
            "id": backtest.id,
            "timeframe": backtest.timeframe,
            "rules_used": backtest.rules_used,
            "period": f"{backtest.start_date.strftime('%Y-%m-%d')} to {backtest.end_date.strftime('%Y-%m-%d')}",
            "initial_balance": backtest.initial_balance,
            "final_balance": backtest.final_balance,
            "total_return_pct": backtest.total_return_pct,
            "total_trades": backtest.total_trades,
            "winning_trades": backtest.winning_trades,
            "losing_trades": backtest.losing_trades,
            "win_rate": backtest.win_rate,
            "profit_factor": backtest.profit_factor,
            "sharpe_ratio": backtest.sharpe_ratio,
            "max_drawdown": backtest.max_drawdown,
            "max_drawdown_pct": backtest.max_drawdown_pct,
            "avg_win": backtest.avg_win,
            "avg_loss": backtest.avg_loss,
            "created_at": backtest.created_at.isoformat(),
            "trades": [
                {
                    "id": t.id,
                    "rule_name": t.rule_name,
                    "direction": t.direction.value,
                    "entry_time": str(t.entry_time),
                    "entry_price": t.entry_price,
                    "exit_time": str(t.exit_time) if t.exit_time else None,
                    "exit_price": t.exit_price,
                    "stop_loss": t.stop_loss,
                    "take_profit": t.take_profit,
                    "pnl": t.pnl,
                    "pnl_percent": t.pnl_percent,
                    "status": t.status.value
                }
                for t in trades
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving backtest details: {str(e)}")


@router.delete("/backtest/{backtest_id}")
async def delete_backtest_run(
    backtest_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a backtest run and its associated trades.
    """
    try:
        service = BacktestService(db)
        success = service.delete_backtest_run(backtest_id)

        if not success:
            raise HTTPException(status_code=404, detail="Backtest not found")

        return {"success": True, "message": f"Backtest {backtest_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting backtest: {str(e)}")

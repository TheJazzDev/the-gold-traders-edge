"""Analytics API Routes"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

# Add engine src to path to import models
engine_src = Path(__file__).parent.parent.parent.parent / "engine" / "src"
sys.path.insert(0, str(engine_src))

from database.models import Signal, SignalStatus, SignalDirection
from src.database import get_db

router = APIRouter(prefix="/v1/analytics", tags=["analytics"])


@router.get("/summary")
async def get_summary(
    days: Optional[int] = Query(30, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """
    Get analytics summary including win rate, PnL, and recent performance.

    Args:
        days: Number of days to analyze (default: 30)
        db: Database session

    Returns:
        Analytics summary data
    """
    query = db.query(Signal)

    # Filter by date range
    if days:
        since = datetime.now() - timedelta(days=days)
        query = query.filter(Signal.timestamp >= since)

    # Get all signals
    all_signals = query.all()
    total_signals = len(all_signals)

    # Get closed signals
    closed_signals = [s for s in all_signals if s.status in [
        SignalStatus.CLOSED_TP,
        SignalStatus.CLOSED_SL,
        SignalStatus.CLOSED_MANUAL
    ]]

    total_closed = len(closed_signals)

    # Calculate stats
    wins = [s for s in closed_signals if s.pnl and s.pnl > 0]
    losses = [s for s in closed_signals if s.pnl and s.pnl <= 0]

    win_count = len(wins)
    loss_count = len(losses)
    win_rate = (win_count / total_closed * 100) if total_closed > 0 else 0

    total_pnl = sum(s.pnl for s in closed_signals if s.pnl) if closed_signals else 0
    total_pnl_pct = sum(s.pnl_pct for s in closed_signals if s.pnl_pct) if closed_signals else 0

    avg_win = sum(s.pnl for s in wins) / win_count if win_count > 0 else 0
    avg_loss = sum(s.pnl for s in losses) / loss_count if loss_count > 0 else 0

    # Get active signals
    active_signals = [s for s in all_signals if s.status in [
        SignalStatus.PENDING,
        SignalStatus.ACTIVE
    ]]

    # Get recent signals (last 10)
    recent_signals = sorted(all_signals, key=lambda x: x.timestamp, reverse=True)[:10]

    return {
        "period_days": days,
        "total_signals": total_signals,
        "total_closed": total_closed,
        "active_signals": len(active_signals),
        "win_count": win_count,
        "loss_count": loss_count,
        "win_rate": round(win_rate, 2),
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": round(total_pnl_pct, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "recent_signals": [
            {
                "id": s.id,
                "timestamp": s.timestamp.isoformat() if s.timestamp else None,
                "direction": s.direction.value,
                "entry_price": s.entry_price,
                "status": s.status.value,
                "pnl": s.pnl,
                "pnl_pct": s.pnl_pct
            } for s in recent_signals
        ]
    }


@router.get("/by-rule")
async def get_by_rule(
    days: Optional[int] = Query(30, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """
    Get analytics grouped by trading rule/strategy.

    Args:
        days: Number of days to analyze (default: 30)
        db: Database session

    Returns:
        Analytics grouped by strategy
    """
    query = db.query(Signal)

    # Filter by date range
    if days:
        since = datetime.now() - timedelta(days=days)
        query = query.filter(Signal.timestamp >= since)

    signals = query.all()

    # Group by strategy
    strategy_stats = {}

    for signal in signals:
        strategy_name = signal.strategy_name or "Unknown"

        if strategy_name not in strategy_stats:
            strategy_stats[strategy_name] = {
                "strategy_name": strategy_name,
                "total_signals": 0,
                "closed_signals": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0,
                "total_pnl": 0,
                "avg_pnl": 0
            }

        stats = strategy_stats[strategy_name]
        stats["total_signals"] += 1

        if signal.status in [SignalStatus.CLOSED_TP, SignalStatus.CLOSED_SL, SignalStatus.CLOSED_MANUAL]:
            stats["closed_signals"] += 1

            if signal.pnl:
                stats["total_pnl"] += signal.pnl
                if signal.pnl > 0:
                    stats["wins"] += 1
                else:
                    stats["losses"] += 1

    # Calculate final stats
    for stats in strategy_stats.values():
        if stats["closed_signals"] > 0:
            stats["win_rate"] = (stats["wins"] / stats["closed_signals"]) * 100
            stats["avg_pnl"] = stats["total_pnl"] / stats["closed_signals"]
        stats["win_rate"] = round(stats["win_rate"], 2)
        stats["total_pnl"] = round(stats["total_pnl"], 2)
        stats["avg_pnl"] = round(stats["avg_pnl"], 2)

    return {
        "period_days": days,
        "strategies": list(strategy_stats.values())
    }


@router.get("/trades")
async def get_trades(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get list of trades with pagination.

    Args:
        page: Page number
        page_size: Items per page
        status: Filter by status
        db: Database session

    Returns:
        Paginated list of trades
    """
    query = db.query(Signal)

    # Apply status filter
    if status:
        try:
            status_enum = SignalStatus[status.upper()]
            query = query.filter(Signal.status == status_enum)
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    # Get total count
    total = query.count()

    # Paginate
    offset = (page - 1) * page_size
    signals = query.order_by(desc(Signal.timestamp)).offset(offset).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "trades": [
            {
                "id": s.id,
                "timestamp": s.timestamp.isoformat() if s.timestamp else None,
                "symbol": s.symbol,
                "direction": s.direction.value,
                "entry_price": s.entry_price,
                "stop_loss": s.stop_loss,
                "take_profit": s.take_profit,
                "status": s.status.value,
                "pnl": s.pnl,
                "pnl_pct": s.pnl_pct,
                "strategy_name": s.strategy_name,
                "confidence": s.confidence
            } for s in signals
        ]
    }


@router.get("/backtest")
async def get_backtest(
    timeframe: Optional[str] = None,
    rules: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Run backtest and return comprehensive results.

    This endpoint combines summary stats, rule performance, and trade details
    to provide everything needed for the backtest dashboard.

    Args:
        timeframe: Timeframe filter (e.g., '4h', '1d')
        rules: Comma-separated list of rule IDs to include
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        db: Database session

    Returns:
        Combined backtest results with summary, rules, and trades
    """
    query = db.query(Signal)

    # Apply filters
    if timeframe:
        query = query.filter(Signal.timeframe == timeframe)

    if rules:
        rule_list = [r.strip() for r in rules.split(',')]
        query = query.filter(Signal.strategy_name.in_(rule_list))

    if start_date:
        try:
            start = datetime.fromisoformat(start_date)
            query = query.filter(Signal.timestamp >= start)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format")

    if end_date:
        try:
            end = datetime.fromisoformat(end_date)
            query = query.filter(Signal.timestamp <= end)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format")

    signals = query.order_by(Signal.timestamp).all()

    # Filter closed signals with PnL
    closed_signals = [s for s in signals if s.status in [
        SignalStatus.CLOSED_TP,
        SignalStatus.CLOSED_SL,
        SignalStatus.CLOSED_MANUAL
    ] and s.pnl is not None]

    # Calculate summary statistics
    initial_balance = 10000
    equity = initial_balance
    equity_curve = []
    max_equity = initial_balance
    max_drawdown = 0

    wins = [s for s in closed_signals if s.pnl > 0]
    losses = [s for s in closed_signals if s.pnl <= 0]

    for signal in closed_signals:
        equity += signal.pnl
        equity_curve.append(equity)
        max_equity = max(max_equity, equity)
        drawdown = max_equity - equity
        max_drawdown = max(max_drawdown, drawdown)

    total_pnl = sum(s.pnl for s in closed_signals)
    total_return_pct = ((equity - initial_balance) / initial_balance) * 100
    max_drawdown_pct = (max_drawdown / max_equity * 100) if max_equity > 0 else 0

    win_pnl = sum(s.pnl for s in wins)
    loss_pnl = abs(sum(s.pnl for s in losses))
    profit_factor = (win_pnl / loss_pnl) if loss_pnl > 0 else 0

    avg_win = (win_pnl / len(wins)) if wins else 0
    avg_loss = (-loss_pnl / len(losses)) if losses else 0

    win_rate = (len(wins) / len(closed_signals) * 100) if closed_signals else 0

    # Calculate Sharpe ratio (simplified)
    if closed_signals:
        returns = [s.pnl / initial_balance for s in closed_signals]
        avg_return = sum(returns) / len(returns)
        std_return = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5
        sharpe_ratio = (avg_return / std_return * (252 ** 0.5)) if std_return > 0 else 0
    else:
        sharpe_ratio = 0

    summary = {
        "total_signals": len(closed_signals),
        "winning_signals": len(wins),
        "losing_signals": len(losses),
        "total_pnl": round(total_pnl, 2),
        "total_return_pct": round(total_return_pct, 2),
        "win_rate": round(win_rate, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "profit_factor": round(profit_factor, 2),
        "max_drawdown": round(max_drawdown, 2),
        "max_drawdown_pct": round(max_drawdown_pct, 2),
        "sharpe_ratio": round(sharpe_ratio, 2),
        "initial_balance": initial_balance,
        "final_balance": round(equity, 2)
    }

    # Group by rule/strategy
    strategy_stats = {}
    for signal in closed_signals:
        strategy_name = signal.strategy_name or "Unknown"

        if strategy_name not in strategy_stats:
            strategy_stats[strategy_name] = {
                "name": strategy_name,
                "signals": [],
                "total_pnl": 0
            }

        strategy_stats[strategy_name]["signals"].append(signal)
        strategy_stats[strategy_name]["total_pnl"] += signal.pnl

    rules_performance = []
    for strategy_name, data in strategy_stats.items():
        strategy_signals = data["signals"]
        strategy_wins = [s for s in strategy_signals if s.pnl > 0]
        strategy_losses = [s for s in strategy_signals if s.pnl <= 0]

        win_pnl = sum(s.pnl for s in strategy_wins)
        loss_pnl = abs(sum(s.pnl for s in strategy_losses))

        rules_performance.append({
            "name": strategy_name,
            "total_signals": len(strategy_signals),
            "winning_signals": len(strategy_wins),
            "losing_signals": len(strategy_losses),
            "win_rate": round((len(strategy_wins) / len(strategy_signals) * 100), 2) if strategy_signals else 0,
            "net_pnl": round(data["total_pnl"], 2),
            "avg_pnl": round(data["total_pnl"] / len(strategy_signals), 2) if strategy_signals else 0,
            "profit_factor": round((win_pnl / loss_pnl), 2) if loss_pnl > 0 else 0
        })

    # Build trades list
    trades = []
    for signal in closed_signals:
        trades.append({
            "id": signal.id,
            "signal_name": signal.strategy_name or "Unknown",
            "direction": signal.direction.value,
            "entry_time": signal.timestamp.isoformat(),
            "entry_price": signal.entry_price,
            "stop_loss": signal.stop_loss,
            "take_profit": signal.take_profit,
            "exit_time": signal.closed_at.isoformat() if signal.closed_at else None,
            "exit_price": signal.exit_price,
            "pnl": round(signal.pnl, 2),
            "pnl_pct": round(signal.pnl_pct, 2) if signal.pnl_pct else 0,
            "status": signal.status.value,
            "risk_reward": round((signal.take_profit - signal.entry_price) / (signal.entry_price - signal.stop_loss), 2) if signal.direction.value == 'long' else round((signal.entry_price - signal.take_profit) / (signal.stop_loss - signal.entry_price), 2) if signal.take_profit else None
        })

    return {
        "summary": summary,
        "rules": rules_performance,
        "trades": trades
    }

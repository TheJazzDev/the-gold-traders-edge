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
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get backtest results and historical performance.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        db: Database session

    Returns:
        Backtest performance data
    """
    query = db.query(Signal)

    # Apply date filters
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

    # Calculate equity curve
    equity = 10000  # Starting balance
    equity_curve = [{"date": None, "equity": equity}]

    closed_signals = [s for s in signals if s.status in [
        SignalStatus.CLOSED_TP,
        SignalStatus.CLOSED_SL,
        SignalStatus.CLOSED_MANUAL
    ] and s.pnl is not None]

    for signal in closed_signals:
        equity += signal.pnl
        equity_curve.append({
            "date": signal.closed_at.isoformat() if signal.closed_at else signal.timestamp.isoformat(),
            "equity": round(equity, 2)
        })

    # Calculate stats
    total_return = ((equity - 10000) / 10000) * 100

    wins = [s for s in closed_signals if s.pnl > 0]
    losses = [s for s in closed_signals if s.pnl <= 0]

    return {
        "start_date": start_date,
        "end_date": end_date,
        "total_trades": len(closed_signals),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": (len(wins) / len(closed_signals) * 100) if closed_signals else 0,
        "total_return": round(total_return, 2),
        "final_equity": round(equity, 2),
        "equity_curve": equity_curve
    }

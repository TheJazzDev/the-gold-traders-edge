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

CLOSED_STATUSES = [SignalStatus.CLOSED_TP, SignalStatus.CLOSED_SL, SignalStatus.CLOSED_MANUAL]


def _is_win(signal: Signal) -> Optional[bool]:
    """True/False for a resolved TP/SL signal, None if not resolved (e.g.
    closed manually) — excluded from win rate, matching
    SignalRepository.get_performance_stats()."""
    if signal.status == SignalStatus.CLOSED_TP:
        return True
    if signal.status == SignalStatus.CLOSED_SL:
        return False
    return None


def _r_multiple(signal: Signal) -> Optional[float]:
    """pnl_pips / risk_pips. There is no real dollar account behind these
    signals yet (Signal.pnl is always NULL in signals-only mode), so edge is
    measured in R-multiples instead — see SignalRepository.get_performance_stats()."""
    if signal.risk_pips and signal.pnl_pips is not None:
        return signal.pnl_pips / signal.risk_pips
    return None


def _profit_factor(total_gain_r: float, total_loss_r: float) -> Optional[float]:
    """total_loss_r must already be a positive magnitude. Returns None (not
    0) when there are gains but no losses yet — that ratio is genuinely
    undefined/infinite, and 0 would misleadingly read as "unprofitable"."""
    if total_loss_r > 0:
        return total_gain_r / total_loss_r
    if total_gain_r > 0:
        return None
    return 0.0


def _round_or_none(value: Optional[float], ndigits: int = 2) -> Optional[float]:
    return round(value, ndigits) if value is not None else None


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
    closed_signals = [s for s in all_signals if s.status in CLOSED_STATUSES]
    total_closed = len(closed_signals)

    # Win rate is over resolved (TP/SL) signals only — a manually-closed
    # signal has no clean win/loss verdict. See _is_win().
    resolved = [s for s in closed_signals if _is_win(s) is not None]
    win_count = sum(1 for s in resolved if _is_win(s))
    loss_count = len(resolved) - win_count
    win_rate = (win_count / len(resolved) * 100) if resolved else 0

    r_multiples = [r for r in (_r_multiple(s) for s in closed_signals) if r is not None]
    net_r_multiple = sum(r_multiples)
    avg_r_multiple = (net_r_multiple / len(r_multiples)) if r_multiples else 0

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
        "net_r_multiple": round(net_r_multiple, 2),
        "avg_r_multiple": round(avg_r_multiple, 2),
        "recent_signals": [
            {
                "id": s.id,
                "timestamp": s.timestamp.isoformat() if s.timestamp else None,
                "direction": s.direction.value,
                "entry_price": s.entry_price,
                "status": s.status.value,
                "r_multiple": _r_multiple(s)
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
                "r_multiples": [],
                "net_r_multiple": 0,
                "avg_r_multiple": 0,
                "profit_factor": 0,
            }

        stats = strategy_stats[strategy_name]
        stats["total_signals"] += 1

        if signal.status in CLOSED_STATUSES:
            stats["closed_signals"] += 1

            is_win = _is_win(signal)
            if is_win is True:
                stats["wins"] += 1
            elif is_win is False:
                stats["losses"] += 1

            r = _r_multiple(signal)
            if r is not None:
                stats["r_multiples"].append(r)

    # Calculate final stats
    for stats in strategy_stats.values():
        resolved = stats["wins"] + stats["losses"]
        if resolved > 0:
            stats["win_rate"] = (stats["wins"] / resolved) * 100

        r_multiples = stats.pop("r_multiples")
        if r_multiples:
            stats["net_r_multiple"] = sum(r_multiples)
            stats["avg_r_multiple"] = stats["net_r_multiple"] / len(r_multiples)
            gains = sum(r for r in r_multiples if r > 0)
            losses_r = abs(sum(r for r in r_multiples if r < 0))
            stats["profit_factor"] = _profit_factor(gains, losses_r)

        stats["win_rate"] = round(stats["win_rate"], 2)
        stats["net_r_multiple"] = round(stats["net_r_multiple"], 2)
        stats["avg_r_multiple"] = round(stats["avg_r_multiple"], 2)
        stats["profit_factor"] = _round_or_none(stats["profit_factor"])

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
                "r_multiple": _r_multiple(s),
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

    # Resolved (TP/SL) signals with a computable R-multiple. There is no
    # real dollar account behind these signals yet (Signal.pnl is always
    # NULL in signals-only mode), so this previously filtered on
    # `s.pnl is not None` and always returned zero signals. Edge is measured
    # in R-multiples instead — see SignalRepository.get_performance_stats().
    closed_signals = [s for s in signals if _r_multiple(s) is not None]

    wins = [s for s in closed_signals if _is_win(s) is True]
    losses = [s for s in closed_signals if _is_win(s) is False]

    equity_r = 0.0
    max_equity_r = 0.0
    max_drawdown_r = 0.0
    for signal in closed_signals:
        equity_r += _r_multiple(signal)
        max_equity_r = max(max_equity_r, equity_r)
        max_drawdown_r = max(max_drawdown_r, max_equity_r - equity_r)

    gains_r = sum(_r_multiple(s) for s in wins)
    losses_r = abs(sum(_r_multiple(s) for s in losses))
    profit_factor = _profit_factor(gains_r, losses_r)

    avg_win_r = (gains_r / len(wins)) if wins else 0
    avg_loss_r = (-losses_r / len(losses)) if losses else 0

    win_rate = (len(wins) / len(closed_signals) * 100) if closed_signals else 0

    # Simplified Sharpe ratio, treating each trade's R-multiple as its "return".
    if closed_signals:
        returns = [_r_multiple(s) for s in closed_signals]
        avg_return = sum(returns) / len(returns)
        std_return = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5
        sharpe_ratio = (avg_return / std_return * (252 ** 0.5)) if std_return > 0 else 0
    else:
        sharpe_ratio = 0

    summary = {
        "total_signals": len(closed_signals),
        "winning_signals": len(wins),
        "losing_signals": len(losses),
        "net_r_multiple": round(equity_r, 2),
        "win_rate": round(win_rate, 2),
        "avg_win_r": round(avg_win_r, 2),
        "avg_loss_r": round(avg_loss_r, 2),
        "profit_factor": _round_or_none(profit_factor),
        "max_drawdown_r": round(max_drawdown_r, 2),
        "sharpe_ratio": round(sharpe_ratio, 2),
    }

    # Group by rule/strategy
    strategy_stats = {}
    for signal in closed_signals:
        strategy_name = signal.strategy_name or "Unknown"

        if strategy_name not in strategy_stats:
            strategy_stats[strategy_name] = {
                "name": strategy_name,
                "signals": [],
                "net_r_multiple": 0,
            }

        strategy_stats[strategy_name]["signals"].append(signal)
        strategy_stats[strategy_name]["net_r_multiple"] += _r_multiple(signal)

    rules_performance = []
    for strategy_name, data in strategy_stats.items():
        strategy_signals = data["signals"]
        strategy_wins = [s for s in strategy_signals if _is_win(s) is True]
        strategy_losses = [s for s in strategy_signals if _is_win(s) is False]

        gains_r = sum(_r_multiple(s) for s in strategy_wins)
        losses_r = abs(sum(_r_multiple(s) for s in strategy_losses))

        rules_performance.append({
            "name": strategy_name,
            "total_signals": len(strategy_signals),
            "winning_signals": len(strategy_wins),
            "losing_signals": len(strategy_losses),
            "win_rate": round((len(strategy_wins) / len(strategy_signals) * 100), 2) if strategy_signals else 0,
            "net_r_multiple": round(data["net_r_multiple"], 2),
            "avg_r_multiple": round(data["net_r_multiple"] / len(strategy_signals), 2) if strategy_signals else 0,
            "profit_factor": _round_or_none(_profit_factor(gains_r, losses_r))
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
            "exit_price": signal.actual_exit,
            "r_multiple": round(_r_multiple(signal), 2),
            "status": signal.status.value,
            "risk_reward": signal.risk_reward_ratio
        })

    return {
        "summary": summary,
        "rules": rules_performance,
        "trades": trades
    }

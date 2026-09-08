"""Signals API Routes"""

import os
import re
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

# Add engine src to path to import models
engine_src = Path(__file__).parent.parent.parent.parent / "engine" / "src"
sys.path.insert(0, str(engine_src))

from database.models import Signal, SignalStatus, SignalDirection
from database.signal_repository import SignalRepository
from database.settings_repository import SettingsRepository

# Import API models
from src.models.signal import (
    SignalResponse,
    SignalList,
    PriceUpdate,
    ServiceStatus,
    PerformanceStats
)
from src.database import get_db
from src.worker_status import derive_worker_status

router = APIRouter(prefix="/v1/signals", tags=["signals"])


def _parse_timeframe_hours(timeframe: str) -> float:
    """Parse a timeframe string like '1h', '4H', '15m' into hours. Falls back to 1h."""
    match = re.match(r"(\d+)\s*([hHmM])", timeframe or "")
    if not match:
        return 1.0
    value, unit = int(match.group(1)), match.group(2).lower()
    return value / 60 if unit == "m" else float(value)


@router.get("/history")
async def get_signals_history(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None),
    strategy: Optional[str] = Query(None),
    timeframe: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get signal history with limit and filters.

    Args:
        limit: Number of signals to return
        offset: Offset for pagination
        status: Filter by status (optional)
        strategy: Filter by strategy (optional)
        timeframe: Filter by timeframe (optional)
        db: Database session

    Returns:
        List of signals with total count
    """
    query = db.query(Signal)

    # Apply filters
    if status:
        try:
            status_enum = SignalStatus(status)
            query = query.filter(Signal.status == status_enum)
        except ValueError:
            pass

    if strategy:
        query = query.filter(Signal.strategy_name == strategy)

    if timeframe:
        query = query.filter(Signal.timeframe == timeframe)

    # Get total count
    total = query.count()

    # Get paginated signals
    signals = query.order_by(desc(Signal.timestamp)).offset(offset).limit(limit).all()

    return {
        "signals": [
            {
                "id": s.id,
                "reference_id": s.reference_id,
                "timestamp": s.timestamp.isoformat() if s.timestamp else None,
                "symbol": s.symbol,
                "timeframe": s.timeframe,
                "strategy_name": s.strategy_name,
                "direction": s.direction.value,
                "entry_price": float(s.entry_price) if s.entry_price else 0.0,
                "stop_loss": float(s.stop_loss) if s.stop_loss else 0.0,
                "take_profit": float(s.take_profit) if s.take_profit else 0.0,
                "confidence": float(s.confidence) if s.confidence else 0.0,
                "risk_pips": float(s.risk_pips) if s.risk_pips else 0.0,
                "reward_pips": float(s.reward_pips) if s.reward_pips else 0.0,
                "risk_reward_ratio": float(s.risk_reward_ratio) if s.risk_reward_ratio else 0.0,
                "status": s.status.value,
                "pnl": float(s.pnl) if s.pnl else None,
                "pnl_pct": float(s.pnl_pct) if s.pnl_pct else None,
            } for s in signals
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/", response_model=SignalList)
async def get_signals(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status: Optional[str] = None,
    direction: Optional[str] = None,
    days: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Get list of signals with pagination and filters.

    Args:
        page: Page number (1-indexed)
        page_size: Number of signals per page
        status: Filter by status (pending, active, closed_tp, closed_sl, etc.)
        direction: Filter by direction (LONG, SHORT)
        days: Get signals from last N days
        db: Database session

    Returns:
        List of signals with metadata
    """
    query = db.query(Signal)

    # Apply filters
    if status:
        try:
            status_enum = SignalStatus[status.upper()]
            query = query.filter(Signal.status == status_enum)
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    if direction:
        try:
            direction_enum = SignalDirection[direction.upper()]
            query = query.filter(Signal.direction == direction_enum)
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid direction: {direction}")

    if days:
        since = datetime.now() - timedelta(days=days)
        query = query.filter(Signal.timestamp >= since)

    # Get total count
    total = query.count()

    # Order by timestamp (newest first) and paginate
    offset = (page - 1) * page_size
    signals = query.order_by(desc(Signal.timestamp)).offset(offset).limit(page_size).all()

    # Convert to response models
    signal_responses = []
    for signal in signals:
        signal_responses.append(SignalResponse(
            id=signal.id,
            reference_id=signal.reference_id,
            timestamp=signal.timestamp,
            symbol=signal.symbol,
            timeframe=signal.timeframe,
            strategy_name=signal.strategy_name,
            direction=signal.direction.value,
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            confidence=signal.confidence,
            status=signal.status.value,
            risk_reward_ratio=signal.risk_reward_ratio,
            risk_pips=signal.risk_pips,
            reward_pips=signal.reward_pips,
            mt5_ticket=signal.mt5_ticket,
            actual_entry=signal.actual_entry,
            actual_exit=signal.actual_exit,
            executed_at=signal.executed_at,
            closed_at=signal.closed_at,
            pnl=signal.pnl,
            pnl_pct=signal.pnl_pct,
            pnl_pips=signal.pnl_pips,
            notes=signal.notes,
            error_message=signal.error_message,
            created_at=signal.created_at,
            updated_at=signal.updated_at
        ))

    return SignalList(
        total=total,
        signals=signal_responses,
        page=page,
        page_size=page_size
    )


@router.get("/{signal_id}", response_model=SignalResponse)
async def get_signal(signal_id: int, db: Session = Depends(get_db)):
    """
    Get a single signal by ID.

    Args:
        signal_id: Signal ID
        db: Database session

    Returns:
        Signal details
    """
    signal = db.query(Signal).filter(Signal.id == signal_id).first()

    if not signal:
        raise HTTPException(status_code=404, detail=f"Signal {signal_id} not found")

    return SignalResponse(
        id=signal.id,
        reference_id=signal.reference_id,
        timestamp=signal.timestamp,
        symbol=signal.symbol,
        timeframe=signal.timeframe,
        strategy_name=signal.strategy_name,
        direction=signal.direction.value,
        entry_price=signal.entry_price,
        stop_loss=signal.stop_loss,
        take_profit=signal.take_profit,
        confidence=signal.confidence,
        status=signal.status.value,
        risk_reward_ratio=signal.risk_reward_ratio,
        risk_pips=signal.risk_pips,
        reward_pips=signal.reward_pips,
        mt5_ticket=signal.mt5_ticket,
        actual_entry=signal.actual_entry,
        actual_exit=signal.actual_exit,
        executed_at=signal.executed_at,
        closed_at=signal.closed_at,
        pnl=signal.pnl,
        pnl_pct=signal.pnl_pct,
        pnl_pips=signal.pnl_pips,
        notes=signal.notes,
        error_message=signal.error_message,
        created_at=signal.created_at,
        updated_at=signal.updated_at
    )


@router.delete("/{signal_id}")
async def delete_signal(signal_id: int, db: Session = Depends(get_db)):
    """
    Permanently delete a signal — for cleaning up a genuine data-entry error
    (e.g. a duplicate signal from a worker restart re-evaluating an
    already-processed candle; see
    docs/superpowers/specs/strategy-ledger.md). Not for closing/cancelling a
    real signal — use its normal status lifecycle for that.

    Args:
        signal_id: Signal ID
        db: Database session

    Returns:
        Confirmation of deletion
    """
    repo = SignalRepository(db)
    deleted = repo.delete(signal_id)

    if not deleted:
        raise HTTPException(status_code=404, detail=f"Signal {signal_id} not found")

    return {"success": True, "deleted_id": signal_id}


@router.get("/stats/performance", response_model=PerformanceStats)
async def get_performance_stats(
    days: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Get signal performance statistics.

    Delegates to SignalRepository.get_performance_stats() — the same
    R-multiple math the weekly Telegram report uses — instead of the old
    inline implementation here, which computed wins/losses from `Signal.pnl`.
    `pnl` is always NULL in signals-only mode (no real account behind these
    signals yet), so that implementation silently counted every closed
    signal as neither a win nor a loss and pinned win_rate at 0%.

    Args:
        days: Calculate stats for last N days (default: all time, via a
            30-year lookback since the repository method requires a value)
        db: Database session

    Returns:
        Performance statistics
    """
    repo = SignalRepository(db)
    stats = repo.get_performance_stats(days=days or 365 * 30)

    return PerformanceStats(
        total_signals=stats['total_signals'],
        total_closed=stats['tp_hits'] + stats['sl_hits'] + stats['closed_manual'],
        win_count=stats['tp_hits'],
        loss_count=stats['sl_hits'],
        win_rate=stats['win_rate'],
        avg_r_multiple=stats['avg_r_multiple'],
        net_r_multiple=stats['net_r_multiple'],
        profit_factor=stats['profit_factor'],
        largest_win_r=stats['largest_win_r'],
        largest_loss_r=stats['largest_loss_r'],
    )


@router.get("/price/current", response_model=PriceUpdate)
async def get_current_price():
    """
    Get current gold price from Yahoo Finance.

    Returns:
        Current price update
    """
    try:
        import yfinance as yf
        ticker = yf.Ticker("GC=F")
        data = ticker.history(period="1d", interval="1m")

        if data.empty:
            raise HTTPException(status_code=503, detail="Price data unavailable")

        latest_price = float(data['Close'].iloc[-1])

        # Calculate change if we have enough data
        change = None
        change_pct = None
        if len(data) > 1:
            prev_price = float(data['Close'].iloc[-2])
            change = latest_price - prev_price
            change_pct = (change / prev_price) * 100

        return PriceUpdate(
            symbol="XAUUSD",
            price=latest_price,
            timestamp=datetime.now(),
            change=change,
            change_pct=change_pct
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch price: {str(e)}")


@router.get("/service/status", response_model=ServiceStatus)
async def get_service_status(db: Session = Depends(get_db)):
    """
    Get signal service status.

    Liveness/candle-progress comes from the worker's own heartbeat (see
    worker_status.derive_worker_status) rather than being inferred from
    signal staleness — a worker that's healthy but simply hasn't generated a
    new signal recently used to be misreported as "stopped".

    Returns:
        Service status information
    """
    # Get latest signal to check if service is running
    latest_signal = db.query(Signal).order_by(desc(Signal.created_at)).first()

    # Timeframe actually in use, from the most recent signal (falls back to the
    # TIMEFRAME env var, then "1h", if no signals exist yet)
    timeframe = (latest_signal.timeframe if latest_signal else None) or os.getenv("TIMEFRAME", "1h")
    timeframe_hours = _parse_timeframe_hours(timeframe)

    settings_repo = SettingsRepository(db)
    heartbeat = settings_repo.get('worker_heartbeat', default={}) or {}
    worker_status = derive_worker_status(heartbeat, timeframe=timeframe, now=datetime.now())

    is_running = worker_status.is_running
    last_candle_time = latest_signal.created_at if latest_signal else None

    if not heartbeat and latest_signal:
        # No heartbeat has ever been written (e.g. worker never started this
        # deploy) — fall back to the old staleness heuristic rather than
        # just reporting "stopped" outright.
        time_since_last = datetime.now() - last_candle_time
        is_running = time_since_last.total_seconds() < (5 * timeframe_hours * 3600)

    # Count signals
    total_signals = db.query(Signal).count()

    # Calculate signal rate
    signal_rate = None
    if total_signals > 0:
        first_signal = db.query(Signal).order_by(Signal.created_at).first()
        if first_signal:
            time_span = datetime.now() - first_signal.created_at
            hours = time_span.total_seconds() / 3600
            estimated_candles = int(hours / timeframe_hours)
            if estimated_candles > 0:
                signal_rate = (total_signals / estimated_candles) * 100

    # Get current price
    current_price = None
    try:
        import yfinance as yf
        ticker = yf.Ticker("GC=F")
        data = ticker.history(period="1d", interval="1m")
        if not data.empty:
            current_price = float(data['Close'].iloc[-1])
    except:
        pass

    # Calculate next candle time from the actual timeframe interval (works for
    # sub-hourly timeframes like 15m too, unlike hour-of-day snapping)
    now = datetime.now()
    timeframe_minutes = max(1, round(timeframe_hours * 60))
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    minutes_since_midnight = (now - midnight).total_seconds() / 60
    next_boundary_minutes = (int(minutes_since_midnight // timeframe_minutes) + 1) * timeframe_minutes
    next_candle_time = midnight + timedelta(minutes=next_boundary_minutes)

    return ServiceStatus(
        status="running" if is_running else "stopped",
        uptime_hours=worker_status.uptime_hours,
        candles_processed=worker_status.candles_processed,
        signals_generated=worker_status.signals_generated,
        signal_rate=signal_rate,
        last_candle_time=last_candle_time,
        next_candle_time=next_candle_time,
        current_price=current_price,
        datafeed_type="yahoo",
        symbol="XAUUSD",
        timeframe=timeframe.upper()
    )

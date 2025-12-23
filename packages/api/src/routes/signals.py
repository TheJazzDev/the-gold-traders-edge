"""Signals API Routes"""

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

# Import API models
from src.models.signal import (
    SignalResponse,
    SignalList,
    PriceUpdate,
    ServiceStatus,
    PerformanceStats
)
from src.database import get_db

router = APIRouter(prefix="/v1/signals", tags=["signals"])


@router.get("/history")
async def get_signals_history(
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get signal history with limit.

    Args:
        limit: Number of signals to return
        db: Database session

    Returns:
        List of recent signals
    """
    signals = db.query(Signal).order_by(desc(Signal.timestamp)).limit(limit).all()

    return {
        "signals": [
            {
                "id": s.id,
                "timestamp": s.timestamp.isoformat() if s.timestamp else None,
                "symbol": s.symbol,
                "timeframe": s.timeframe,
                "strategy_name": s.strategy_name,
                "direction": s.direction.value,
                "entry_price": s.entry_price,
                "stop_loss": s.stop_loss,
                "take_profit": s.take_profit,
                "confidence": s.confidence,
                "status": s.status.value,
                "pnl": s.pnl,
                "pnl_pct": s.pnl_pct,
                "risk_reward_ratio": s.risk_reward_ratio
            } for s in signals
        ]
    }


@router.get("/latest")
async def get_latest_signals(
    timeframe: Optional[str] = None,
    rules: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get latest signals with optional filters.

    Args:
        timeframe: Filter by timeframe (optional)
        rules: Filter by strategy/rules (optional)
        db: Database session

    Returns:
        Latest signals matching filters
    """
    query = db.query(Signal)

    # Apply filters
    if timeframe:
        query = query.filter(Signal.timeframe == timeframe)

    if rules:
        query = query.filter(Signal.strategy_name == rules)

    # Get latest signals
    signals = query.order_by(desc(Signal.timestamp)).limit(10).all()

    return {
        "timestamp": datetime.now().isoformat(),
        "symbol": "XAUUSD",
        "timeframe": timeframe or "4h",
        "current_price": None,  # Will be populated by market data if needed
        "signals": [
            {
                "id": s.id,
                "timestamp": s.timestamp.isoformat() if s.timestamp else None,
                "direction": s.direction.value,
                "entry_price": s.entry_price,
                "stop_loss": s.stop_loss,
                "take_profit": s.take_profit,
                "confidence": s.confidence,
                "status": s.status.value,
                "strategy_name": s.strategy_name,
                "risk_reward_ratio": s.risk_reward_ratio
            } for s in signals
        ],
        "market_context": {
            "trend": "neutral",
            "volatility": "moderate",
            "atr": 15.0
        }
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


@router.get("/stats/performance", response_model=PerformanceStats)
async def get_performance_stats(
    days: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Get signal performance statistics.

    Args:
        days: Calculate stats for last N days (default: all time)
        db: Database session

    Returns:
        Performance statistics
    """
    query = db.query(Signal)

    if days:
        since = datetime.now() - timedelta(days=days)
        query = query.filter(Signal.timestamp >= since)

    # Get closed signals
    closed_signals = query.filter(
        Signal.status.in_([
            SignalStatus.CLOSED_TP,
            SignalStatus.CLOSED_SL,
            SignalStatus.CLOSED_MANUAL
        ])
    ).all()

    total_signals = query.count()
    total_closed = len(closed_signals)

    if total_closed == 0:
        return PerformanceStats(
            total_signals=total_signals,
            total_closed=0,
            win_count=0,
            loss_count=0,
            win_rate=0.0,
            total_pnl=0.0,
            total_pnl_pct=0.0,
            avg_win=0.0,
            avg_loss=0.0,
            profit_factor=0.0,
            largest_win=0.0,
            largest_loss=0.0
        )

    # Calculate stats
    wins = [s for s in closed_signals if s.pnl and s.pnl > 0]
    losses = [s for s in closed_signals if s.pnl and s.pnl < 0]

    win_count = len(wins)
    loss_count = len(losses)
    win_rate = (win_count / total_closed) * 100 if total_closed > 0 else 0

    total_pnl = sum(s.pnl for s in closed_signals if s.pnl)
    total_pnl_pct = sum(s.pnl_pct for s in closed_signals if s.pnl_pct)

    avg_win = sum(s.pnl for s in wins) / win_count if win_count > 0 else 0
    avg_loss = sum(s.pnl for s in losses) / loss_count if loss_count > 0 else 0

    total_wins = sum(s.pnl for s in wins)
    total_losses = abs(sum(s.pnl for s in losses))
    profit_factor = total_wins / total_losses if total_losses > 0 else 0

    largest_win = max((s.pnl for s in wins), default=0)
    largest_loss = min((s.pnl for s in losses), default=0)

    return PerformanceStats(
        total_signals=total_signals,
        total_closed=total_closed,
        win_count=win_count,
        loss_count=loss_count,
        win_rate=win_rate,
        total_pnl=total_pnl,
        total_pnl_pct=total_pnl_pct,
        avg_win=avg_win,
        avg_loss=avg_loss,
        profit_factor=profit_factor,
        largest_win=largest_win,
        largest_loss=largest_loss
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

    Returns:
        Service status information
    """
    # Get latest signal to check if service is running
    latest_signal = db.query(Signal).order_by(desc(Signal.created_at)).first()

    # Check if service has run recently (within last 5 hours for 4H timeframe)
    is_running = False
    last_candle_time = None

    if latest_signal:
        last_candle_time = latest_signal.created_at
        time_since_last = datetime.now() - last_candle_time
        is_running = time_since_last.total_seconds() < (5 * 3600)  # 5 hours

    # Count signals
    total_signals = db.query(Signal).count()

    # Calculate signal rate
    signal_rate = None
    if total_signals > 0:
        # Assume 4H timeframe, estimate candles processed
        first_signal = db.query(Signal).order_by(Signal.created_at).first()
        if first_signal:
            time_span = datetime.now() - first_signal.created_at
            hours = time_span.total_seconds() / 3600
            estimated_candles = int(hours / 4)  # 4H timeframe
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

    # Calculate next candle time (4H intervals: 00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC)
    now = datetime.now()
    current_hour = now.hour
    next_close_hour = ((current_hour // 4) + 1) * 4

    if next_close_hour >= 24:
        next_candle_time = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    else:
        next_candle_time = now.replace(hour=next_close_hour, minute=0, second=0, microsecond=0)

    return ServiceStatus(
        status="running" if is_running else "stopped",
        candles_processed=total_signals,  # Approximate
        signals_generated=total_signals,
        signal_rate=signal_rate,
        last_candle_time=last_candle_time,
        next_candle_time=next_candle_time,
        current_price=current_price,
        datafeed_type="yahoo",
        symbol="XAUUSD",
        timeframe="4H"
    )

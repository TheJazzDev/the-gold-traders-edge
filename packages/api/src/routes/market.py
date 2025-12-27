"""Market Data API Routes"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from zoneinfo import ZoneInfo

router = APIRouter(prefix="/v1/market", tags=["market"])


@router.get("/ohlcv")
async def get_ohlcv(
    symbol: str = Query("XAUUSD", description="Trading symbol"),
    timeframe: str = Query("4h", description="Timeframe (1h, 4h, 1d)"),
    limit: int = Query(100, ge=1, le=500, description="Number of candles")
):
    """
    Get OHLCV (Open, High, Low, Close, Volume) data for a symbol.

    Args:
        symbol: Trading symbol (default: XAUUSD)
        timeframe: Timeframe (default: 4h)
        limit: Number of candles to return (default: 100)

    Returns:
        OHLCV data
    """
    try:
        import yfinance as yf

        # Map timeframe to yfinance intervals
        interval_map = {
            "1m": "1m",
            "5m": "5m",
            "15m": "15m",
            "30m": "30m",
            "1h": "1h",
            "4h": "1h",  # We'll resample 1h to 4h
            "1d": "1d"
        }

        interval = interval_map.get(timeframe.lower(), "1h")

        # Calculate period based on timeframe and limit
        if timeframe.lower() == "4h":
            period_days = (limit * 4) // 24 + 1
        elif timeframe.lower() == "1h":
            period_days = limit // 24 + 1
        else:
            period_days = limit + 1

        period_days = min(period_days, 60)  # Max 60 days for free tier

        # Fetch data from Yahoo Finance
        ticker = yf.Ticker("GC=F")  # Gold futures
        data = ticker.history(period=f"{period_days}d", interval=interval)

        if data.empty:
            raise HTTPException(status_code=503, detail="Market data unavailable")

        # Resample to 4h if needed
        if timeframe.lower() == "4h":
            data = data.resample('4h').agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            }).dropna()

        # Limit to requested number of candles
        data = data.tail(limit)

        # Convert to response format
        candles = []
        for timestamp, row in data.iterrows():
            candles.append({
                "timestamp": timestamp.isoformat(),
                "open": float(row['Open']),
                "high": float(row['High']),
                "low": float(row['Low']),
                "close": float(row['Close']),
                "volume": int(row['Volume']) if row['Volume'] else 0
            })

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "candles": candles
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch market data: {str(e)}"
        )


@router.get("/price/latest")
async def get_latest_price(
    symbol: str = Query("XAUUSD", description="Trading symbol")
):
    """
    Get the latest price for a symbol.

    Args:
        symbol: Trading symbol (default: XAUUSD)

    Returns:
        Latest price data
    """
    try:
        import yfinance as yf

        ticker = yf.Ticker("GC=F")
        data = ticker.history(period="1d", interval="1m")

        if data.empty:
            raise HTTPException(status_code=503, detail="Price data unavailable")

        latest_price = float(data['Close'].iloc[-1])
        timestamp = data.index[-1]

        # Calculate change if we have enough data
        change = None
        change_pct = None
        if len(data) > 1:
            prev_price = float(data['Close'].iloc[-2])
            change = latest_price - prev_price
            change_pct = (change / prev_price) * 100

        return {
            "symbol": symbol,
            "price": latest_price,
            "timestamp": timestamp.isoformat(),
            "change": change,
            "change_pct": change_pct
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch price: {str(e)}"
        )


@router.get("/status")
async def get_market_status():
    """
    Get market status (open/closed) for Forex markets.

    Forex markets (including XAUUSD) are open:
    - 24 hours a day, 5 days a week
    - Sunday 5:00 PM EST to Friday 5:00 PM EST
    - Closed on weekends (Friday 5pm EST - Sunday 5pm EST)

    Returns:
        Market status with open/closed info and next market event
    """
    try:
        # Get current time in EST/EDT (New York time zone)
        ny_tz = ZoneInfo("America/New_York")
        now = datetime.now(ny_tz)

        # Get current day of week (0=Monday, 6=Sunday)
        weekday = now.weekday()
        current_hour = now.hour
        current_minute = now.minute

        # Market is CLOSED on:
        # - Friday after 5:00 PM EST
        # - All day Saturday
        # - Sunday before 5:00 PM EST

        is_open = True
        reason = None
        next_open = None
        next_close = None

        # Friday after 5pm
        if weekday == 4 and (current_hour >= 17):  # Friday = 4
            is_open = False
            reason = "Weekend - Market closed"
            # Calculate next Sunday 5pm
            days_until_sunday = (6 - weekday) % 7
            next_open_dt = now.replace(hour=17, minute=0, second=0, microsecond=0) + timedelta(days=days_until_sunday + 2)
            next_open = next_open_dt.isoformat()

        # Saturday (all day)
        elif weekday == 5:  # Saturday = 5
            is_open = False
            reason = "Weekend - Market closed"
            # Next open: Sunday 5pm
            days_until_sunday = 1
            next_open_dt = now.replace(hour=17, minute=0, second=0, microsecond=0) + timedelta(days=days_until_sunday)
            next_open = next_open_dt.isoformat()

        # Sunday before 5pm
        elif weekday == 6 and current_hour < 17:  # Sunday = 6
            is_open = False
            reason = "Weekend - Market opens at 5:00 PM EST"
            next_open_dt = now.replace(hour=17, minute=0, second=0, microsecond=0)
            next_open = next_open_dt.isoformat()

        # Market is open
        else:
            is_open = True
            reason = "Forex market is open 24 hours"

            # Calculate next close (Friday 5pm)
            days_until_friday = (4 - weekday) % 7
            if days_until_friday == 0 and current_hour >= 17:
                days_until_friday = 7
            next_close_dt = now.replace(hour=17, minute=0, second=0, microsecond=0) + timedelta(days=days_until_friday)
            next_close = next_close_dt.isoformat()

        # Calculate time until next event
        if not is_open and next_open:
            next_open_dt = datetime.fromisoformat(next_open)
            time_until = next_open_dt - now
            hours_until = int(time_until.total_seconds() // 3600)
            minutes_until = int((time_until.total_seconds() % 3600) // 60)
            time_until_text = f"{hours_until}h {minutes_until}m"
        elif is_open and next_close:
            next_close_dt = datetime.fromisoformat(next_close)
            time_until = next_close_dt - now
            hours_until = int(time_until.total_seconds() // 3600)
            minutes_until = int((time_until.total_seconds() % 3600) // 60)
            time_until_text = f"{hours_until}h {minutes_until}m"
        else:
            time_until_text = None

        return {
            "is_open": is_open,
            "reason": reason,
            "current_time": now.isoformat(),
            "timezone": "America/New_York (EST/EDT)",
            "next_open": next_open,
            "next_close": next_close,
            "time_until_event": time_until_text,
            "market_hours": {
                "description": "Forex markets open 24/5",
                "open": "Sunday 5:00 PM EST",
                "close": "Friday 5:00 PM EST"
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check market status: {str(e)}"
        )

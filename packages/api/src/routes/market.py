"""Market Data API Routes"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Query

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

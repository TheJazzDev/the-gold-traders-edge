"""
Market router - Market data endpoints.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from data.loader import GoldDataLoader

router = APIRouter()


class Candle(BaseModel):
    """OHLCV candle model."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


class OHLCVResponse(BaseModel):
    """Response model for OHLCV data."""
    symbol: str
    timeframe: str
    candles: List[Candle]


@router.get("/ohlcv", response_model=OHLCVResponse)
async def get_ohlcv(
    timeframe: str = Query("4h", description="Timeframe: 1h, 4h, or 1d"),
    limit: int = Query(100, ge=1, le=5000, description="Number of candles")
):
    """
    Get OHLCV (candlestick) data for XAUUSD.

    Returns historical price data for charting and analysis.
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

        # Get last N candles
        df = df.tail(limit)

        # Convert to candles
        candles = []
        for idx, row in df.iterrows():
            candle = Candle(
                timestamp=idx,
                open=float(row['open']),
                high=float(row['high']),
                low=float(row['low']),
                close=float(row['close']),
                volume=int(row['volume'])
            )
            candles.append(candle)

        return OHLCVResponse(
            symbol="XAUUSD",
            timeframe=timeframe,
            candles=candles
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching OHLCV data: {str(e)}")


@router.get("/indicators")
async def get_indicators(timeframe: str = Query("4h")):
    """
    Get current technical indicators for XAUUSD.

    Returns key indicators used by the trading strategy.
    """
    try:
        # Load latest data
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

        # Get latest price
        latest = df.iloc[-1]
        current_price = float(latest['close'])

        # Calculate simple indicators (placeholder - implement full indicator calculation)
        recent_df = df.tail(50)
        ema_20 = recent_df['close'].ewm(span=20).mean().iloc[-1]
        ema_50 = recent_df['close'].ewm(span=50).mean().iloc[-1] if len(recent_df) >= 50 else ema_20

        # ATR calculation
        high_low = recent_df['high'] - recent_df['low']
        high_close = abs(recent_df['high'] - recent_df['close'].shift())
        low_close = abs(recent_df['low'] - recent_df['close'].shift())
        true_range = high_low.combine(high_close, max).combine(low_close, max)
        atr = true_range.rolling(14).mean().iloc[-1]

        # Simple Fibonacci levels (from recent high/low)
        recent_high = recent_df['high'].max()
        recent_low = recent_df['low'].min()
        diff = recent_high - recent_low

        return {
            "timestamp": datetime.now().isoformat(),
            "price": current_price,
            "indicators": {
                "ema_20": float(ema_20),
                "ema_50": float(ema_50),
                "atr_14": float(atr),
                "fibonacci_levels": {
                    "0.236": float(recent_high - (diff * 0.236)),
                    "0.382": float(recent_high - (diff * 0.382)),
                    "0.618": float(recent_high - (diff * 0.618)),
                    "0.786": float(recent_high - (diff * 0.786))
                }
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating indicators: {str(e)}")

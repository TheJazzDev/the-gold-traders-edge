"""
Signals router - Trading signal endpoints.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from data.loader import GoldDataLoader
from signals.gold_strategy import GoldStrategy, create_strategy_function
from backtesting.engine import BacktestEngine

router = APIRouter()


class SignalDetail(BaseModel):
    """Trading signal model."""
    rule: str
    signal: str  # LONG, SHORT, or NONE
    entry_price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    confidence: float
    risk_reward_ratio: Optional[float] = None
    generated_at: datetime


class SignalsResponse(BaseModel):
    """Response model for latest signals."""
    timestamp: datetime
    symbol: str
    timeframe: str
    current_price: float
    signals: List[SignalDetail]
    market_context: dict


@router.get("/latest", response_model=SignalsResponse)
async def get_latest_signals(
    timeframe: str = Query("4h", description="Timeframe: 4h or 1d"),
    rules: Optional[str] = Query(None, description="Comma-separated rule numbers (e.g., 1,2,5,6)")
):
    """
    Get the latest trading signals for XAUUSD.

    Returns real-time signals based on the most recent market data.
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
                detail=f"No data available for timeframe {timeframe}. Please fetch data first."
            )

        data_file = sorted(matching_files)[-1]
        df = loader.load_from_csv(str(data_file))

        if len(df) < 100:
            raise HTTPException(
                status_code=400,
                detail="Insufficient data to generate signals"
            )

        # Initialize strategy
        strategy = GoldStrategy()

        # Configure enabled rules
        if rules:
            for rule in strategy.rules_enabled:
                strategy.rules_enabled[rule] = False

            rule_map = {
                '1': 'rule_1_618_retracement',
                '2': 'rule_2_786_deep_discount',
                '3': 'rule_3_236_shallow_pullback',
                '4': 'rule_4_consolidation_break',
                '5': 'rule_5_ath_breakout_retest',
                '6': 'rule_6_50_momentum',
            }

            for rule_num in rules.split(','):
                rule_num = rule_num.strip()
                if rule_num in rule_map:
                    strategy.rules_enabled[rule_map[rule_num]] = True

        # Get the latest candle
        latest_candle = df.iloc[-1]
        current_price = float(latest_candle['close'])
        timestamp = df.index[-1]

        # Run strategy on latest data (last 100 candles for indicators)
        recent_df = df.tail(100).copy()
        strategy_func = create_strategy_function(strategy)

        # Generate signal (evaluate on the latest candle)
        signal_result = strategy_func(recent_df, len(recent_df) - 1)

        # Extract active signals
        active_signals = []

        if signal_result and hasattr(signal_result, 'signal'):
            for rule_name, enabled in strategy.rules_enabled.items():
                if enabled:
                    # Create signal detail (simplified for MVP)
                    signal_detail = SignalDetail(
                        rule=rule_name.replace('_', ' ').title(),
                        signal=signal_result.signal if signal_result.signal else "NONE",
                        entry_price=current_price,
                        stop_loss=signal_result.stop_loss if hasattr(signal_result, 'stop_loss') else None,
                        take_profit=signal_result.take_profit if hasattr(signal_result, 'take_profit') else None,
                        confidence=0.75,  # Placeholder - implement confidence scoring
                        risk_reward_ratio=1.75,  # Placeholder
                        generated_at=datetime.now()
                    )
                    if signal_detail.signal != "NONE":
                        active_signals.append(signal_detail)

        # Market context
        market_context = {
            "trend": "bullish" if len(active_signals) > 0 else "neutral",
            "volatility": "moderate",
            "atr": 15.0  # Placeholder - calculate real ATR
        }

        return SignalsResponse(
            timestamp=datetime.now(),
            symbol="XAUUSD",
            timeframe=timeframe,
            current_price=current_price,
            signals=active_signals,
            market_context=market_context
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating signals: {str(e)}")


@router.get("/history")
async def get_signal_history(
    timeframe: str = Query("4h", description="Timeframe: 4h or 1d"),
    limit: int = Query(100, ge=1, le=1000, description="Number of historical signals")
):
    """
    Get historical trading signals.

    Returns past signals and their outcomes for analysis.
    """
    # Placeholder - implement database storage for signal history
    return {
        "signals": [],
        "message": "Signal history tracking will be implemented with database integration",
        "total": 0
    }

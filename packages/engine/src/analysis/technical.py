"""
Technical Analysis Module
Provides tools for analyzing gold price action including:
- Fibonacci retracement levels
- Swing high/low detection
- Trend analysis
- Support/Resistance zones
"""

import pandas as pd
import numpy as np
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
from enum import Enum


class TrendDirection(Enum):
    UPTREND = "uptrend"
    DOWNTREND = "downtrend"
    SIDEWAYS = "sideways"


@dataclass
class SwingPoint:
    """Represents a swing high or swing low point."""
    index: pd.Timestamp
    price: float
    is_high: bool  # True for swing high, False for swing low
    strength: int  # Number of candles on each side that confirm this swing


@dataclass
class FibonacciLevel:
    """Represents a Fibonacci retracement level."""
    level: float  # 0.236, 0.382, 0.5, 0.618, 0.786, etc.
    price: float
    label: str


@dataclass
class ZoneInfo:
    """Represents a price zone (support/resistance)."""
    price_low: float
    price_high: float
    zone_type: str  # 'support', 'resistance', 'fib_zone'
    strength: int  # How many times price has reacted to this zone
    fib_level: Optional[float] = None


class TechnicalAnalysis:
    """
    Core technical analysis class for gold trading.
    """
    
    # Standard Fibonacci levels
    FIB_LEVELS = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
    
    # Extended Fibonacci levels (for extensions)
    FIB_EXTENSIONS = [1.272, 1.414, 1.618, 2.0, 2.618]
    
    def __init__(self, df: pd.DataFrame):
        """
        Initialize with OHLCV data.
        
        Args:
            df: DataFrame with columns ['open', 'high', 'low', 'close', 'volume']
        """
        self.df = df.copy()
        self._validate_data()
    
    def _validate_data(self):
        """Ensure required columns exist."""
        required = ['open', 'high', 'low', 'close']
        missing = [col for col in required if col not in self.df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
    
    def detect_swing_points(
        self, 
        lookback: int = 5,
        min_strength: int = 2
    ) -> List[SwingPoint]:
        """
        Detect swing highs and swing lows.
        
        A swing high is a candle where the high is higher than the highs
        of `lookback` candles on both sides.
        
        Args:
            lookback: Number of candles to look back/forward
            min_strength: Minimum strength to qualify as a valid swing
        
        Returns:
            List of SwingPoint objects
        """
        swing_points = []
        highs = self.df['high'].values
        lows = self.df['low'].values
        indices = self.df.index
        
        for i in range(lookback, len(self.df) - lookback):
            # Check for swing high
            is_swing_high = True
            strength = 0
            
            for j in range(1, lookback + 1):
                if highs[i] > highs[i - j] and highs[i] > highs[i + j]:
                    strength += 1
                else:
                    is_swing_high = False
                    break
            
            if is_swing_high and strength >= min_strength:
                swing_points.append(SwingPoint(
                    index=indices[i],
                    price=highs[i],
                    is_high=True,
                    strength=strength
                ))
            
            # Check for swing low
            is_swing_low = True
            strength = 0
            
            for j in range(1, lookback + 1):
                if lows[i] < lows[i - j] and lows[i] < lows[i + j]:
                    strength += 1
                else:
                    is_swing_low = False
                    break
            
            if is_swing_low and strength >= min_strength:
                swing_points.append(SwingPoint(
                    index=indices[i],
                    price=lows[i],
                    is_high=False,
                    strength=strength
                ))
        
        # Sort by index
        swing_points.sort(key=lambda x: x.index)
        return swing_points
    
    def calculate_fibonacci_retracement(
        self,
        swing_low: float,
        swing_high: float,
        include_extensions: bool = False
    ) -> List[FibonacciLevel]:
        """
        Calculate Fibonacci retracement levels between two swing points.
        
        For an uptrend:
            - swing_low is the start (0%)
            - swing_high is the end (100%)
            - Retracement levels are measured from high going down
        
        Args:
            swing_low: Lower price point
            swing_high: Higher price point
            include_extensions: Whether to include extension levels
        
        Returns:
            List of FibonacciLevel objects
        """
        price_range = swing_high - swing_low
        fib_levels = []
        
        # Standard retracement levels (measured from high)
        for level in self.FIB_LEVELS:
            price = swing_high - (price_range * level)
            label = f"{level * 100:.1f}%"
            fib_levels.append(FibonacciLevel(level=level, price=price, label=label))
        
        # Extension levels (above the high)
        if include_extensions:
            for level in self.FIB_EXTENSIONS:
                price = swing_low + (price_range * level)
                label = f"{level * 100:.1f}% ext"
                fib_levels.append(FibonacciLevel(level=level, price=price, label=label))
        
        return fib_levels
    
    def get_fib_level_at_price(
        self,
        price: float,
        swing_low: float,
        swing_high: float
    ) -> float:
        """
        Calculate what Fibonacci level a given price represents.
        
        Args:
            price: Current price to check
            swing_low: Lower swing point
            swing_high: Upper swing point
        
        Returns:
            Fibonacci level as decimal (e.g., 0.618)
        """
        price_range = swing_high - swing_low
        if price_range == 0:
            return 0.0
        
        # Level from the high (for retracement)
        level = (swing_high - price) / price_range
        return round(level, 3)
    
    def is_near_fib_level(
        self,
        price: float,
        swing_low: float,
        swing_high: float,
        target_level: float = 0.786,
        tolerance: float = 0.02
    ) -> bool:
        """
        Check if price is near a specific Fibonacci level.
        
        Args:
            price: Price to check
            swing_low: Lower swing point
            swing_high: Upper swing point
            target_level: The Fib level to check against (e.g., 0.786)
            tolerance: Allowed deviation from the level
        
        Returns:
            True if price is within tolerance of the target Fib level
        """
        actual_level = self.get_fib_level_at_price(price, swing_low, swing_high)
        return abs(actual_level - target_level) <= tolerance
    
    def detect_trend(
        self,
        lookback: int = 50,
        method: str = "swing"
    ) -> TrendDirection:
        """
        Detect the current trend direction.
        
        Args:
            lookback: Number of candles to analyze
            method: 'swing' (higher highs/lows), 'ma' (moving averages), or 'linear'
        
        Returns:
            TrendDirection enum value
        """
        if len(self.df) < lookback:
            lookback = len(self.df)
        
        recent_data = self.df.tail(lookback)
        
        if method == "swing":
            return self._trend_by_swings(recent_data)
        elif method == "ma":
            return self._trend_by_ma(recent_data)
        elif method == "linear":
            return self._trend_by_linear_regression(recent_data)
        else:
            raise ValueError(f"Unknown method: {method}")
    
    def _trend_by_swings(self, df: pd.DataFrame) -> TrendDirection:
        """Detect trend by analyzing higher highs/lows or lower highs/lows."""
        swing_points = self.detect_swing_points(lookback=3, min_strength=1)
        
        if len(swing_points) < 4:
            return TrendDirection.SIDEWAYS
        
        # Get recent swing highs and lows
        recent_highs = [sp for sp in swing_points[-10:] if sp.is_high]
        recent_lows = [sp for sp in swing_points[-10:] if not sp.is_high]
        
        if len(recent_highs) < 2 or len(recent_lows) < 2:
            return TrendDirection.SIDEWAYS
        
        # Check for higher highs and higher lows (uptrend)
        higher_highs = recent_highs[-1].price > recent_highs[-2].price
        higher_lows = recent_lows[-1].price > recent_lows[-2].price
        
        # Check for lower highs and lower lows (downtrend)
        lower_highs = recent_highs[-1].price < recent_highs[-2].price
        lower_lows = recent_lows[-1].price < recent_lows[-2].price
        
        if higher_highs and higher_lows:
            return TrendDirection.UPTREND
        elif lower_highs and lower_lows:
            return TrendDirection.DOWNTREND
        else:
            return TrendDirection.SIDEWAYS
    
    def _trend_by_ma(self, df: pd.DataFrame) -> TrendDirection:
        """Detect trend using moving averages."""
        ma_fast = df['close'].rolling(window=10).mean()
        ma_slow = df['close'].rolling(window=30).mean()
        
        if ma_fast.iloc[-1] > ma_slow.iloc[-1] and ma_fast.iloc[-5] > ma_slow.iloc[-5]:
            return TrendDirection.UPTREND
        elif ma_fast.iloc[-1] < ma_slow.iloc[-1] and ma_fast.iloc[-5] < ma_slow.iloc[-5]:
            return TrendDirection.DOWNTREND
        else:
            return TrendDirection.SIDEWAYS
    
    def _trend_by_linear_regression(self, df: pd.DataFrame) -> TrendDirection:
        """Detect trend using linear regression slope."""
        y = df['close'].values
        x = np.arange(len(y))
        
        # Calculate slope
        slope = np.polyfit(x, y, 1)[0]
        
        # Normalize slope by average price
        normalized_slope = slope / np.mean(y)
        
        if normalized_slope > 0.0001:
            return TrendDirection.UPTREND
        elif normalized_slope < -0.0001:
            return TrendDirection.DOWNTREND
        else:
            return TrendDirection.SIDEWAYS
    
    def detect_breakout(
        self,
        lookback: int = 20,
        threshold: float = 0.5
    ) -> Dict:
        """
        Detect if price has broken out of a recent range.
        
        Args:
            lookback: Number of candles to define the range
            threshold: Percentage above/below range to confirm breakout
        
        Returns:
            Dict with breakout information
        """
        if len(self.df) < lookback + 1:
            return {"breakout": False}
        
        # Get the range (excluding the current candle)
        range_data = self.df.iloc[-(lookback + 1):-1]
        range_high = range_data['high'].max()
        range_low = range_data['low'].min()
        range_size = range_high - range_low
        
        current_close = self.df['close'].iloc[-1]
        current_high = self.df['high'].iloc[-1]
        current_low = self.df['low'].iloc[-1]
        
        # Check for breakout
        breakout_up = current_close > range_high + (range_size * threshold / 100)
        breakout_down = current_close < range_low - (range_size * threshold / 100)
        
        return {
            "breakout": breakout_up or breakout_down,
            "direction": "up" if breakout_up else ("down" if breakout_down else None),
            "range_high": range_high,
            "range_low": range_low,
            "current_price": current_close,
            "breakout_level": range_high if breakout_up else (range_low if breakout_down else None)
        }
    
    def detect_retest(
        self,
        breakout_level: float,
        tolerance_pct: float = 0.3,
        lookback: int = 10
    ) -> Dict:
        """
        Detect if price has retested a breakout level.
        
        Args:
            breakout_level: The price level that was broken
            tolerance_pct: Percentage tolerance for the retest
            lookback: Number of candles to look for the retest
        
        Returns:
            Dict with retest information
        """
        recent_data = self.df.tail(lookback)
        tolerance = breakout_level * (tolerance_pct / 100)
        
        retest_candles = []
        
        for idx, row in recent_data.iterrows():
            # Check if low touched the breakout level (for bullish retest)
            if abs(row['low'] - breakout_level) <= tolerance:
                retest_candles.append({
                    'index': idx,
                    'low': row['low'],
                    'close': row['close'],
                    'type': 'bullish_retest' if row['close'] > breakout_level else 'failed_retest'
                })
            # Check if high touched the breakout level (for bearish retest)
            elif abs(row['high'] - breakout_level) <= tolerance:
                retest_candles.append({
                    'index': idx,
                    'high': row['high'],
                    'close': row['close'],
                    'type': 'bearish_retest' if row['close'] < breakout_level else 'failed_retest'
                })
        
        return {
            "retest_found": len(retest_candles) > 0,
            "retest_candles": retest_candles,
            "breakout_level": breakout_level
        }
    
    def calculate_atr(self, period: int = 14) -> pd.Series:
        """
        Calculate Average True Range (ATR) for volatility-based stops.
        
        Args:
            period: ATR period
        
        Returns:
            Series of ATR values
        """
        high = self.df['high']
        low = self.df['low']
        close = self.df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()
        
        return atr
    
    def calculate_rsi(self, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index."""
        delta = self.df['close'].diff()

        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)

        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def calculate_ema(self, period: int = 20) -> pd.Series:
        """
        Calculate Exponential Moving Average.

        Args:
            period: EMA period

        Returns:
            Series of EMA values
        """
        return self.df['close'].ewm(span=period, adjust=False).mean()

    def calculate_sma(self, period: int = 20) -> pd.Series:
        """
        Calculate Simple Moving Average.

        Args:
            period: SMA period

        Returns:
            Series of SMA values
        """
        return self.df['close'].rolling(window=period).mean()
    
    def get_support_resistance_zones(
        self,
        lookback: int = 100,
        zone_tolerance: float = 0.5
    ) -> List[ZoneInfo]:
        """
        Identify key support and resistance zones.
        
        Args:
            lookback: Number of candles to analyze
            zone_tolerance: Percentage tolerance for zone detection
        
        Returns:
            List of ZoneInfo objects
        """
        if len(self.df) < lookback:
            lookback = len(self.df)
        
        data = self.df.tail(lookback)
        swing_points = self.detect_swing_points(lookback=5, min_strength=2)
        
        zones = []
        
        for sp in swing_points:
            tolerance = sp.price * (zone_tolerance / 100)
            
            # Check how many times price has reacted to this level
            reactions = 0
            for _, row in data.iterrows():
                if abs(row['high'] - sp.price) <= tolerance or abs(row['low'] - sp.price) <= tolerance:
                    reactions += 1
            
            zone_type = "resistance" if sp.is_high else "support"
            
            zones.append(ZoneInfo(
                price_low=sp.price - tolerance,
                price_high=sp.price + tolerance,
                zone_type=zone_type,
                strength=reactions
            ))
        
        # Sort by strength
        zones.sort(key=lambda x: x.strength, reverse=True)
        
        return zones


if __name__ == "__main__":
    # Example usage
    from data.loader import generate_sample_data
    
    # Generate sample data
    df = generate_sample_data(start_date="2023-01-01", end_date="2024-01-01")
    
    # Initialize analyzer
    ta = TechnicalAnalysis(df)
    
    # Detect swing points
    swings = ta.detect_swing_points(lookback=5)
    print(f"Found {len(swings)} swing points")
    
    # Get recent swing high and low for Fib calculation
    swing_highs = [s for s in swings if s.is_high]
    swing_lows = [s for s in swings if not s.is_high]
    
    if swing_highs and swing_lows:
        recent_high = swing_highs[-1]
        recent_low = swing_lows[-1]
        
        # Calculate Fibonacci levels
        fib_levels = ta.calculate_fibonacci_retracement(
            swing_low=recent_low.price,
            swing_high=recent_high.price
        )
        
        print("\nFibonacci Levels:")
        for fib in fib_levels:
            print(f"  {fib.label}: ${fib.price:.2f}")
    
    # Detect trend
    trend = ta.detect_trend(lookback=50)
    print(f"\nCurrent Trend: {trend.value}")
    
    # Calculate indicators
    atr = ta.calculate_atr(period=14)
    print(f"Current ATR: ${atr.iloc[-1]:.2f}")

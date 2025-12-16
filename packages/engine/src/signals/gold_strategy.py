"""
Gold Trading Strategy - The Gold Trader's Edge
Implements 6 core gold (XAU/USD) trading rules based on proven patterns.

These rules are the result of years of studying and backtesting XAU/USD.
"""

import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass
from enum import Enum

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from analysis.technical import TechnicalAnalysis, TrendDirection, SwingPoint
from backtesting.engine import Signal, TradeDirection


class MarketStructure(Enum):
    """Market structure types."""
    CHOCH = "choch"  # Change of Character
    BOS = "bos"      # Break of Structure
    NONE = "none"


class MomentumStrength(Enum):
    """Momentum strength classification."""
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"


@dataclass
class RuleResult:
    """Result of evaluating a trading rule."""
    rule_name: str
    triggered: bool
    direction: Optional[TradeDirection] = None
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    confidence: float = 0.0
    notes: str = ""


@dataclass
class FibZone:
    """Represents a Fibonacci zone with price levels."""
    swing_low: float
    swing_high: float
    level_236: float
    level_382: float
    level_500: float
    level_618: float
    level_786: float
    direction: str  # 'up' or 'down'


class GoldStrategy:
    """
    Gold-specific trading strategy implementing 6 core hard facts.
    
    RULES:
    1. 61.8% Golden Retracement - Price always retraces here
    2. 78.6% Deep Discount - High probability entry in trend
    3. 23.6% Shallow Pullback - Strong trend continuation
    4. Multiple Buy/Sell Candles - Correction detection
    5. Break of ATH After Consolidation - Trend continuation entry
    6. 50% Rule in Strong Momentum - Mid-range equilibrium entry
    """
    
    DEFAULT_CONFIG = {
        # Fibonacci tolerances
        'fib_tolerance': 0.015,  # 1.5% tolerance around fib levels
        
        # Swing detection
        'swing_lookback': 5,
        'swing_min_strength': 2,
        
        # Trend detection
        'trend_lookback': 50,
        
        # Momentum thresholds
        'strong_momentum_threshold': 0.02,  # 2% move
        'atr_period': 14,
        
        # Consolidation detection
        'consolidation_min_candles': 5,
        'consolidation_max_range_atr': 1.5,  # Max range as ATR multiple
        
        # Risk management
        'default_rr_ratio': 2.0,
        'sl_buffer_atr': 0.3,  # Buffer below/above swing as ATR multiple
        
        # Confirmation candles
        'confirmation_candles': 2,
    }
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize the strategy with optional custom config."""
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        self.ta: Optional[TechnicalAnalysis] = None
        self.df: Optional[pd.DataFrame] = None
        
        # Enable/disable individual rules
        self.rules_enabled = {
            'rule_1_618_retracement': True,
            'rule_2_786_deep_discount': True,
            'rule_3_236_shallow_pullback': True,
            'rule_4_consolidation_break': True,
            'rule_5_ath_breakout_retest': True,
            'rule_6_50_momentum': True,
        }
    
    def set_rule_enabled(self, rule_name: str, enabled: bool):
        """Enable or disable a specific rule."""
        if rule_name in self.rules_enabled:
            self.rules_enabled[rule_name] = enabled
    
    def evaluate(self, df: pd.DataFrame, current_idx: int) -> Optional[Signal]:
        """
        Evaluate all rules and return a signal if any rule triggers.
        
        Args:
            df: OHLCV DataFrame
            current_idx: Current candle index
        
        Returns:
            Signal if any rule triggers, None otherwise
        """
        min_required = max(self.config['trend_lookback'], 60)
        if current_idx < min_required:
            return None
        
        self.df = df
        self.ta = TechnicalAnalysis(df.iloc[:current_idx + 1])
        
        # Evaluate each enabled rule
        results = []
        
        if self.rules_enabled.get('rule_1_618_retracement'):
            result = self._rule_1_618_retracement(df, current_idx)
            if result.triggered:
                results.append(result)
        
        if self.rules_enabled.get('rule_2_786_deep_discount'):
            result = self._rule_2_786_deep_discount(df, current_idx)
            if result.triggered:
                results.append(result)
        
        if self.rules_enabled.get('rule_3_236_shallow_pullback'):
            result = self._rule_3_236_shallow_pullback(df, current_idx)
            if result.triggered:
                results.append(result)
        
        if self.rules_enabled.get('rule_4_consolidation_break'):
            result = self._rule_4_consolidation_break(df, current_idx)
            if result.triggered:
                results.append(result)
        
        if self.rules_enabled.get('rule_5_ath_breakout_retest'):
            result = self._rule_5_ath_breakout_retest(df, current_idx)
            if result.triggered:
                results.append(result)
        
        if self.rules_enabled.get('rule_6_50_momentum'):
            result = self._rule_6_50_momentum(df, current_idx)
            if result.triggered:
                results.append(result)
        
        if not results:
            return None
        
        # Return highest confidence signal
        best = max(results, key=lambda x: x.confidence)
        
        return Signal(
            time=df.index[current_idx],
            direction=best.direction,
            entry_price=best.entry_price,
            stop_loss=best.stop_loss,
            take_profit=best.take_profit,
            signal_name=best.rule_name,
            confidence=best.confidence,
            notes=best.notes
        )
    
    # ==================== HELPER METHODS ====================
    
    def _get_fib_zones(self, df: pd.DataFrame, idx: int) -> Optional[FibZone]:
        """Calculate Fibonacci zones from recent swing points."""
        swings = self.ta.detect_swing_points(
            lookback=self.config['swing_lookback'],
            min_strength=self.config['swing_min_strength']
        )
        
        if len(swings) < 2:
            return None
        
        # Get most recent swing high and low
        highs = [s for s in swings if s.is_high]
        lows = [s for s in swings if not s.is_high]
        
        if not highs or not lows:
            return None
        
        recent_high = highs[-1]
        recent_low = lows[-1]
        
        # Determine direction based on which came last
        if recent_high.index > recent_low.index:
            # Upswing - measure from low to high
            direction = 'up'
            swing_low = recent_low.price
            swing_high = recent_high.price
        else:
            # Downswing - measure from high to low
            direction = 'down'
            swing_low = recent_low.price
            swing_high = recent_high.price
        
        price_range = swing_high - swing_low
        
        return FibZone(
            swing_low=swing_low,
            swing_high=swing_high,
            level_236=swing_high - (price_range * 0.236),
            level_382=swing_high - (price_range * 0.382),
            level_500=swing_high - (price_range * 0.500),
            level_618=swing_high - (price_range * 0.618),
            level_786=swing_high - (price_range * 0.786),
            direction=direction
        )
    
    def _is_near_level(self, price: float, level: float) -> bool:
        """Check if price is near a specific level."""
        tolerance = level * self.config['fib_tolerance']
        return abs(price - level) <= tolerance
    
    def _detect_market_structure(self, df: pd.DataFrame, idx: int, lookback: int = 10) -> MarketStructure:
        """
        Detect Change of Character (CHoCH) or Break of Structure (BOS).
        
        CHoCH: First break against the trend (potential reversal)
        BOS: Break in direction of trend (continuation)
        """
        if idx < lookback + 5:
            return MarketStructure.NONE
        
        recent = df.iloc[idx - lookback:idx + 1]
        
        # Find recent swing points in this window
        highs = []
        lows = []
        
        for i in range(2, len(recent) - 2):
            if recent['high'].iloc[i] > recent['high'].iloc[i-1] and \
               recent['high'].iloc[i] > recent['high'].iloc[i+1]:
                highs.append((i, recent['high'].iloc[i]))
            if recent['low'].iloc[i] < recent['low'].iloc[i-1] and \
               recent['low'].iloc[i] < recent['low'].iloc[i+1]:
                lows.append((i, recent['low'].iloc[i]))
        
        if len(highs) < 2 or len(lows) < 2:
            return MarketStructure.NONE
        
        current_close = recent['close'].iloc[-1]
        
        # Check for BOS (break of most recent swing)
        last_high = highs[-1][1]
        last_low = lows[-1][1]
        
        if current_close > last_high:
            return MarketStructure.BOS
        if current_close < last_low:
            return MarketStructure.BOS
        
        # Check for CHoCH (break against prevailing structure)
        if len(highs) >= 2 and len(lows) >= 2:
            prev_high = highs[-2][1]
            prev_low = lows[-2][1]
            
            # Downtrend structure broken to upside
            if last_high < prev_high and current_close > last_high:
                return MarketStructure.CHOCH
            # Uptrend structure broken to downside
            if last_low > prev_low and current_close < last_low:
                return MarketStructure.CHOCH
        
        return MarketStructure.NONE
    
    def _detect_reversal_pattern(self, df: pd.DataFrame, idx: int) -> Optional[str]:
        """Detect reversal candlestick patterns."""
        if idx < 2:
            return None
        
        current = df.iloc[idx]
        prev = df.iloc[idx - 1]
        
        body = abs(current['close'] - current['open'])
        upper_wick = current['high'] - max(current['close'], current['open'])
        lower_wick = min(current['close'], current['open']) - current['low']
        candle_range = current['high'] - current['low']
        
        if candle_range == 0:
            return None
        
        # Bullish Engulfing
        if (current['close'] > current['open'] and  # Current is bullish
            prev['close'] < prev['open'] and        # Previous is bearish
            current['open'] < prev['close'] and     # Opens below prev close
            current['close'] > prev['open']):       # Closes above prev open
            return "bullish_engulfing"
        
        # Bearish Engulfing
        if (current['close'] < current['open'] and  # Current is bearish
            prev['close'] > prev['open'] and        # Previous is bullish
            current['open'] > prev['close'] and     # Opens above prev close
            current['close'] < prev['open']):       # Closes below prev open
            return "bearish_engulfing"
        
        # Bullish Pin Bar (Hammer)
        if (lower_wick > body * 2 and              # Long lower wick
            upper_wick < body * 0.5 and            # Short upper wick
            lower_wick > candle_range * 0.6):      # Lower wick is dominant
            return "bullish_pinbar"
        
        # Bearish Pin Bar (Shooting Star)
        if (upper_wick > body * 2 and              # Long upper wick
            lower_wick < body * 0.5 and            # Short lower wick
            upper_wick > candle_range * 0.6):      # Upper wick is dominant
            return "bearish_pinbar"
        
        return None
    
    def _get_momentum_strength(self, df: pd.DataFrame, idx: int, lookback: int = 10) -> MomentumStrength:
        """Classify momentum strength based on recent price action."""
        if idx < lookback:
            return MomentumStrength.WEAK
        
        recent = df.iloc[idx - lookback:idx + 1]
        price_change = (recent['close'].iloc[-1] - recent['close'].iloc[0]) / recent['close'].iloc[0]
        
        atr = self.ta.calculate_atr(period=self.config['atr_period']).iloc[-1]
        avg_price = recent['close'].mean()
        atr_pct = atr / avg_price
        
        if abs(price_change) > self.config['strong_momentum_threshold']:
            return MomentumStrength.STRONG
        elif abs(price_change) > atr_pct * 2:
            return MomentumStrength.MODERATE
        else:
            return MomentumStrength.WEAK
    
    def _detect_consolidation(self, df: pd.DataFrame, idx: int) -> Optional[Dict]:
        """Detect if price is in a consolidation range."""
        min_candles = self.config['consolidation_min_candles']
        
        if idx < min_candles + 5:
            return None
        
        atr = self.ta.calculate_atr(period=self.config['atr_period']).iloc[-1]
        max_range = atr * self.config['consolidation_max_range_atr']
        
        # Check last N candles for consolidation
        for lookback in range(min_candles, min(20, idx)):
            window = df.iloc[idx - lookback:idx + 1]
            range_high = window['high'].max()
            range_low = window['low'].min()
            range_size = range_high - range_low
            
            if range_size <= max_range:
                # Count mixed candles (alternating directions)
                bullish = sum(window['close'] > window['open'])
                bearish = len(window) - bullish
                
                if bullish >= 2 and bearish >= 2:  # Mixed signals = consolidation
                    return {
                        'range_high': range_high,
                        'range_low': range_low,
                        'range_size': range_size,
                        'candles': lookback,
                        'midpoint': (range_high + range_low) / 2
                    }
        
        return None
    
    def _find_ath(self, df: pd.DataFrame, idx: int, lookback: int = 100) -> float:
        """Find All-Time High within lookback period."""
        start_idx = max(0, idx - lookback)
        return df.iloc[start_idx:idx + 1]['high'].max()
    
    def _find_atl(self, df: pd.DataFrame, idx: int, lookback: int = 100) -> float:
        """Find All-Time Low within lookback period."""
        start_idx = max(0, idx - lookback)
        return df.iloc[start_idx:idx + 1]['low'].min()
    
    # ==================== TRADING RULES ====================
    
    def _rule_1_618_retracement(self, df: pd.DataFrame, idx: int) -> RuleResult:
        """
        RULE 1: 61.8% Golden Retracement
        
        "Price will always retrace to this level no matter what."
        
        Entry Logic:
        - Price retraces to 61.8% Fib level
        - Wait for CHoCH/BOS confirmation OR reversal pattern
        - Enter in direction of original trend
        """
        result = RuleResult(rule_name="Rule1_618_Golden", triggered=False)
        
        fib = self._get_fib_zones(df, idx)
        if fib is None:
            return result
        
        current = df.iloc[idx]
        atr = self.ta.calculate_atr(period=self.config['atr_period']).iloc[-1]
        
        # Check if price is at 61.8% level
        if not self._is_near_level(current['low'], fib.level_618) and \
           not self._is_near_level(current['high'], fib.level_618):
            return result
        
        # Look for confirmation
        structure = self._detect_market_structure(df, idx)
        pattern = self._detect_reversal_pattern(df, idx)
        
        has_confirmation = (
            structure in [MarketStructure.CHOCH, MarketStructure.BOS] or
            pattern is not None
        )
        
        if not has_confirmation:
            return result
        
        # Determine direction based on fib swing direction
        if fib.direction == 'up':
            # Upswing retracement - look for bullish entry
            if pattern and 'bearish' in pattern:
                return result  # Wrong pattern
            
            direction = TradeDirection.LONG
            entry_price = current['close']
            stop_loss = fib.swing_low - (atr * self.config['sl_buffer_atr'])
            risk = entry_price - stop_loss
            take_profit = entry_price + (risk * self.config['default_rr_ratio'])
            
        else:
            # Downswing retracement - look for bearish entry
            if pattern and 'bullish' in pattern:
                return result  # Wrong pattern
            
            direction = TradeDirection.SHORT
            entry_price = current['close']
            stop_loss = fib.swing_high + (atr * self.config['sl_buffer_atr'])
            risk = stop_loss - entry_price
            take_profit = entry_price - (risk * self.config['default_rr_ratio'])
        
        # Calculate confidence
        confidence = 0.5
        if structure == MarketStructure.CHOCH:
            confidence += 0.2
        if pattern:
            confidence += 0.2
        
        rsi = self.ta.calculate_rsi(period=14).iloc[-1]
        if direction == TradeDirection.LONG and rsi < 40:
            confidence += 0.1
        elif direction == TradeDirection.SHORT and rsi > 60:
            confidence += 0.1
        
        result.triggered = True
        result.direction = direction
        result.entry_price = entry_price
        result.stop_loss = stop_loss
        result.take_profit = take_profit
        result.confidence = min(confidence, 1.0)
        result.notes = f"61.8% retracement, structure: {structure.value}, pattern: {pattern}"
        
        return result
    
    def _rule_2_786_deep_discount(self, df: pd.DataFrame, idx: int) -> RuleResult:
        """
        RULE 2: 78.6% Deep Discount Entry
        
        "If bias is bullish and price retraces to 78.6%, a big move is likely coming."
        
        Entry Logic:
        - Identify bullish/bearish bias
        - Wait for price to reach 78.6% level
        - Look for liquidity sweep (price takes out previous low before bouncing)
        - Enter on confirmation
        """
        result = RuleResult(rule_name="Rule2_786_DeepDiscount", triggered=False)
        
        fib = self._get_fib_zones(df, idx)
        if fib is None:
            return result
        
        current = df.iloc[idx]
        prev = df.iloc[idx - 1] if idx > 0 else None
        atr = self.ta.calculate_atr(period=self.config['atr_period']).iloc[-1]
        
        # Check if price touched 78.6% level
        touches_786 = (
            self._is_near_level(current['low'], fib.level_786) or
            self._is_near_level(current['high'], fib.level_786) or
            (current['low'] <= fib.level_786 <= current['high'])
        )
        
        if not touches_786:
            return result
        
        # Determine bias from overall trend
        trend = self.ta.detect_trend(lookback=self.config['trend_lookback'])
        
        # Look for liquidity sweep (wick below/above previous swing)
        liquidity_sweep = False
        if prev is not None:
            if trend == TrendDirection.UPTREND and fib.direction == 'up':
                # Bullish setup - look for sweep below swing low
                if current['low'] < fib.swing_low and current['close'] > fib.level_786:
                    liquidity_sweep = True
            elif trend == TrendDirection.DOWNTREND and fib.direction == 'down':
                # Bearish setup - look for sweep above swing high
                if current['high'] > fib.swing_high and current['close'] < fib.level_786:
                    liquidity_sweep = True
        
        # Require either liquidity sweep or reversal pattern
        pattern = self._detect_reversal_pattern(df, idx)
        
        if not liquidity_sweep and not pattern:
            return result
        
        # Setup the trade
        if trend == TrendDirection.UPTREND and fib.direction == 'up':
            direction = TradeDirection.LONG
            entry_price = current['close']
            stop_loss = min(current['low'], fib.swing_low) - (atr * self.config['sl_buffer_atr'])
            risk = entry_price - stop_loss
            take_profit = entry_price + (risk * self.config['default_rr_ratio'])
            
        elif trend == TrendDirection.DOWNTREND and fib.direction == 'down':
            direction = TradeDirection.SHORT
            entry_price = current['close']
            stop_loss = max(current['high'], fib.swing_high) + (atr * self.config['sl_buffer_atr'])
            risk = stop_loss - entry_price
            take_profit = entry_price - (risk * self.config['default_rr_ratio'])
        else:
            return result
        
        # Calculate confidence
        confidence = 0.6  # Base - deep discount is high probability
        if liquidity_sweep:
            confidence += 0.2
        if pattern:
            confidence += 0.15
        
        result.triggered = True
        result.direction = direction
        result.entry_price = entry_price
        result.stop_loss = stop_loss
        result.take_profit = take_profit
        result.confidence = min(confidence, 1.0)
        result.notes = f"78.6% deep discount, sweep: {liquidity_sweep}, pattern: {pattern}"
        
        return result
    
    def _rule_3_236_shallow_pullback(self, df: pd.DataFrame, idx: int) -> RuleResult:
        """
        RULE 3: 23.6% Shallow Pullback in Strong Trend
        
        "In strong bullish moves, price may only pullback to 23.6% before continuing."
        
        Entry Logic:
        - Detect strong momentum (big recent move)
        - Price pulls back to only 23.6%
        - Look for small consolidation then BOS
        - Enter on breakout with trailing stop mindset
        """
        result = RuleResult(rule_name="Rule3_236_Shallow", triggered=False)
        
        # Require strong momentum
        momentum = self._get_momentum_strength(df, idx, lookback=15)
        if momentum != MomentumStrength.STRONG:
            return result
        
        fib = self._get_fib_zones(df, idx)
        if fib is None:
            return result
        
        current = df.iloc[idx]
        atr = self.ta.calculate_atr(period=self.config['atr_period']).iloc[-1]
        
        # Check if price is at 23.6% level (shallow pullback)
        at_236 = self._is_near_level(current['close'], fib.level_236)
        
        # Also accept if price is between swing high and 23.6% (hasn't pulled back much)
        in_shallow_zone = fib.level_236 <= current['close'] <= fib.swing_high
        
        if not at_236 and not in_shallow_zone:
            return result
        
        # Look for BOS (continuation signal)
        structure = self._detect_market_structure(df, idx)
        
        # Determine trend direction
        trend = self.ta.detect_trend(lookback=20)
        
        if trend == TrendDirection.UPTREND and fib.direction == 'up':
            # Bullish continuation
            if structure != MarketStructure.BOS:
                # Alternative: look for bullish candle close above recent high
                lookback_highs = df.iloc[idx-5:idx]['high'].max()
                if current['close'] <= lookback_highs:
                    return result
            
            direction = TradeDirection.LONG
            entry_price = current['close']
            stop_loss = fib.level_382 - (atr * self.config['sl_buffer_atr'])  # Below 38.2%
            risk = entry_price - stop_loss
            take_profit = entry_price + (risk * 2.5)  # Higher R:R for momentum trades
            
        elif trend == TrendDirection.DOWNTREND and fib.direction == 'down':
            # Bearish continuation
            if structure != MarketStructure.BOS:
                lookback_lows = df.iloc[idx-5:idx]['low'].min()
                if current['close'] >= lookback_lows:
                    return result
            
            direction = TradeDirection.SHORT
            entry_price = current['close']
            stop_loss = fib.level_382 + (atr * self.config['sl_buffer_atr'])
            risk = stop_loss - entry_price
            take_profit = entry_price - (risk * 2.5)
        else:
            return result
        
        confidence = 0.65  # Strong momentum setups are reliable
        if structure == MarketStructure.BOS:
            confidence += 0.15
        
        result.triggered = True
        result.direction = direction
        result.entry_price = entry_price
        result.stop_loss = stop_loss
        result.take_profit = take_profit
        result.confidence = min(confidence, 1.0)
        result.notes = f"23.6% shallow pullback in {momentum.value} momentum"
        
        return result
    
    def _rule_4_consolidation_break(self, df: pd.DataFrame, idx: int) -> RuleResult:
        """
        RULE 4: Multiple Buy/Sell Candles = Correction → Wait for Break
        
        "When you see choppy candles in both directions, that's likely a correction."
        
        Entry Logic:
        - Identify sideways/choppy price action
        - Mark the range
        - Wait for break of range
        - Enter on breakout with confirmation
        """
        result = RuleResult(rule_name="Rule4_ConsolidationBreak", triggered=False)
        
        # Check for consolidation in recent history
        consolidation = self._detect_consolidation(df, idx - 1)  # Check previous candles
        
        if consolidation is None:
            return result
        
        current = df.iloc[idx]
        atr = self.ta.calculate_atr(period=self.config['atr_period']).iloc[-1]
        
        range_high = consolidation['range_high']
        range_low = consolidation['range_low']
        
        # Check for breakout
        breakout_up = current['close'] > range_high
        breakout_down = current['close'] < range_low
        
        if not breakout_up and not breakout_down:
            return result
        
        # Determine overall bias
        trend = self.ta.detect_trend(lookback=self.config['trend_lookback'])
        
        if breakout_up:
            # Only take bullish breakout if trend supports it
            if trend == TrendDirection.DOWNTREND:
                confidence_penalty = 0.2
            else:
                confidence_penalty = 0
            
            direction = TradeDirection.LONG
            entry_price = current['close']
            stop_loss = range_low - (atr * self.config['sl_buffer_atr'])
            risk = entry_price - stop_loss
            take_profit = entry_price + (risk * self.config['default_rr_ratio'])
            
        else:  # breakout_down
            if trend == TrendDirection.UPTREND:
                confidence_penalty = 0.2
            else:
                confidence_penalty = 0
            
            direction = TradeDirection.SHORT
            entry_price = current['close']
            stop_loss = range_high + (atr * self.config['sl_buffer_atr'])
            risk = stop_loss - entry_price
            take_profit = entry_price - (risk * self.config['default_rr_ratio'])
        
        # Confidence based on consolidation quality
        confidence = 0.55 - confidence_penalty
        
        # Longer consolidation = stronger breakout
        if consolidation['candles'] >= 10:
            confidence += 0.15
        elif consolidation['candles'] >= 7:
            confidence += 0.1
        
        result.triggered = True
        result.direction = direction
        result.entry_price = entry_price
        result.stop_loss = stop_loss
        result.take_profit = take_profit
        result.confidence = min(max(confidence, 0.3), 1.0)
        result.notes = f"Consolidation break after {consolidation['candles']} candles"
        
        return result
    
    def _rule_5_ath_breakout_retest(self, df: pd.DataFrame, idx: int) -> RuleResult:
        """
        RULE 5: Break of ATH After Consolidation = Entry
        
        "Safe to join trend after clean ATH break following retracement + consolidation."
        
        Entry Logic:
        - Price breaks ATH
        - Look for pullback to ATH level
        - Consolidation near ATH
        - Enter on retest confirmation
        """
        result = RuleResult(rule_name="Rule5_ATH_Retest", triggered=False)
        
        lookback = 100
        if idx < lookback:
            return result
        
        current = df.iloc[idx]
        atr = self.ta.calculate_atr(period=self.config['atr_period']).iloc[-1]
        
        # Find ATH from before recent action
        older_ath = df.iloc[max(0, idx-lookback):idx-20]['high'].max()
        recent_high = df.iloc[idx-20:idx]['high'].max()
        
        # Check if we broke ATH recently
        broke_ath = recent_high > older_ath
        
        if not broke_ath:
            # Also check for ATL break (bearish version)
            older_atl = df.iloc[max(0, idx-lookback):idx-20]['low'].min()
            recent_low = df.iloc[idx-20:idx]['low'].min()
            
            if recent_low < older_atl:
                # Bearish ATL break setup
                key_level = older_atl
                direction = TradeDirection.SHORT
            else:
                return result
        else:
            key_level = older_ath
            direction = TradeDirection.LONG
        
        # Check if price is retesting the key level
        tolerance = atr * 0.5
        
        if direction == TradeDirection.LONG:
            # Price should be near the old ATH (now support)
            retesting = abs(current['low'] - key_level) <= tolerance or \
                       (current['low'] <= key_level <= current['high'])
            
            if not retesting:
                return result
            
            # Look for bounce confirmation
            if current['close'] < key_level:
                return result  # Failed retest
            
            entry_price = current['close']
            stop_loss = key_level - (atr * self.config['sl_buffer_atr'])
            risk = entry_price - stop_loss
            take_profit = entry_price + (risk * self.config['default_rr_ratio'])
            
        else:  # SHORT
            retesting = abs(current['high'] - key_level) <= tolerance or \
                       (current['low'] <= key_level <= current['high'])
            
            if not retesting:
                return result
            
            if current['close'] > key_level:
                return result  # Failed retest
            
            entry_price = current['close']
            stop_loss = key_level + (atr * self.config['sl_buffer_atr'])
            risk = stop_loss - entry_price
            take_profit = entry_price - (risk * self.config['default_rr_ratio'])
        
        # Check for consolidation near the level
        consolidation = self._detect_consolidation(df, idx)
        
        confidence = 0.6
        if consolidation:
            confidence += 0.2
        
        # Reversal pattern adds confidence
        pattern = self._detect_reversal_pattern(df, idx)
        if pattern:
            confidence += 0.1
        
        result.triggered = True
        result.direction = direction
        result.entry_price = entry_price
        result.stop_loss = stop_loss
        result.take_profit = take_profit
        result.confidence = min(confidence, 1.0)
        result.notes = f"ATH/ATL retest at {key_level:.2f}, consolidation: {consolidation is not None}"
        
        return result
    
    def _rule_6_50_momentum(self, df: pd.DataFrame, idx: int) -> RuleResult:
        """
        RULE 6: 50% Rule in Strong Momentum
        
        "In high momentum, price will only pull back to 50% before moving on."
        
        Entry Logic:
        - Detect high momentum environment
        - Price pulls back to 50% equilibrium
        - Look for imbalance zone or order block
        - Enter with tight stop
        """
        result = RuleResult(rule_name="Rule6_50_Momentum", triggered=False)
        
        # Require at least moderate momentum
        momentum = self._get_momentum_strength(df, idx, lookback=10)
        if momentum == MomentumStrength.WEAK:
            return result
        
        fib = self._get_fib_zones(df, idx)
        if fib is None:
            return result
        
        current = df.iloc[idx]
        atr = self.ta.calculate_atr(period=self.config['atr_period']).iloc[-1]
        
        # Check if price is at 50% level
        at_50 = self._is_near_level(current['close'], fib.level_500) or \
                self._is_near_level(current['low'], fib.level_500) or \
                self._is_near_level(current['high'], fib.level_500)
        
        if not at_50:
            return result
        
        # Determine direction based on swing
        trend = self.ta.detect_trend(lookback=30)
        
        if fib.direction == 'up' and trend == TrendDirection.UPTREND:
            # Bullish setup - entered equilibrium zone
            direction = TradeDirection.LONG
            entry_price = current['close']
            # Tight stop below 61.8%
            stop_loss = fib.level_618 - (atr * 0.3)
            risk = entry_price - stop_loss
            take_profit = entry_price + (risk * self.config['default_rr_ratio'])
            
        elif fib.direction == 'down' and trend == TrendDirection.DOWNTREND:
            # Bearish setup
            direction = TradeDirection.SHORT
            entry_price = current['close']
            stop_loss = fib.level_618 + (atr * 0.3)
            risk = stop_loss - entry_price
            take_profit = entry_price - (risk * self.config['default_rr_ratio'])
        else:
            return result
        
        # Look for additional confirmation
        pattern = self._detect_reversal_pattern(df, idx)
        structure = self._detect_market_structure(df, idx)
        
        confidence = 0.5
        if momentum == MomentumStrength.STRONG:
            confidence += 0.2
        if pattern:
            confidence += 0.1
        if structure == MarketStructure.BOS:
            confidence += 0.1
        
        result.triggered = True
        result.direction = direction
        result.entry_price = entry_price
        result.stop_loss = stop_loss
        result.take_profit = take_profit
        result.confidence = min(confidence, 1.0)
        result.notes = f"50% equilibrium in {momentum.value} momentum"
        
        return result


def create_strategy_function(strategy: GoldStrategy):
    """Create a strategy function compatible with BacktestEngine."""
    def strategy_func(df: pd.DataFrame, idx: int) -> Optional[Signal]:
        return strategy.evaluate(df, idx)
    return strategy_func


# ==================== TESTING ====================

if __name__ == "__main__":
    from data.loader import generate_sample_data
    from backtesting.engine import BacktestEngine
    
    print("=" * 60)
    print("GOLD STRATEGY - BACKTEST")
    print("=" * 60)
    
    # Generate sample data
    print("\n📊 Generating sample gold data...")
    df = generate_sample_data(
        start_date="2022-01-01",
        end_date="2024-12-01",
        timeframe="4h"
    )
    
    # Initialize strategy
    print("\n🎯 Initializing Gold Strategy with 6 rules...")
    strategy = GoldStrategy()
    
    # Show enabled rules
    print("\nEnabled Rules:")
    for rule, enabled in strategy.rules_enabled.items():
        status = "✅" if enabled else "❌"
        print(f"  {status} {rule}")
    
    # Run backtest
    print("\n🚀 Running backtest...")
    engine = BacktestEngine(
        initial_balance=10000,
        position_size_pct=2.0,
        commission=2.0,  # $2 per trade
        slippage=0.5
    )
    
    result = engine.run(
        df=df,
        strategy_func=create_strategy_function(strategy),
        max_open_trades=1
    )
    
    print(result.summary())
    
    # Show trades by rule
    if result.trades:
        print("\n📋 Trades by Rule:")
        rule_stats = {}
        for trade in result.trades:
            rule = trade.signal_name
            if rule not in rule_stats:
                rule_stats[rule] = {'count': 0, 'wins': 0, 'pnl': 0}
            rule_stats[rule]['count'] += 1
            rule_stats[rule]['pnl'] += trade.pnl
            if trade.pnl > 0:
                rule_stats[rule]['wins'] += 1
        
        for rule, stats in sorted(rule_stats.items()):
            win_rate = (stats['wins'] / stats['count'] * 100) if stats['count'] > 0 else 0
            print(f"  {rule}:")
            print(f"    Trades: {stats['count']}, Win Rate: {win_rate:.1f}%, P&L: ${stats['pnl']:.2f}")

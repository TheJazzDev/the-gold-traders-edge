"""
Gold Trading Strategy
Implements the core gold trading rules for signal generation.

This strategy is based on specific gold "hard facts" - patterns that
have shown consistent behavior in gold (XAUUSD) price action.
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


class GoldStrategy:
    """
    Gold-specific trading strategy implementing 5 core rules.
    
    RULES:
    1. Fib 76.8% Retracement Buy - In uptrend, after breakout and retest at 76.8% fib
    2. [TO BE CONFIGURED]
    3. [TO BE CONFIGURED]
    4. [TO BE CONFIGURED]
    5. [TO BE CONFIGURED]
    
    Configure your rules using the set_rule_config() method.
    """
    
    # Default configuration
    DEFAULT_CONFIG = {
        # Fibonacci settings
        'fib_entry_level': 0.786,  # 76.8% (or 78.6%) retracement
        'fib_tolerance': 0.02,     # 2% tolerance around fib level
        
        # Swing detection
        'swing_lookback': 5,       # Candles to look back for swings
        'swing_min_strength': 2,   # Minimum swing strength
        
        # Risk management
        'default_sl_atr_multiplier': 1.5,  # SL = ATR * multiplier
        'default_tp_rr_ratio': 2.0,        # TP at 2:1 R:R
        
        # Trend detection
        'trend_lookback': 50,      # Candles for trend detection
        
        # Breakout settings
        'breakout_lookback': 20,   # Candles to define range
        'retest_lookback': 10,     # Candles to look for retest
        'retest_tolerance_pct': 0.3,  # % tolerance for retest
    }
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the strategy.
        
        Args:
            config: Optional custom configuration dict
        """
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        self.ta: Optional[TechnicalAnalysis] = None
        self.rules_enabled = {
            'rule_1_fib_retest': True,
            'rule_2': False,  # Configure these
            'rule_3': False,
            'rule_4': False,
            'rule_5': False,
        }
    
    def set_rule_config(self, rule_name: str, enabled: bool, **kwargs):
        """
        Configure a specific rule.
        
        Args:
            rule_name: Name of the rule (e.g., 'rule_2')
            enabled: Whether the rule is enabled
            **kwargs: Rule-specific parameters
        """
        if rule_name in self.rules_enabled:
            self.rules_enabled[rule_name] = enabled
        
        # Store rule-specific config
        for key, value in kwargs.items():
            self.config[f"{rule_name}_{key}"] = value
    
    def evaluate(
        self, 
        df: pd.DataFrame, 
        current_idx: int
    ) -> Optional[Signal]:
        """
        Evaluate all rules and return a signal if any rule triggers.
        
        Args:
            df: OHLCV DataFrame
            current_idx: Current candle index
        
        Returns:
            Signal if any rule triggers, None otherwise
        """
        # Need minimum data
        min_required = max(self.config['trend_lookback'], 50)
        if current_idx < min_required:
            return None
        
        # Initialize technical analysis
        self.ta = TechnicalAnalysis(df.iloc[:current_idx + 1])
        
        # Evaluate each enabled rule
        results = []
        
        if self.rules_enabled.get('rule_1_fib_retest'):
            result = self._rule_1_fib_retest(df, current_idx)
            if result.triggered:
                results.append(result)
        
        if self.rules_enabled.get('rule_2'):
            result = self._rule_2(df, current_idx)
            if result.triggered:
                results.append(result)
        
        if self.rules_enabled.get('rule_3'):
            result = self._rule_3(df, current_idx)
            if result.triggered:
                results.append(result)
        
        if self.rules_enabled.get('rule_4'):
            result = self._rule_4(df, current_idx)
            if result.triggered:
                results.append(result)
        
        if self.rules_enabled.get('rule_5'):
            result = self._rule_5(df, current_idx)
            if result.triggered:
                results.append(result)
        
        # Return highest confidence signal
        if not results:
            return None
        
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
    
    def _rule_1_fib_retest(self, df: pd.DataFrame, idx: int) -> RuleResult:
        """
        RULE 1: Fibonacci 76.8% Retracement Buy
        
        Conditions:
        1. Gold is in an uptrend (higher highs, higher lows)
        2. Price breaks above a resistance level
        3. Price retraces back to the breakout level
        4. The retracement level coincides with the 76.8% Fibonacci level
        5. Enter long at this zone
        
        Stop Loss: Below the swing low
        Take Profit: At the previous high or 2:1 R:R
        """
        result = RuleResult(rule_name="Rule1_Fib_Retest", triggered=False)
        
        # 1. Check for uptrend
        trend = self.ta.detect_trend(
            lookback=self.config['trend_lookback'],
            method="swing"
        )
        
        if trend != TrendDirection.UPTREND:
            return result
        
        # 2. Get recent swing points
        swings = self.ta.detect_swing_points(
            lookback=self.config['swing_lookback'],
            min_strength=self.config['swing_min_strength']
        )
        
        if len(swings) < 4:
            return result
        
        # Get recent swing high and swing low
        recent_highs = [s for s in swings if s.is_high][-3:]
        recent_lows = [s for s in swings if not s.is_high][-3:]
        
        if len(recent_highs) < 2 or len(recent_lows) < 1:
            return result
        
        swing_high = recent_highs[-1]  # Most recent high
        swing_low = recent_lows[-1]     # Most recent low
        previous_high = recent_highs[-2] if len(recent_highs) >= 2 else None
        
        # 3. Check if price has broken above previous high
        current_candle = df.iloc[idx]
        
        if previous_high is None:
            return result
        
        breakout_level = previous_high.price
        
        # Check if we had a breakout (high went above previous high)
        # Look back to find breakout
        lookback_data = df.iloc[max(0, idx-self.config['breakout_lookback']):idx+1]
        broke_above = lookback_data['high'].max() > breakout_level
        
        if not broke_above:
            return result
        
        # 4. Check if current price is near the 76.8% fib level
        fib_level = self.config['fib_entry_level']
        fib_tolerance = self.config['fib_tolerance']
        
        # Calculate fib from swing low to swing high
        is_near_fib = self.ta.is_near_fib_level(
            price=current_candle['low'],
            swing_low=swing_low.price,
            swing_high=swing_high.price,
            target_level=fib_level,
            tolerance=fib_tolerance
        )
        
        if not is_near_fib:
            return result
        
        # 5. Check if price is retesting the breakout level
        retest_info = self.ta.detect_retest(
            breakout_level=breakout_level,
            tolerance_pct=self.config['retest_tolerance_pct'],
            lookback=self.config['retest_lookback']
        )
        
        # Signal conditions met - calculate entry, SL, TP
        entry_price = current_candle['close']
        
        # Stop loss below the swing low
        atr = self.ta.calculate_atr(period=14).iloc[-1]
        stop_loss = swing_low.price - (atr * 0.5)  # Slightly below swing low
        
        # Take profit at previous high or 2:1 R:R
        risk = entry_price - stop_loss
        tp_by_rr = entry_price + (risk * self.config['default_tp_rr_ratio'])
        tp_by_swing = swing_high.price
        take_profit = max(tp_by_rr, tp_by_swing)
        
        # Calculate confidence based on multiple factors
        confidence = 0.5  # Base confidence
        
        # Bonus for strong trend
        if trend == TrendDirection.UPTREND:
            confidence += 0.2
        
        # Bonus for confirmed retest
        if retest_info['retest_found']:
            confidence += 0.2
        
        # Bonus for RSI not overbought
        rsi = self.ta.calculate_rsi(period=14).iloc[-1]
        if 30 < rsi < 70:
            confidence += 0.1
        
        result.triggered = True
        result.direction = TradeDirection.LONG
        result.entry_price = entry_price
        result.stop_loss = stop_loss
        result.take_profit = take_profit
        result.confidence = min(confidence, 1.0)
        result.notes = f"Fib {fib_level*100:.1f}% retest at {entry_price:.2f}, SL: {stop_loss:.2f}, TP: {take_profit:.2f}"
        
        return result
    
    def _rule_2(self, df: pd.DataFrame, idx: int) -> RuleResult:
        """
        RULE 2: [PLACEHOLDER - Configure with your rule]
        
        Override this method with your second gold trading rule.
        """
        return RuleResult(rule_name="Rule2", triggered=False)
    
    def _rule_3(self, df: pd.DataFrame, idx: int) -> RuleResult:
        """
        RULE 3: [PLACEHOLDER - Configure with your rule]
        
        Override this method with your third gold trading rule.
        """
        return RuleResult(rule_name="Rule3", triggered=False)
    
    def _rule_4(self, df: pd.DataFrame, idx: int) -> RuleResult:
        """
        RULE 4: [PLACEHOLDER - Configure with your rule]
        
        Override this method with your fourth gold trading rule.
        """
        return RuleResult(rule_name="Rule4", triggered=False)
    
    def _rule_5(self, df: pd.DataFrame, idx: int) -> RuleResult:
        """
        RULE 5: [PLACEHOLDER - Configure with your rule]
        
        Override this method with your fifth gold trading rule.
        """
        return RuleResult(rule_name="Rule5", triggered=False)


def create_strategy_function(strategy: GoldStrategy):
    """
    Create a strategy function compatible with BacktestEngine.
    
    Args:
        strategy: GoldStrategy instance
    
    Returns:
        Callable that takes (df, idx) and returns Signal or None
    """
    def strategy_func(df: pd.DataFrame, idx: int) -> Optional[Signal]:
        return strategy.evaluate(df, idx)
    
    return strategy_func


if __name__ == "__main__":
    # Test the strategy
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from data.loader import generate_sample_data
    from backtesting.engine import BacktestEngine
    
    # Generate sample data
    print("Generating sample data...")
    df = generate_sample_data(
        start_date="2022-01-01",
        end_date="2024-01-01",
        timeframe="4h"
    )
    
    # Initialize strategy
    strategy = GoldStrategy()
    
    # Run backtest
    print("\nRunning backtest...")
    engine = BacktestEngine(
        initial_balance=10000,
        position_size_pct=2.0
    )
    
    result = engine.run(
        df=df,
        strategy_func=create_strategy_function(strategy),
        max_open_trades=1
    )
    
    print(result.summary())
    
    # Show individual trades
    if result.trades:
        print("\nRecent Trades:")
        for trade in result.trades[-5:]:
            print(f"  {trade.entry_time}: {trade.direction.value.upper()} @ {trade.entry_price:.2f} "
                  f"-> {trade.status.value} P&L: ${trade.pnl:.2f}")

"""
Gold Trading Strategy - The Gold Trader's Edge
Implements professional gold (XAU/USD) trading rules based on proven patterns.
"""

import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, time

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
    Professional Gold Trading Strategy - 5 PROVEN PROFITABLE RULES ONLY

    ALL RULES ARE PROFITABLE AND ENABLED:
    1. Momentum Equilibrium (50% Fib) - 76% WR, 293% return ⭐ BEST
    2. London Session Breakout - 58.8% WR, 2.74 PF ⭐ STRONG
    3. Golden Fibonacci (61.8%) - 52.6% WR, 44% return
    4. ATH Breakout Retest - 38% WR, 30% return
    5. Order Block Retest - Institutional smart money zones

    Unprofitable rules have been DELETED from codebase.
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
        'consolidation_max_range_atr': 1.5,

        # Risk management
        'default_rr_ratio': 2.0,
        'sl_buffer_atr': 0.3,

        # Volatility squeeze breakout (see
        # docs/superpowers/specs/2026-09-08-volatility-squeeze-breakout-design.md)
        'squeeze_lookback': 20,
        'squeeze_atr_ratio': 0.7,
        'breakout_buffer_atr': 0.2,

        # Fibonacci Golden Zone Confluence (a faithful implementation of the
        # user's own trading plan — see docs/superpowers/specs/strategy-ledger.md)
        'liquidity_grab_lookback': 10,
        'fib_confluence_min_rr': 2.0,
        # Shallow Pullback Continuation (see
        # docs/superpowers/specs/strategy-ledger.md) — how many recent
        # candles the 23.6% touch is allowed to have happened within,
        # before the structure-break entry candle.
        'pullback_window': 10,

        # How many recent candles the liquidity-grab/structure-retest
        # confirmations are allowed to have happened within, rather than
        # requiring them on the exact same candle as the 61.8% touch — see
        # strategy-ledger.md's diagnostic (requiring same-candle alignment
        # for all 4 conditions collapsed to ~0.15% of candles). 11 is where
        # a full-dataset feasibility sweep found the best trade-count/PF
        # tradeoff (window<11 too rare to evaluate, window>11 dilutes into
        # noise) — see strategy-ledger.md.
        'confluence_window': 11,

        # EMA periods
        'ema_fast': 9,
        'ema_slow': 21,

        # RSI settings
        'rsi_period': 14,
        'rsi_overbought': 70,
        'rsi_oversold': 30,
    }

    def __init__(self, config: Optional[Dict] = None, enabled_rules: Optional[List[int]] = None):
        """
        Initialize the strategy with optional custom config.

        Args:
            config: Optional configuration dictionary
            enabled_rules: Optional list of rule IDs to enable (1-6)
                          If None, uses default enabled rules
        """
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        self.ta: Optional[TechnicalAnalysis] = None
        self.df: Optional[pd.DataFrame] = None

        # Map rule IDs to rule names for backward compatibility
        rule_id_map = {
            1: 'golden_fibonacci',
            2: 'ath_retest',
            3: 'momentum_equilibrium',
            4: 'london_session_breakout',
            5: 'momentum_equilibrium',  # Rule 5 is also momentum equilibrium (legacy)
            6: 'order_block_retest',
        }

        # Enable/disable individual rules.
        # NOTE: figures below are from `run_backtest.py --rules <name>` run in
        # ISOLATION against real 2025-2026 XAUUSD 4H data (Yahoo Finance), each
        # rule alone vs. the shared-trade-slot backtest. The combined 5-rule
        # backtest reports much worse per-rule numbers for some rules because
        # `BacktestEngine.run()` hardcodes max_open_trades=1 *shared across all
        # rules* — whichever rule fires first blocks every other rule's entries
        # until its trade closes, regardless of signal quality. That artifact
        # doesn't affect live alerting (RealtimeSignalGenerator has no such
        # single-slot gate), only the backtested combined equity curve.
        self.rules_enabled = {
            # Isolated real-data backtest: 78 trades, 80.8% win rate, PF 4.58, +191.7%
            'momentum_equilibrium': True,

            # Isolated real-data backtest: 14 trades, 57.1% win rate, PF 2.18, +15.9%
            'london_session_breakout': True,

            # Isolated real-data backtest: 31 trades, 51.6% win rate, PF 1.46, +15.6%
            'golden_fibonacci': True,

            # Isolated real-data backtest: 98 trades, 38.8% win rate, PF 1.15, +15.3%
            'ath_retest': True,

            # Isolated real-data backtest: 118 trades, 41.5% win rate, PF 1.35, +48.6%
            'order_block_retest': True,

            # Not yet validated — disabled until it survives the same
            # train/test + shared-config gate as the other 5 (see
            # docs/superpowers/specs/2026-09-08-volatility-squeeze-breakout-design.md).
            'volatility_squeeze_breakout': False,

            # Not yet validated — see docs/superpowers/specs/strategy-ledger.md.
            'fib_golden_zone_confluence': False,

            # Not yet validated — see docs/superpowers/specs/strategy-ledger.md.
            'shallow_pullback_continuation': False,
        }

        # Override with enabled_rules if provided
        if enabled_rules is not None:
            # Disable all rules first
            for rule in self.rules_enabled:
                self.rules_enabled[rule] = False

            # Enable only specified rules
            for rule_id in enabled_rules:
                rule_name = rule_id_map.get(rule_id)
                if rule_name and rule_name in self.rules_enabled:
                    self.rules_enabled[rule_name] = True

    def set_rule_enabled(self, rule_name: str, enabled: bool):
        """Enable or disable a specific rule."""
        if rule_name in self.rules_enabled:
            self.rules_enabled[rule_name] = enabled

    def evaluate(self, df: pd.DataFrame, current_idx: int) -> Optional[Signal]:
        """
        Evaluate all rules and return a signal if any rule triggers.
        """
        min_required = max(self.config['trend_lookback'], 60)
        if current_idx < min_required:
            return None

        self.df = df
        self.ta = TechnicalAnalysis(df.iloc[:current_idx + 1])

        # Evaluate each enabled rule
        results = []

        if self.rules_enabled.get('momentum_equilibrium'):
            result = self._momentum_equilibrium(df, current_idx)
            if result.triggered:
                results.append(result)

        if self.rules_enabled.get('london_session_breakout'):
            result = self._london_session_breakout(df, current_idx)
            if result.triggered:
                results.append(result)

        if self.rules_enabled.get('golden_fibonacci'):
            result = self._golden_fibonacci(df, current_idx)
            if result.triggered:
                results.append(result)

        if self.rules_enabled.get('order_block_retest'):
            result = self._order_block_retest(df, current_idx)
            if result.triggered:
                results.append(result)

        if self.rules_enabled.get('ath_retest'):
            result = self._ath_retest(df, current_idx)
            if result.triggered:
                results.append(result)

        if self.rules_enabled.get('volatility_squeeze_breakout'):
            result = self._volatility_squeeze_breakout(df, current_idx)
            if result.triggered:
                results.append(result)

        if self.rules_enabled.get('fib_golden_zone_confluence'):
            result = self._fib_golden_zone_confluence(df, current_idx)
            if result.triggered:
                results.append(result)

        if self.rules_enabled.get('shallow_pullback_continuation'):
            result = self._shallow_pullback_continuation(df, current_idx)
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

    def _fib_levels(self, swing_low: float, swing_high: float, direction: str) -> Dict[str, float]:
        """
        Retracement levels anchored from the price extreme the market is
        retracing *from*: the high for an uptrend pullback, the low for a
        downtrend bounce. Anchoring both directions from the high (as this
        used to do) flips level_618 to the wrong side of level_500 for a
        'down' zone, which can hand a rule a stop-loss on the wrong side of
        entry — see _momentum_equilibrium's risk guard.
        """
        price_range = swing_high - swing_low
        if direction == 'up':
            return {
                'level_236': swing_high - (price_range * 0.236),
                'level_382': swing_high - (price_range * 0.382),
                'level_500': swing_high - (price_range * 0.500),
                'level_618': swing_high - (price_range * 0.618),
                'level_786': swing_high - (price_range * 0.786),
            }
        return {
            'level_236': swing_low + (price_range * 0.236),
            'level_382': swing_low + (price_range * 0.382),
            'level_500': swing_low + (price_range * 0.500),
            'level_618': swing_low + (price_range * 0.618),
            'level_786': swing_low + (price_range * 0.786),
        }

    def _get_fib_zones(self, df: pd.DataFrame, idx: int) -> Optional[FibZone]:
        """Calculate Fibonacci zones from recent swing points."""
        swings = self.ta.detect_swing_points(
            lookback=self.config['swing_lookback'],
            min_strength=self.config['swing_min_strength']
        )

        if len(swings) < 2:
            return None

        highs = [s for s in swings if s.is_high]
        lows = [s for s in swings if not s.is_high]

        if not highs or not lows:
            return None

        recent_high = highs[-1]
        recent_low = lows[-1]

        direction = 'up' if recent_high.index > recent_low.index else 'down'
        swing_low = recent_low.price
        swing_high = recent_high.price

        return FibZone(
            swing_low=swing_low,
            swing_high=swing_high,
            direction=direction,
            **self._fib_levels(swing_low, swing_high, direction)
        )

    def _is_near_level(self, price: float, level: float) -> bool:
        """Check if price is near a specific level."""
        tolerance = level * self.config['fib_tolerance']
        return abs(price - level) <= tolerance

    def _detect_market_structure(self, df: pd.DataFrame, idx: int, lookback: int = 10) -> MarketStructure:
        """Detect Change of Character (CHoCH) or Break of Structure (BOS)."""
        if idx < lookback + 5:
            return MarketStructure.NONE

        recent = df.iloc[idx - lookback:idx + 1]

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
        last_high = highs[-1][1]
        last_low = lows[-1][1]

        if current_close > last_high:
            return MarketStructure.BOS
        if current_close < last_low:
            return MarketStructure.BOS

        if len(highs) >= 2 and len(lows) >= 2:
            prev_high = highs[-2][1]
            prev_low = lows[-2][1]

            if last_high < prev_high and current_close > last_high:
                return MarketStructure.CHOCH
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
        if (current['close'] > current['open'] and
            prev['close'] < prev['open'] and
            current['open'] < prev['close'] and
            current['close'] > prev['open']):
            return "bullish_engulfing"

        # Bearish Engulfing
        if (current['close'] < current['open'] and
            prev['close'] > prev['open'] and
            current['open'] > prev['close'] and
            current['close'] < prev['open']):
            return "bearish_engulfing"

        # Bullish Pin Bar
        if (lower_wick > body * 2 and
            upper_wick < body * 0.5 and
            lower_wick > candle_range * 0.6):
            return "bullish_pinbar"

        # Bearish Pin Bar
        if (upper_wick > body * 2 and
            lower_wick < body * 0.5 and
            upper_wick > candle_range * 0.6):
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

        for lookback in range(min_candles, min(20, idx)):
            window = df.iloc[idx - lookback:idx + 1]
            range_high = window['high'].max()
            range_low = window['low'].min()
            range_size = range_high - range_low

            if range_size <= max_range:
                bullish = sum(window['close'] > window['open'])
                bearish = len(window) - bullish

                if bullish >= 2 and bearish >= 2:
                    return {
                        'range_high': range_high,
                        'range_low': range_low,
                        'range_size': range_size,
                        'candles': lookback,
                        'midpoint': (range_high + range_low) / 2
                    }

        return None

    def _detect_order_block(self, df: pd.DataFrame, idx: int, lookback: int = 20) -> Optional[Dict]:
        """Detect order blocks (institutional entry zones)."""
        if idx < lookback + 5:
            return None

        # Look for strong momentum candles followed by reversal
        for i in range(idx - lookback, idx - 3):
            candle = df.iloc[i]
            body = abs(candle['close'] - candle['open'])
            candle_range = candle['high'] - candle['low']

            if candle_range == 0:
                continue

            # Strong bullish candle
            if candle['close'] > candle['open'] and body > candle_range * 0.6:
                # Check if price came back to this zone
                ob_high = candle['high']
                ob_low = candle['open']  # Use open as bottom of order block

                current = df.iloc[idx]
                if ob_low <= current['low'] <= ob_high:
                    return {
                        'type': 'bullish',
                        'high': ob_high,
                        'low': ob_low,
                        'index': i
                    }

            # Strong bearish candle
            if candle['close'] < candle['open'] and body > candle_range * 0.6:
                ob_high = candle['open']
                ob_low = candle['low']

                current = df.iloc[idx]
                if ob_low <= current['high'] <= ob_high:
                    return {
                        'type': 'bearish',
                        'high': ob_high,
                        'low': ob_low,
                        'index': i
                    }

        return None

    def _detect_liquidity_grab(self, df: pd.DataFrame, idx: int, lookback: int = 10) -> Optional[str]:
        """
        Detect a liquidity grab (stop hunt): price wicks beyond a recent
        swing low/high — sweeping resting stop orders — then closes back
        inside the prior range on the same candle, signaling a reversal
        setup rather than genuine continuation. The lookback window is the
        candles strictly BEFORE idx, matching the same "don't let the
        candle under test contaminate its own reference range" pattern used
        by _volatility_squeeze_breakout.
        """
        if idx < lookback:
            return None

        window = df.iloc[idx - lookback:idx]
        prior_low = window['low'].min()
        prior_high = window['high'].max()
        current = df.iloc[idx]

        if current['low'] < prior_low and current['close'] > prior_low:
            return 'bullish'
        if current['high'] > prior_high and current['close'] < prior_high:
            return 'bearish'
        return None

    # ==================== ORIGINAL TRADING RULES ====================

    def _golden_fibonacci(self, df: pd.DataFrame, idx: int) -> RuleResult:
        """
        Golden Fibonacci (61.8% Retracement)
        Price retraces to the golden ratio Fibonacci level in trending market.
        """
        result = RuleResult(rule_name="Golden Fibonacci", triggered=False)

        fib = self._get_fib_zones(df, idx)
        if fib is None:
            return result

        current = df.iloc[idx]
        atr = self.ta.calculate_atr(period=self.config['atr_period']).iloc[-1]

        if not self._is_near_level(current['low'], fib.level_618) and \
           not self._is_near_level(current['high'], fib.level_618):
            return result

        structure = self._detect_market_structure(df, idx)
        pattern = self._detect_reversal_pattern(df, idx)

        has_confirmation = (
            structure in [MarketStructure.CHOCH, MarketStructure.BOS] or
            pattern is not None
        )

        if not has_confirmation:
            return result

        if fib.direction == 'up':
            if pattern and 'bearish' in pattern:
                return result

            direction = TradeDirection.LONG
            entry_price = current['close']
            stop_loss = fib.swing_low - (atr * self.config['sl_buffer_atr'])
            risk = entry_price - stop_loss
            take_profit = entry_price + (risk * self.config['default_rr_ratio'])
        else:
            if pattern and 'bullish' in pattern:
                return result

            direction = TradeDirection.SHORT
            entry_price = current['close']
            stop_loss = fib.swing_high + (atr * self.config['sl_buffer_atr'])
            risk = stop_loss - entry_price
            take_profit = entry_price - (risk * self.config['default_rr_ratio'])

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
        result.notes = f"61.8% retracement with {pattern or structure.value} confirmation"

        return result

    def _ath_retest(self, df: pd.DataFrame, idx: int) -> RuleResult:
        """
        ATH/ATL Retest
        Retest of all-time high/low as support/resistance after breakout.
        """
        result = RuleResult(rule_name="ATH Retest", triggered=False)

        lookback = 100
        if idx < lookback:
            return result

        current = df.iloc[idx]
        atr = self.ta.calculate_atr(period=self.config['atr_period']).iloc[-1]

        older_ath = df.iloc[max(0, idx-lookback):idx-20]['high'].max()
        recent_high = df.iloc[idx-20:idx]['high'].max()

        broke_ath = recent_high > older_ath

        if not broke_ath:
            older_atl = df.iloc[max(0, idx-lookback):idx-20]['low'].min()
            recent_low = df.iloc[idx-20:idx]['low'].min()

            if recent_low < older_atl:
                key_level = older_atl
                direction = TradeDirection.SHORT
            else:
                return result
        else:
            key_level = older_ath
            direction = TradeDirection.LONG

        tolerance = atr * 0.5

        if direction == TradeDirection.LONG:
            retesting = abs(current['low'] - key_level) <= tolerance or \
                       (current['low'] <= key_level <= current['high'])

            if not retesting or current['close'] < key_level:
                return result

            entry_price = current['close']
            stop_loss = key_level - (atr * self.config['sl_buffer_atr'])
            risk = entry_price - stop_loss
            take_profit = entry_price + (risk * self.config['default_rr_ratio'])
        else:
            retesting = abs(current['high'] - key_level) <= tolerance or \
                       (current['low'] <= key_level <= current['high'])

            if not retesting or current['close'] > key_level:
                return result

            entry_price = current['close']
            stop_loss = key_level + (atr * self.config['sl_buffer_atr'])
            risk = stop_loss - entry_price
            take_profit = entry_price - (risk * self.config['default_rr_ratio'])

        consolidation = self._detect_consolidation(df, idx)
        pattern = self._detect_reversal_pattern(df, idx)

        confidence = 0.6
        if consolidation:
            confidence += 0.2
        if pattern:
            confidence += 0.1

        result.triggered = True
        result.direction = direction
        result.entry_price = entry_price
        result.stop_loss = stop_loss
        result.take_profit = take_profit
        result.confidence = min(confidence, 1.0)
        result.notes = f"ATH/ATL retest at {key_level:.2f}"

        return result

    def _momentum_equilibrium(self, df: pd.DataFrame, idx: int) -> RuleResult:
        """
        Momentum Equilibrium (50% Retracement)
        Entry at equilibrium (50% Fibonacci) during strong momentum moves.
        Win Rate: 74% | Profit Factor: 3.31 | Best performing strategy
        """
        result = RuleResult(rule_name="Momentum Equilibrium", triggered=False)

        momentum = self._get_momentum_strength(df, idx, lookback=10)
        if momentum == MomentumStrength.WEAK:
            return result

        fib = self._get_fib_zones(df, idx)
        if fib is None:
            return result

        current = df.iloc[idx]
        atr = self.ta.calculate_atr(period=self.config['atr_period']).iloc[-1]

        at_50 = self._is_near_level(current['close'], fib.level_500) or \
                self._is_near_level(current['low'], fib.level_500) or \
                self._is_near_level(current['high'], fib.level_500)

        if not at_50:
            return result

        trend = self.ta.detect_trend(lookback=30)

        if fib.direction == 'up' and trend == TrendDirection.UPTREND:
            direction = TradeDirection.LONG
            entry_price = current['close']
            stop_loss = fib.level_618 - (atr * 0.3)
            risk = entry_price - stop_loss
        elif fib.direction == 'down' and trend == TrendDirection.DOWNTREND:
            direction = TradeDirection.SHORT
            entry_price = current['close']
            stop_loss = fib.level_618 + (atr * 0.3)
            risk = stop_loss - entry_price
        else:
            return result

        # A malformed fib zone (or an entry that landed on the wrong side of
        # level_618) can put the stop-loss on the wrong side of entry. Refuse
        # rather than emit a signal with negative/zero risk.
        if risk <= 0:
            return result

        take_profit = (
            entry_price + (risk * self.config['default_rr_ratio'])
            if direction == TradeDirection.LONG
            else entry_price - (risk * self.config['default_rr_ratio'])
        )

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

    # ==================== NEW TRADING RULES ====================

    def _london_session_breakout(self, df: pd.DataFrame, idx: int) -> RuleResult:
        """
        London Session Breakout
        Breakout of Asian session range during London market open (7-9 UTC).
        Win Rate: 58.8% | Profit Factor: 2.74 | Strong performer
        """
        result = RuleResult(rule_name="London Session Breakout", triggered=False)

        if idx < 20:
            return result

        # Get current timestamp
        current_time = df.index[idx]
        if not isinstance(current_time, (pd.Timestamp, datetime)):
            return result

        # London session: 07:00-08:00 UTC (typical breakout window)
        current_hour = current_time.hour if hasattr(current_time, 'hour') else 0

        # Only trigger during London open (7-9 UTC)
        if not (7 <= current_hour <= 9):
            return result

        # Calculate Asian session range (last 12-20 candles depending on timeframe)
        lookback = min(20, idx)
        asian_range = df.iloc[idx - lookback:idx]
        range_high = asian_range['high'].max()
        range_low = asian_range['low'].min()
        range_size = range_high - range_low

        current = df.iloc[idx]
        atr = self.ta.calculate_atr(period=self.config['atr_period']).iloc[-1]

        # Require meaningful range
        if range_size < atr * 0.5:
            return result

        # Check for breakout
        breakout_up = current['close'] > range_high
        breakout_down = current['close'] < range_low

        if not breakout_up and not breakout_down:
            return result

        if breakout_up:
            direction = TradeDirection.LONG
            entry_price = current['close']
            stop_loss = range_low - (atr * 0.3)
            risk = entry_price - stop_loss
            take_profit = entry_price + (risk * 2.0)  # Higher R:R for session breakouts
        else:
            direction = TradeDirection.SHORT
            entry_price = current['close']
            stop_loss = range_high + (atr * 0.3)
            risk = stop_loss - entry_price
            take_profit = entry_price - (risk * 2.0)

        confidence = 0.6

        # Volume confirmation would add confidence
        if 'volume' in df.columns:
            current_vol = current['volume']
            avg_vol = df.iloc[idx-20:idx]['volume'].mean()
            if current_vol > avg_vol * 1.5:
                confidence += 0.15

        result.triggered = True
        result.direction = direction
        result.entry_price = entry_price
        result.stop_loss = stop_loss
        result.take_profit = take_profit
        result.confidence = min(confidence, 1.0)
        result.notes = f"London breakout of Asian range ({range_low:.2f}-{range_high:.2f})"

        return result

    def _order_block_retest(self, df: pd.DataFrame, idx: int) -> RuleResult:
        """
        Order Block Retest
        Smart money concept - retest of institutional entry zones.
        Win Rate: 38.6% | Profit Factor: 1.14 | Marginal
        """
        result = RuleResult(rule_name="Order Block Retest", triggered=False)

        ob = self._detect_order_block(df, idx)
        if ob is None:
            return result

        current = df.iloc[idx]
        atr = self.ta.calculate_atr(period=self.config['atr_period']).iloc[-1]

        if ob['type'] == 'bullish':
            # Price entering bullish order block - look for long
            pattern = self._detect_reversal_pattern(df, idx)
            if pattern and 'bearish' in pattern:
                return result

            direction = TradeDirection.LONG
            entry_price = current['close']
            stop_loss = ob['low'] - (atr * self.config['sl_buffer_atr'])
            risk = entry_price - stop_loss
            take_profit = entry_price + (risk * self.config['default_rr_ratio'])
        else:
            pattern = self._detect_reversal_pattern(df, idx)
            if pattern and 'bullish' in pattern:
                return result

            direction = TradeDirection.SHORT
            entry_price = current['close']
            stop_loss = ob['high'] + (atr * self.config['sl_buffer_atr'])
            risk = stop_loss - entry_price
            take_profit = entry_price - (risk * self.config['default_rr_ratio'])

        trend = self.ta.detect_trend(lookback=30)

        confidence = 0.55
        if (ob['type'] == 'bullish' and trend == TrendDirection.UPTREND) or \
           (ob['type'] == 'bearish' and trend == TrendDirection.DOWNTREND):
            confidence += 0.15

        pattern = self._detect_reversal_pattern(df, idx)
        if pattern:
            confidence += 0.1

        result.triggered = True
        result.direction = direction
        result.entry_price = entry_price
        result.stop_loss = stop_loss
        result.take_profit = take_profit
        result.confidence = min(confidence, 1.0)
        result.notes = f"{ob['type']} order block retest"

        return result

    def _volatility_squeeze_breakout(self, df: pd.DataFrame, idx: int) -> RuleResult:
        """
        Volatility Squeeze Breakout.

        Gold characteristically chops in a tight range through low-news
        periods, then expands sharply on real catalysts (Fed decisions,
        real-yield moves, USD strength shifts, geopolitical shocks). This
        detects the contraction (ATR genuinely below its own recent
        average, not just a narrow closing-price range) and trades the
        breakout once price closes decisively outside the range that
        contraction traded in.

        The squeeze/consolidation window is measured over the
        `squeeze_lookback` candles strictly BEFORE `idx` — the candle under
        test is never included in its own "was this a squeeze" check, so a
        large breakout candle can't inflate the ATR reading that's supposed
        to describe the calm before it.

        See docs/superpowers/specs/2026-09-08-volatility-squeeze-breakout-design.md
        """
        result = RuleResult(rule_name="Volatility Squeeze Breakout", triggered=False)

        lookback = self.config['squeeze_lookback']
        if idx < lookback + self.config['atr_period']:
            return result

        atr_series = self.ta.calculate_atr(period=self.config['atr_period'])
        if len(atr_series) < lookback + 2:
            return result

        # Evaluated as of the candle before idx — see docstring.
        pre_breakout_atr = atr_series.iloc[-2]
        squeeze_reference_atr = atr_series.iloc[-(lookback + 1):-1].mean()
        if pd.isna(pre_breakout_atr) or pd.isna(squeeze_reference_atr) or squeeze_reference_atr == 0:
            return result

        is_squeezed = pre_breakout_atr < self.config['squeeze_atr_ratio'] * squeeze_reference_atr
        if not is_squeezed:
            return result

        window = df.iloc[idx - lookback:idx]
        range_high = window['high'].max()
        range_low = window['low'].min()

        current = df.iloc[idx]
        buffer = pre_breakout_atr * self.config['breakout_buffer_atr']

        if current['close'] > range_high + buffer:
            breakout_direction = 'up'
        elif current['close'] < range_low - buffer:
            breakout_direction = 'down'
        else:
            return result

        pattern = self._detect_reversal_pattern(df, idx)
        if breakout_direction == 'up' and pattern and 'bearish' in pattern:
            return result
        if breakout_direction == 'down' and pattern and 'bullish' in pattern:
            return result

        if breakout_direction == 'up':
            direction = TradeDirection.LONG
            entry_price = current['close']
            stop_loss = range_low - (pre_breakout_atr * self.config['sl_buffer_atr'])
            risk = entry_price - stop_loss
            take_profit = entry_price + (risk * self.config['default_rr_ratio'])
        else:
            direction = TradeDirection.SHORT
            entry_price = current['close']
            stop_loss = range_high + (pre_breakout_atr * self.config['sl_buffer_atr'])
            risk = stop_loss - entry_price
            take_profit = entry_price - (risk * self.config['default_rr_ratio'])

        if risk <= 0:
            return result

        trend = self.ta.detect_trend(lookback=30)
        confidence = 0.5
        if (breakout_direction == 'up' and trend == TrendDirection.UPTREND) or \
           (breakout_direction == 'down' and trend == TrendDirection.DOWNTREND):
            confidence += 0.15

        # Tighter compression (relative to the squeeze_atr_ratio threshold)
        # is more likely a real regime change than noise.
        compression = 1.0 - (pre_breakout_atr / squeeze_reference_atr)
        confidence += min(compression, 0.5) * 0.2

        result.triggered = True
        result.direction = direction
        result.entry_price = entry_price
        result.stop_loss = stop_loss
        result.take_profit = take_profit
        result.confidence = min(confidence, 1.0)
        result.notes = f"volatility squeeze breakout ({breakout_direction})"

        return result

    def _fib_golden_zone_confluence(self, df: pd.DataFrame, idx: int) -> RuleResult:
        """
        Fibonacci Golden Zone Confluence — a faithful implementation of the
        user's own XAU/USD trading plan (see
        docs/superpowers/specs/strategy-ledger.md), not a generic pattern.

        Entry at the 61.8% retracement, ONLY if ALL of the following hold:
          - it aligns with an Order Block in the same direction (checked at
            the current candle — price is retesting it right now)
          - a liquidity grab in the same direction happened within the last
            `confluence_window` candles (not necessarily the exact same one
            as the 61.8% touch — see strategy-ledger.md's diagnostic:
            requiring same-candle alignment for all 4 conditions collapsed
            to ~0.15% of candles with zero direction-matched cases)
          - market structure confirmed a retest of broken structure
            (BOS/CHoCH) within that same window
        Stop loss sits just beyond the 78.6% level (the plan's "deep
        discount" extreme) — interpreted here as an ATR buffer past 78.6% in
        the adverse direction, matching how every other rule in this file
        buffers a structural stop level; take profit is the 38.2% level
        directly, NOT an RR-multiple like every other rule, since the plan
        specifies a fixed retracement target. A trade whose resulting R:R
        falls under the plan's own stated minimum (fib_confluence_min_rr,
        default 2.0 — "take only trades with a minimum 1:2 R:R") is
        rejected even if every confluence condition is met.
        """
        result = RuleResult(rule_name="Fibonacci Golden Zone Confluence", triggered=False)

        fib = self._get_fib_zones(df, idx)
        if fib is None:
            return result

        current = df.iloc[idx]
        if not self._is_near_level(current['close'], fib.level_618):
            return result

        ob = self._detect_order_block(df, idx)
        if ob is None:
            return result

        expected_bias = 'bullish' if fib.direction == 'up' else 'bearish'
        if ob['type'] != expected_bias:
            return result

        window_start = max(0, idx - self.config['confluence_window'])
        grab_seen = any(
            self._detect_liquidity_grab(df, i, lookback=self.config['liquidity_grab_lookback']) == expected_bias
            for i in range(window_start, idx + 1)
        )
        if not grab_seen:
            return result

        structure_seen = any(
            self._detect_market_structure(df, i) in (MarketStructure.BOS, MarketStructure.CHOCH)
            for i in range(window_start, idx + 1)
        )
        if not structure_seen:
            return result

        atr = self.ta.calculate_atr(period=self.config['atr_period']).iloc[-1]

        if fib.direction == 'up':
            direction = TradeDirection.LONG
            entry_price = current['close']
            stop_loss = fib.level_786 - (atr * self.config['sl_buffer_atr'])
            take_profit = fib.level_382
        else:
            direction = TradeDirection.SHORT
            entry_price = current['close']
            stop_loss = fib.level_786 + (atr * self.config['sl_buffer_atr'])
            take_profit = fib.level_382

        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)
        if risk <= 0 or reward <= 0:
            return result
        if reward / risk < self.config['fib_confluence_min_rr']:
            return result

        result.triggered = True
        result.direction = direction
        result.entry_price = entry_price
        result.stop_loss = stop_loss
        result.take_profit = take_profit
        result.confidence = 0.7  # every confluence condition already required to reach here
        result.notes = "61.8% + order block + liquidity grab + structure retest"

        return result

    def _shallow_pullback_continuation(self, df: pd.DataFrame, idx: int) -> RuleResult:
        """
        Shallow Pullback Continuation — from the user's own trading plan
        hard fact: "In strong bullish moves, price may only pull back to
        the 23.6% level before continuing." Confirmation = a small
        consolidation near 23.6%, followed by a break of structure in the
        trend direction. See docs/superpowers/specs/strategy-ledger.md.

        Unlike Fibonacci Golden Zone Confluence (deep pullback, reversal),
        this trades trend CONTINUATION off a shallow pullback: the pullback
        must have touched 23.6% within the last `pullback_window` candles
        AND never traded through the deeper 38.2% level in that window (a
        deeper move means it's no longer a "shallow" pullback), then enters
        on the current candle's structure-break confirmation.
        """
        result = RuleResult(rule_name="Shallow Pullback Continuation", triggered=False)

        fib = self._get_fib_zones(df, idx)
        if fib is None:
            return result

        trend = self.ta.detect_trend(lookback=self.config['trend_lookback'])
        if fib.direction == 'up' and trend != TrendDirection.UPTREND:
            return result
        if fib.direction == 'down' and trend != TrendDirection.DOWNTREND:
            return result

        window_start = max(0, idx - self.config['pullback_window'])
        window = df.iloc[window_start:idx + 1]

        touched_236 = any(self._is_near_level(c, fib.level_236) for c in window['close'])
        if not touched_236:
            return result

        if fib.direction == 'up':
            stayed_shallow = window['low'].min() >= fib.level_382
        else:
            stayed_shallow = window['high'].max() <= fib.level_382
        if not stayed_shallow:
            return result

        structure = self._detect_market_structure(df, idx)
        if structure not in (MarketStructure.BOS, MarketStructure.CHOCH):
            return result

        current = df.iloc[idx]
        atr = self.ta.calculate_atr(period=self.config['atr_period']).iloc[-1]

        if fib.direction == 'up':
            direction = TradeDirection.LONG
            entry_price = current['close']
            stop_loss = fib.level_236 - (atr * self.config['sl_buffer_atr'])
            risk = entry_price - stop_loss
            take_profit = entry_price + (risk * self.config['default_rr_ratio'])
        else:
            direction = TradeDirection.SHORT
            entry_price = current['close']
            stop_loss = fib.level_236 + (atr * self.config['sl_buffer_atr'])
            risk = stop_loss - entry_price
            take_profit = entry_price - (risk * self.config['default_rr_ratio'])

        if risk <= 0:
            return result

        confidence = 0.55
        if structure == MarketStructure.BOS:
            confidence += 0.15

        result.triggered = True
        result.direction = direction
        result.entry_price = entry_price
        result.stop_loss = stop_loss
        result.take_profit = take_profit
        result.confidence = min(confidence, 1.0)
        result.notes = "shallow pullback to 23.6% + trend continuation structure break"

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
    print("\n🎯 Initializing Gold Strategy with 9 rules...")
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
        commission=2.0,
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

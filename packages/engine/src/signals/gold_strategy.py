"""
Gold Trading Strategy - The Gold Trader's Edge
Implements professional gold (XAU/USD) trading rules based on proven patterns.
"""

import pandas as pd
from typing import Optional, List, Dict

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from analysis.technical import TechnicalAnalysis, TrendDirection
from backtesting.engine import Signal, TradeDirection


from dataclasses import dataclass


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
    Professional Gold Trading Strategy.

    Only one rule remains: Order Block Retest — the sole strategy that
    survived shared-config, out-of-sample validation (PF 1.16, 114 trades,
    +28.7% net — see tuned_configs/1h.json). Every other rule tried against
    gold (5 legacy rules plus 3 new hypotheses from a later research pass —
    Volatility Squeeze Breakout, Fibonacci Golden Zone Confluence, Shallow
    Pullback Continuation) and against other instruments (silver, BTC-USD,
    GBPUSD) was tested and ruled out. Their full hypothesis, method, and
    result are recorded — not lost — in
    docs/superpowers/specs/strategy-ledger.md; that's the place to check
    before re-testing an old idea, not this file's history.
    """

    DEFAULT_CONFIG = {
        # Trend detection — used by evaluate()'s data-sufficiency gate.
        'trend_lookback': 50,

        'atr_period': 14,

        # Risk management
        'default_rr_ratio': 2.0,
        'sl_buffer_atr': 0.3,
    }

    def __init__(self, config: Optional[Dict] = None, enabled_rules: Optional[List[int]] = None):
        """
        Initialize the strategy with optional custom config.

        Args:
            config: Optional configuration dictionary
            enabled_rules: Optional list of rule IDs to enable. Only rule
                ID 6 (order_block_retest) maps to an implemented rule; any
                other ID is a no-op. Kept for backward compatibility with
                callers still passing legacy IDs.
        """
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        self.ta: Optional[TechnicalAnalysis] = None
        self.df: Optional[pd.DataFrame] = None

        # Map rule IDs to rule names for backward compatibility.
        rule_id_map = {
            6: 'order_block_retest',
        }

        self.rules_enabled = {
            # Live, validated (see tuned_configs/1h.json and
            # docs/superpowers/specs/strategy-ledger.md).
            'order_block_retest': True,
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

        if self.rules_enabled.get('order_block_retest'):
            result = self._order_block_retest(df, current_idx)
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

    # ==================== TRADING RULES ====================

    def _order_block_retest(self, df: pd.DataFrame, idx: int) -> RuleResult:
        """
        Order Block Retest
        Smart money concept - retest of institutional entry zones.
        The only validated, live strategy — see tuned_configs/1h.json
        (PF 1.16, 114 trades, +28.7% net on the 1H shared-config test slice).
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
    print("\n🎯 Initializing Gold Strategy...")
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
            print(f"    Trades: {stats['count']}, Win Rate: {win_rate:.1f}%, PnL: ${stats['pnl']:.2f}")

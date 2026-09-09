"""
Forex Session Strategy - The Gold Trader's Edge

Session-driven strategies for major forex pairs, structurally distinct
from GoldStrategy (which trades order-block/zone-retest concepts). The
first and only rule here — Asian Range London Breakout — exploits a real,
causally-grounded forex pattern: GBP (and to a lesser extent EUR)
liquidity concentrates in the London session, so price often consolidates
during the quiet Asian session and breaks out decisively at London open.

Validated on GBPUSD and EURUSD 1H via a real 70/30 train/test split before
being implemented here — see
docs/superpowers/specs/2026-09-09-gbpusd-asian-range-breakout-design.md.
Not yet wired into the live multi-timeframe service — going live is a
separate, later decision, same convention as every GoldStrategy rule.
"""

import pandas as pd
from typing import Optional, Dict

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from analysis.technical import TechnicalAnalysis
from backtesting.engine import Signal, TradeDirection
from signals.gold_strategy import RuleResult


class ForexSessionStrategy:
    """
    Session-driven forex strategy. Only one rule: Asian Range London
    Breakout. See module docstring.
    """

    DEFAULT_CONFIG = {
        # Asian session window, UTC hours [start, end) — price consolidates
        # here before London desks open.
        'asian_hours_start': 0,
        'asian_hours_end': 7,

        # Entry only evaluated on the candle at this UTC hour (the first
        # London-session candle) — not re-checked on every candle within a
        # wider window, matching what was actually validated.
        'entry_hour': 7,

        # How many candles back to look for this session's Asian-hour
        # candles (must cover a full Asian session plus slack for gaps).
        'lookback_candles': 12,

        # Minimum Asian-hour candles required to trust the measured range —
        # guards against a weekend/holiday gap producing a spurious range
        # from too few candles.
        'min_asian_candles': 5,

        'atr_period': 14,

        # How far past the Asian range (in ATR) price must close to count
        # as a genuine breakout, not a marginal poke.
        'breakout_buffer_atr': 0.1,

        # Stop loss sits this many ATR beyond the OPPOSITE side of the
        # Asian range (a real structural invalidation level).
        'sl_buffer_atr': 0.3,

        'default_rr_ratio': 2.0,
    }

    def __init__(self, config: Optional[Dict] = None):
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        self.ta: Optional[TechnicalAnalysis] = None
        self.df: Optional[pd.DataFrame] = None

        self.rules_enabled = {
            'asian_range_london_breakout': True,
        }

    def set_rule_enabled(self, rule_name: str, enabled: bool):
        """Enable or disable a specific rule."""
        if rule_name in self.rules_enabled:
            self.rules_enabled[rule_name] = enabled

    def evaluate(self, df: pd.DataFrame, current_idx: int) -> Optional[Signal]:
        """Evaluate all rules and return a signal if any rule triggers."""
        if current_idx < self.config['lookback_candles'] + self.config['atr_period']:
            return None

        self.df = df
        self.ta = TechnicalAnalysis(df.iloc[:current_idx + 1])

        results = []

        if self.rules_enabled.get('asian_range_london_breakout'):
            result = self._asian_range_london_breakout(df, current_idx)
            if result.triggered:
                results.append(result)

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

    def _asian_range_london_breakout(self, df: pd.DataFrame, idx: int) -> RuleResult:
        """
        Asian Range London Breakout.

        Only evaluated on the candle at `entry_hour` (UTC) — the first
        London-session candle. Measures the high/low range of this same
        session's Asian-hour candles (strictly before idx, so the entry
        candle can't inflate its own reference range), then triggers if the
        entry candle's close breaks decisively outside that range.
        """
        result = RuleResult(rule_name="Asian Range London Breakout", triggered=False)

        current_time = df.index[idx]
        if current_time.hour != self.config['entry_hour']:
            return result

        window_start = max(0, idx - self.config['lookback_candles'])
        window = df.iloc[window_start:idx]
        asian_start, asian_end = self.config['asian_hours_start'], self.config['asian_hours_end']
        asian_candles = window[[asian_start <= t.hour < asian_end for t in window.index]]

        if len(asian_candles) < self.config['min_asian_candles']:
            return result

        asian_high = asian_candles['high'].max()
        asian_low = asian_candles['low'].min()

        atr = self.ta.calculate_atr(period=self.config['atr_period']).iloc[-1]
        if pd.isna(atr):
            return result

        current = df.iloc[idx]
        buffer = atr * self.config['breakout_buffer_atr']

        if current['close'] > asian_high + buffer:
            direction = TradeDirection.LONG
            entry_price = current['close']
            stop_loss = asian_low - atr * self.config['sl_buffer_atr']
            risk = entry_price - stop_loss
            take_profit = entry_price + risk * self.config['default_rr_ratio']
        elif current['close'] < asian_low - buffer:
            direction = TradeDirection.SHORT
            entry_price = current['close']
            stop_loss = asian_high + atr * self.config['sl_buffer_atr']
            risk = stop_loss - entry_price
            take_profit = entry_price - risk * self.config['default_rr_ratio']
        else:
            return result

        if risk <= 0:
            return result

        result.triggered = True
        result.direction = direction
        result.entry_price = entry_price
        result.stop_loss = stop_loss
        result.take_profit = take_profit
        result.confidence = 0.6
        result.notes = "Asian session range breakout at London open"

        return result


def create_strategy_function(strategy: ForexSessionStrategy):
    """Create a strategy function compatible with BacktestEngine."""
    def strategy_func(df: pd.DataFrame, idx: int) -> Optional[Signal]:
        return strategy.evaluate(df, idx)
    return strategy_func

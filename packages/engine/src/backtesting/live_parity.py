"""
Backtest the trade population live actually publishes.

Shared by tune_strategy.py, tune_forex_session_strategy.py and
scripts/validate_signal_gates.py so every validation number means the same
thing as a live signal:

- risk > 0, reward > 0, R:R >= 1.5 and confidence >= 0.60, the same checks
  SignalValidator applies with the live min_rr_ratio / min_confidence
  settings. The tuner used to skip the confidence check, so it scored a
  different set of trades from the ones live sends;
- one open trade at a time (BacktestEngine max_open_trades=1), which live
  now enforces too (signals/open_signal_gate.py);
- when scoring a slice, the strategy sees warm-up history before it, as live
  does, but no trade opens before the slice starts.
"""

from typing import Callable, Dict, List, Optional

import pandas as pd

from backtesting.engine import BacktestEngine, BacktestResult, Signal, Trade, TradeStatus
from signals.realtime_generator import SignalValidator

# Matches the live `min_rr_ratio` / `min_confidence` settings.
PRODUCTION_MIN_RR = 1.5
PRODUCTION_MIN_CONFIDENCE = 0.60

StrategyFunc = Callable[[pd.DataFrame, int], Optional[Signal]]


def live_gated_strategy_func(strategy, min_rr: float = PRODUCTION_MIN_RR,
                             min_confidence: float = PRODUCTION_MIN_CONFIDENCE) -> StrategyFunc:
    """Wrap strategy.evaluate so only signals live would publish get through."""
    def strategy_func(df, idx):
        signal = strategy.evaluate(df, idx)
        if signal is None or signal.confidence < min_confidence:
            return None
        risk_reward = SignalValidator.compute_risk_reward(signal)
        if risk_reward is None or not SignalValidator.meets_min_rr(risk_reward[2], min_rr):
            return None
        return signal
    return strategy_func


def run_on_window(df: pd.DataFrame, start: pd.Timestamp, strategy_func: StrategyFunc,
                  warmup: int) -> BacktestResult:
    """
    Backtest df from `start` onward, feeding the strategy `warmup` extra
    candles of history before `start` without letting it trade on them.
    """
    start_pos = df.index.get_loc(start)
    frame = df.iloc[max(0, start_pos - warmup):]

    def windowed(frame_df, idx):
        if frame_df.index[idx] < start:
            return None
        return strategy_func(frame_df, idx)

    engine = BacktestEngine(initial_balance=10000, position_size_pct=2.0)
    return engine.run(frame, windowed, max_open_trades=1)


def max_losing_streak(trades: List[Trade]) -> int:
    longest = current = 0
    for trade in trades:
        current = current + 1 if trade.pnl <= 0 else 0
        longest = max(longest, current)
    return longest


def resolved_stats(result) -> Dict:
    """
    PF / trades / win rate / net % / max losing streak over RESOLVED
    (CLOSED_TP/CLOSED_SL) trades only. A CLOSED_MANUAL trade is an open
    position marked to market at the end of the slice, not a real result.
    """
    resolved = [t for t in result.trades if t.status in (TradeStatus.CLOSED_TP, TradeStatus.CLOSED_SL)]
    total_trades = len(resolved)
    if total_trades == 0:
        return {'profit_factor': 0.0, 'total_trades': 0, 'win_rate': 0.0,
                'net_profit_pct': 0.0, 'max_losing_streak': 0}

    winning = [t for t in resolved if t.pnl > 0]
    losing = [t for t in resolved if t.pnl <= 0]
    total_profit = sum(t.pnl for t in winning)
    total_loss = abs(sum(t.pnl for t in losing))

    return {
        'profit_factor': total_profit / total_loss if total_loss > 0 else float('inf'),
        'total_trades': total_trades,
        'win_rate': len(winning) / total_trades * 100,
        'net_profit_pct': sum(t.pnl for t in resolved) / result.initial_balance * 100,
        'max_losing_streak': max_losing_streak(resolved),
    }

"""
Signal outcome decision logic.

Determines whether an open signal should be closed (TP/SL hit) or expired,
given a newly-closed candle. Mirrors BacktestEngine.check_and_close_trades()
exactly (stop-loss checked before take-profit when both would be hit by the
same candle) so live outcome tracking stays consistent with the validated
backtest numbers.
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

import pandas as pd


class OutcomeAction(Enum):
    NONE = "none"
    CLOSED_TP = "closed_tp"
    CLOSED_SL = "closed_sl"
    EXPIRED = "expired"


@dataclass
class OpenSignalLike:
    """Minimal view of a Signal needed to evaluate its outcome."""
    id: int
    direction: str  # "LONG" or "SHORT"
    entry_price: float
    stop_loss: float
    take_profit: float
    timestamp: datetime  # when the signal was generated (its entry candle's time)


def evaluate_signal_outcome(
    signal: OpenSignalLike,
    candle: pd.Series,
    candle_time: datetime,
    expiry_hours: float,
) -> OutcomeAction:
    """
    Decide what should happen to `signal` given a new candle.

    Never evaluates a candle at or before the signal's own entry time.
    """
    if candle_time <= signal.timestamp:
        return OutcomeAction.NONE

    if signal.direction == "LONG":
        if candle['low'] <= signal.stop_loss:
            return OutcomeAction.CLOSED_SL
        if candle['high'] >= signal.take_profit:
            return OutcomeAction.CLOSED_TP
    else:  # SHORT
        if candle['high'] >= signal.stop_loss:
            return OutcomeAction.CLOSED_SL
        if candle['low'] <= signal.take_profit:
            return OutcomeAction.CLOSED_TP

    elapsed_hours = (candle_time - signal.timestamp).total_seconds() / 3600
    if elapsed_hours > expiry_hours:
        return OutcomeAction.EXPIRED

    return OutcomeAction.NONE

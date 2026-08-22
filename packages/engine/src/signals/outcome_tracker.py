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


import sys
from pathlib import Path as _Path

sys.path.insert(0, str(_Path(__file__).parent.parent))

from database.connection import DatabaseManager
from database.models import SignalStatus
from database.signal_repository import SignalRepository


class SignalOutcomeTracker:
    """
    Checks every open signal for a given symbol/timeframe against a newly
    closed candle, closing it on TP/SL hit or expiring it if it's been open
    too long. Meant to be called once per candle from the live signal loop.
    """

    def __init__(self, database_url: str, symbol: str, timeframe: str, expiry_hours: float):
        self.db_manager = DatabaseManager(database_url)
        self.symbol = symbol
        self.timeframe = timeframe
        self.expiry_hours = expiry_hours

    def check_candle(self, candle: pd.Series, candle_time) -> None:
        with self.db_manager.session_scope() as session:
            repo = SignalRepository(session)
            open_signals = repo.get_open_signals(symbol=self.symbol, timeframe=self.timeframe)

            for sig in open_signals:
                signal_like = OpenSignalLike(
                    id=sig.id,
                    direction=sig.direction.value,
                    entry_price=sig.entry_price,
                    stop_loss=sig.stop_loss,
                    take_profit=sig.take_profit,
                    timestamp=sig.timestamp,
                )
                action = evaluate_signal_outcome(signal_like, candle, candle_time, self.expiry_hours)

                if action == OutcomeAction.CLOSED_TP:
                    repo.close_open_signal(
                        sig.id, exit_price=sig.take_profit,
                        status=SignalStatus.CLOSED_TP, closed_at=candle_time,
                    )
                elif action == OutcomeAction.CLOSED_SL:
                    repo.close_open_signal(
                        sig.id, exit_price=sig.stop_loss,
                        status=SignalStatus.CLOSED_SL, closed_at=candle_time,
                    )
                elif action == OutcomeAction.EXPIRED:
                    repo.close_open_signal(
                        sig.id, exit_price=None,
                        status=SignalStatus.CANCELLED, closed_at=candle_time,
                        note_suffix=f" [expired after {self.expiry_hours}h with no resolution]",
                    )

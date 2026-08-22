"""Tests for signal outcome decision logic."""
import sys
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from signals.outcome_tracker import OpenSignalLike, OutcomeAction, evaluate_signal_outcome


def make_candle(low, high):
    return pd.Series({'open': (low + high) / 2, 'high': high, 'low': low, 'close': (low + high) / 2})


class TestEvaluateSignalOutcome:
    def test_long_hits_stop_loss(self):
        signal = OpenSignalLike(
            id=1, direction="LONG", entry_price=2000.0,
            stop_loss=1990.0, take_profit=2030.0,
            timestamp=datetime(2026, 1, 1, 10, 0),
        )
        candle = make_candle(low=1985.0, high=2010.0)
        result = evaluate_signal_outcome(
            signal, candle, candle_time=datetime(2026, 1, 1, 11, 0), expiry_hours=48
        )
        assert result == OutcomeAction.CLOSED_SL

    def test_long_hits_take_profit(self):
        signal = OpenSignalLike(
            id=1, direction="LONG", entry_price=2000.0,
            stop_loss=1990.0, take_profit=2030.0,
            timestamp=datetime(2026, 1, 1, 10, 0),
        )
        candle = make_candle(low=1995.0, high=2035.0)
        result = evaluate_signal_outcome(
            signal, candle, candle_time=datetime(2026, 1, 1, 11, 0), expiry_hours=48
        )
        assert result == OutcomeAction.CLOSED_TP

    def test_long_sl_wins_when_both_hit_same_candle(self):
        """Matches BacktestEngine.check_and_close_trades: SL checked before TP."""
        signal = OpenSignalLike(
            id=1, direction="LONG", entry_price=2000.0,
            stop_loss=1990.0, take_profit=2030.0,
            timestamp=datetime(2026, 1, 1, 10, 0),
        )
        candle = make_candle(low=1985.0, high=2035.0)
        result = evaluate_signal_outcome(
            signal, candle, candle_time=datetime(2026, 1, 1, 11, 0), expiry_hours=48
        )
        assert result == OutcomeAction.CLOSED_SL

    def test_short_hits_stop_loss(self):
        signal = OpenSignalLike(
            id=1, direction="SHORT", entry_price=2000.0,
            stop_loss=2010.0, take_profit=1970.0,
            timestamp=datetime(2026, 1, 1, 10, 0),
        )
        candle = make_candle(low=1990.0, high=2015.0)
        result = evaluate_signal_outcome(
            signal, candle, candle_time=datetime(2026, 1, 1, 11, 0), expiry_hours=48
        )
        assert result == OutcomeAction.CLOSED_SL

    def test_short_hits_take_profit(self):
        signal = OpenSignalLike(
            id=1, direction="SHORT", entry_price=2000.0,
            stop_loss=2010.0, take_profit=1970.0,
            timestamp=datetime(2026, 1, 1, 10, 0),
        )
        candle = make_candle(low=1965.0, high=2005.0)
        result = evaluate_signal_outcome(
            signal, candle, candle_time=datetime(2026, 1, 1, 11, 0), expiry_hours=48
        )
        assert result == OutcomeAction.CLOSED_TP

    def test_no_hit_and_not_expired_returns_none(self):
        signal = OpenSignalLike(
            id=1, direction="LONG", entry_price=2000.0,
            stop_loss=1990.0, take_profit=2030.0,
            timestamp=datetime(2026, 1, 1, 10, 0),
        )
        candle = make_candle(low=1998.0, high=2005.0)
        result = evaluate_signal_outcome(
            signal, candle, candle_time=datetime(2026, 1, 1, 11, 0), expiry_hours=48
        )
        assert result == OutcomeAction.NONE

    def test_expires_after_max_holding_time(self):
        signal = OpenSignalLike(
            id=1, direction="LONG", entry_price=2000.0,
            stop_loss=1990.0, take_profit=2030.0,
            timestamp=datetime(2026, 1, 1, 10, 0),
        )
        candle = make_candle(low=1998.0, high=2005.0)
        candle_time = datetime(2026, 1, 1, 10, 0) + timedelta(hours=49)
        result = evaluate_signal_outcome(
            signal, candle, candle_time=candle_time, expiry_hours=48
        )
        assert result == OutcomeAction.EXPIRED

    def test_ignores_candle_at_or_before_entry_time(self):
        """Never check a signal against its own entry candle."""
        signal = OpenSignalLike(
            id=1, direction="LONG", entry_price=2000.0,
            stop_loss=1990.0, take_profit=2030.0,
            timestamp=datetime(2026, 1, 1, 10, 0),
        )
        candle = make_candle(low=1000.0, high=3000.0)  # would hit both if checked
        result = evaluate_signal_outcome(
            signal, candle, candle_time=datetime(2026, 1, 1, 10, 0), expiry_hours=48
        )
        assert result == OutcomeAction.NONE

"""Tests for signal outcome decision logic."""
import sys
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import MagicMock

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


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Base, Signal, SignalDirection, SignalStatus
from database.signal_repository import SignalRepository
from signals.outcome_tracker import SignalOutcomeTracker


@pytest.fixture
def db_url(tmp_path):
    return f"sqlite:///{tmp_path / 'tracker_test.db'}"


@pytest.fixture
def session_for(db_url):
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    sess = SessionLocal()
    yield sess
    sess.close()


def make_signal(session, direction, entry, sl, tp, timestamp, timeframe="1h", symbol="XAUUSD"):
    repo = SignalRepository(session)
    return repo.create(Signal(
        timestamp=timestamp, symbol=symbol, timeframe=timeframe,
        strategy_name="Test", direction=direction,
        entry_price=entry, stop_loss=sl, take_profit=tp,
        confidence=0.8, risk_pips=abs(entry - sl) * 10,
        reward_pips=abs(tp - entry) * 10, risk_reward_ratio=2.0,
        status=SignalStatus.PENDING,
    ))


class TestSignalOutcomeTracker:
    def test_closes_signal_that_hits_take_profit(self, db_url, session_for):
        signal = make_signal(
            session_for, SignalDirection.LONG, entry=2000.0, sl=1990.0, tp=2030.0,
            timestamp=datetime(2026, 1, 1, 10, 0),
        )

        tracker = SignalOutcomeTracker(
            database_url=db_url, symbol="XAUUSD", timeframe="1h", expiry_hours=48,
        )
        candle = pd.Series({'open': 2020.0, 'high': 2035.0, 'low': 2015.0, 'close': 2032.0})
        tracker.check_candle(candle, candle_time=datetime(2026, 1, 1, 11, 0))

        # The tracker writes via its own DatabaseManager session; expire this
        # session's identity map so it re-reads fresh state from the DB
        # instead of returning the stale in-memory object from make_signal().
        session_for.expire_all()
        repo = SignalRepository(session_for)
        refreshed = repo.get_by_id(signal.id)
        assert refreshed.status == SignalStatus.CLOSED_TP
        assert refreshed.actual_exit == 2030.0

    def test_leaves_unresolved_signal_open(self, db_url, session_for):
        signal = make_signal(
            session_for, SignalDirection.LONG, entry=2000.0, sl=1990.0, tp=2030.0,
            timestamp=datetime(2026, 1, 1, 10, 0),
        )

        tracker = SignalOutcomeTracker(
            database_url=db_url, symbol="XAUUSD", timeframe="1h", expiry_hours=48,
        )
        candle = pd.Series({'open': 2001.0, 'high': 2005.0, 'low': 1999.0, 'close': 2002.0})
        tracker.check_candle(candle, candle_time=datetime(2026, 1, 1, 11, 0))

        # The tracker writes via its own DatabaseManager session; expire this
        # session's identity map so it re-reads fresh state from the DB
        # instead of returning the stale in-memory object from make_signal().
        session_for.expire_all()
        repo = SignalRepository(session_for)
        refreshed = repo.get_by_id(signal.id)
        assert refreshed.status == SignalStatus.PENDING

    def test_expires_stale_signal(self, db_url, session_for):
        signal = make_signal(
            session_for, SignalDirection.LONG, entry=2000.0, sl=1990.0, tp=2030.0,
            timestamp=datetime(2026, 1, 1, 10, 0),
        )

        tracker = SignalOutcomeTracker(
            database_url=db_url, symbol="XAUUSD", timeframe="1h", expiry_hours=1,
        )
        candle = pd.Series({'open': 2001.0, 'high': 2005.0, 'low': 1999.0, 'close': 2002.0})
        tracker.check_candle(candle, candle_time=datetime(2026, 1, 1, 12, 0))

        # The tracker writes via its own DatabaseManager session; expire this
        # session's identity map so it re-reads fresh state from the DB
        # instead of returning the stale in-memory object from make_signal().
        session_for.expire_all()
        repo = SignalRepository(session_for)
        refreshed = repo.get_by_id(signal.id)
        assert refreshed.status == SignalStatus.CANCELLED
        assert "[expired" in refreshed.notes

    def test_only_checks_matching_symbol_and_timeframe(self, db_url, session_for):
        other_tf_signal = make_signal(
            session_for, SignalDirection.LONG, entry=2000.0, sl=1990.0, tp=2030.0,
            timestamp=datetime(2026, 1, 1, 10, 0), timeframe="4h",
        )

        tracker = SignalOutcomeTracker(
            database_url=db_url, symbol="XAUUSD", timeframe="1h", expiry_hours=48,
        )
        candle = pd.Series({'open': 2020.0, 'high': 2035.0, 'low': 2015.0, 'close': 2032.0})
        tracker.check_candle(candle, candle_time=datetime(2026, 1, 1, 11, 0))

        # The tracker writes via its own DatabaseManager session; expire this
        # session's identity map so it re-reads fresh state from the DB
        # instead of returning the stale in-memory object from make_signal().
        session_for.expire_all()
        repo = SignalRepository(session_for)
        refreshed = repo.get_by_id(other_tf_signal.id)
        assert refreshed.status == SignalStatus.PENDING  # untouched, different timeframe


class TestMatchesBacktestEngine:
    """
    Divergence check: replay the same signal + candle sequence through both
    SignalOutcomeTracker and BacktestEngine.check_and_close_trades(), and
    assert they reach the same conclusion. Catches the two implementations
    drifting apart even though they're meant to encode identical logic.
    """

    def test_multi_candle_replay_matches_backtest_engine(self, db_url, session_for):
        from backtesting.engine import BacktestEngine, Trade, TradeDirection, TradeStatus

        entry_time = datetime(2026, 1, 1, 10, 0)
        signal = make_signal(
            session_for, SignalDirection.LONG, entry=2000.0, sl=1990.0, tp=2030.0,
            timestamp=entry_time,
        )

        candles = [
            (datetime(2026, 1, 1, 11, 0), pd.Series({'open': 2001, 'high': 2010, 'low': 1995, 'close': 2005})),
            (datetime(2026, 1, 1, 12, 0), pd.Series({'open': 2005, 'high': 2015, 'low': 2000, 'close': 2010})),
            (datetime(2026, 1, 1, 13, 0), pd.Series({'open': 2010, 'high': 2032, 'low': 2008, 'close': 2029})),
        ]

        tracker = SignalOutcomeTracker(
            database_url=db_url, symbol="XAUUSD", timeframe="1h", expiry_hours=48,
        )
        for candle_time, candle in candles:
            tracker.check_candle(candle, candle_time=candle_time)

        # The tracker writes via its own DatabaseManager session; expire this
        # session's identity map so it re-reads fresh state from the DB
        # instead of returning the stale in-memory object from make_signal().
        session_for.expire_all()
        repo = SignalRepository(session_for)
        tracker_result = repo.get_by_id(signal.id)

        # Replay the identical sequence through the trusted backtester.
        engine = BacktestEngine(initial_balance=10000, position_size_pct=2.0, slippage=0.0)
        trade = Trade(
            id=1, entry_time=entry_time, entry_price=2000.0,
            direction=TradeDirection.LONG, stop_loss=1990.0, take_profit=2030.0,
        )
        engine.open_trades = [trade]
        engine.trades = [trade]
        for candle_time, candle in candles:
            engine.check_and_close_trades(candle, candle_time)

        assert tracker_result.status.value == trade.status.value
        if trade.status != TradeStatus.OPEN:
            assert tracker_result.actual_exit == trade.exit_price


class TestCloseNotifications:
    """
    Previously check_candle() closed a signal with zero notification —
    only signal creation sent a Telegram message. A resolved trade could
    sit "closed" in the database with no way to tell from Telegram.
    """

    def test_notifies_on_take_profit(self, db_url, session_for):
        signal = make_signal(
            session_for, SignalDirection.LONG, entry=2000.0, sl=1990.0, tp=2030.0,
            timestamp=datetime(2026, 1, 1, 10, 0),
        )
        telegram = MagicMock()
        tracker = SignalOutcomeTracker(
            database_url=db_url, symbol="XAUUSD", timeframe="1h", expiry_hours=48,
            telegram_subscriber=telegram,
        )
        candle = pd.Series({'open': 2020.0, 'high': 2035.0, 'low': 2015.0, 'close': 2032.0})
        tracker.check_candle(candle, candle_time=datetime(2026, 1, 1, 11, 0))

        telegram.send_close_notification.assert_called_once()
        kwargs = telegram.send_close_notification.call_args.kwargs
        assert kwargs['outcome'] == 'closed_tp'
        assert kwargs['exit_price'] == 2030.0
        assert kwargs['r_multiple'] == pytest.approx(3.0)  # 300 pips / 100 pips risk

    def test_notifies_on_stop_loss(self, db_url, session_for):
        make_signal(
            session_for, SignalDirection.LONG, entry=2000.0, sl=1990.0, tp=2030.0,
            timestamp=datetime(2026, 1, 1, 10, 0),
        )
        telegram = MagicMock()
        tracker = SignalOutcomeTracker(
            database_url=db_url, symbol="XAUUSD", timeframe="1h", expiry_hours=48,
            telegram_subscriber=telegram,
        )
        candle = pd.Series({'open': 1995.0, 'high': 1998.0, 'low': 1985.0, 'close': 1988.0})
        tracker.check_candle(candle, candle_time=datetime(2026, 1, 1, 11, 0))

        telegram.send_close_notification.assert_called_once()
        kwargs = telegram.send_close_notification.call_args.kwargs
        assert kwargs['outcome'] == 'closed_sl'
        assert kwargs['r_multiple'] == pytest.approx(-1.0)

    def test_notifies_on_expiry(self, db_url, session_for):
        make_signal(
            session_for, SignalDirection.LONG, entry=2000.0, sl=1990.0, tp=2030.0,
            timestamp=datetime(2026, 1, 1, 10, 0),
        )
        telegram = MagicMock()
        tracker = SignalOutcomeTracker(
            database_url=db_url, symbol="XAUUSD", timeframe="1h", expiry_hours=1,
            telegram_subscriber=telegram,
        )
        candle = pd.Series({'open': 2001.0, 'high': 2005.0, 'low': 1999.0, 'close': 2002.0})
        tracker.check_candle(candle, candle_time=datetime(2026, 1, 1, 12, 0))

        telegram.send_close_notification.assert_called_once()
        assert telegram.send_close_notification.call_args.kwargs['outcome'] == 'expired'

    def test_does_not_notify_unresolved_signal(self, db_url, session_for):
        make_signal(
            session_for, SignalDirection.LONG, entry=2000.0, sl=1990.0, tp=2030.0,
            timestamp=datetime(2026, 1, 1, 10, 0),
        )
        telegram = MagicMock()
        tracker = SignalOutcomeTracker(
            database_url=db_url, symbol="XAUUSD", timeframe="1h", expiry_hours=48,
            telegram_subscriber=telegram,
        )
        candle = pd.Series({'open': 2001.0, 'high': 2005.0, 'low': 1999.0, 'close': 2002.0})
        tracker.check_candle(candle, candle_time=datetime(2026, 1, 1, 11, 0))

        telegram.send_close_notification.assert_not_called()

    def test_no_telegram_subscriber_does_not_crash(self, db_url, session_for):
        """telegram_subscriber is optional — outcome tracking must work without it."""
        make_signal(
            session_for, SignalDirection.LONG, entry=2000.0, sl=1990.0, tp=2030.0,
            timestamp=datetime(2026, 1, 1, 10, 0),
        )
        tracker = SignalOutcomeTracker(
            database_url=db_url, symbol="XAUUSD", timeframe="1h", expiry_hours=48,
        )
        candle = pd.Series({'open': 2020.0, 'high': 2035.0, 'low': 2015.0, 'close': 2032.0})
        tracker.check_candle(candle, candle_time=datetime(2026, 1, 1, 11, 0))  # must not raise

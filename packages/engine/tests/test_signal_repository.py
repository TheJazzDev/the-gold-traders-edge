"""Tests for SignalRepository, using a temporary on-disk SQLite database."""
import sys
from pathlib import Path
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from database.models import Base, Signal, SignalDirection, SignalStatus
from database.signal_repository import SignalRepository


@pytest.fixture
def session(tmp_path):
    db_path = tmp_path / "test_signals.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    sess = SessionLocal()
    yield sess
    sess.close()


@pytest.fixture
def repo(session):
    return SignalRepository(session)


def make_signal(symbol="XAUUSD", timeframe="1h", status=SignalStatus.PENDING, direction=SignalDirection.LONG):
    return Signal(
        timestamp=datetime(2026, 1, 1, 10, 0),
        symbol=symbol,
        timeframe=timeframe,
        strategy_name="Test Strategy",
        direction=direction,
        entry_price=2000.0,
        stop_loss=1990.0,
        take_profit=2030.0,
        confidence=0.8,
        risk_pips=100.0,
        reward_pips=300.0,
        risk_reward_ratio=3.0,
        status=status,
    )


class TestGetOpenSignals:
    def test_returns_pending_and_active(self, repo):
        repo.create(make_signal(status=SignalStatus.PENDING))
        repo.create(make_signal(status=SignalStatus.ACTIVE))
        repo.create(make_signal(status=SignalStatus.CLOSED_TP))

        open_signals = repo.get_open_signals()

        assert len(open_signals) == 2
        assert {s.status for s in open_signals} == {SignalStatus.PENDING, SignalStatus.ACTIVE}

    def test_filters_by_symbol_and_timeframe(self, repo):
        repo.create(make_signal(symbol="XAUUSD", timeframe="1h"))
        repo.create(make_signal(symbol="XAUUSD", timeframe="4h"))
        repo.create(make_signal(symbol="XAGUSD", timeframe="1h"))

        result = repo.get_open_signals(symbol="XAUUSD", timeframe="1h")

        assert len(result) == 1
        assert result[0].symbol == "XAUUSD"
        assert result[0].timeframe == "1h"


class TestCloseOpenSignal:
    def test_closes_at_take_profit_and_computes_pnl_pips_from_entry_price(self, repo):
        saved = repo.create(make_signal(direction=SignalDirection.LONG))

        updated = repo.close_open_signal(
            signal_id=saved.id,
            exit_price=2030.0,
            status=SignalStatus.CLOSED_TP,
            closed_at=datetime(2026, 1, 1, 14, 0),
        )

        assert updated.status == SignalStatus.CLOSED_TP
        assert updated.actual_exit == 2030.0
        assert updated.pnl_pips == pytest.approx((2030.0 - 2000.0) * 10)
        assert updated.pnl is None  # no dollar P&L fabricated
        assert updated.closed_at == datetime(2026, 1, 1, 14, 0)

    def test_closes_short_correctly(self, repo):
        saved = repo.create(make_signal(direction=SignalDirection.SHORT))
        saved.entry_price = 2000.0
        repo.update(saved)

        updated = repo.close_open_signal(
            signal_id=saved.id,
            exit_price=1970.0,
            status=SignalStatus.CLOSED_TP,
            closed_at=datetime(2026, 1, 1, 14, 0),
        )

        assert updated.pnl_pips == pytest.approx((2000.0 - 1970.0) * 10)

    def test_expiry_has_no_exit_price_and_appends_note(self, repo):
        saved = repo.create(make_signal())
        saved.notes = "original note"
        repo.update(saved)

        updated = repo.close_open_signal(
            signal_id=saved.id,
            exit_price=None,
            status=SignalStatus.CANCELLED,
            closed_at=datetime(2026, 1, 2, 10, 0),
            note_suffix=" [expired after 48h with no resolution]",
        )

        assert updated.status == SignalStatus.CANCELLED
        assert updated.actual_exit is None
        assert updated.pnl_pips is None
        assert updated.notes == "original note [expired after 48h with no resolution]"

    def test_returns_none_for_unknown_id(self, repo):
        assert repo.close_open_signal(
            signal_id=99999, exit_price=2000.0,
            status=SignalStatus.CLOSED_TP, closed_at=datetime.utcnow(),
        ) is None

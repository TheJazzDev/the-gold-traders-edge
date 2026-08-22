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
        timestamp=datetime.utcnow() - timedelta(hours=1),
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


class TestGetPerformanceStats:
    def test_counts_and_rates_by_status(self, repo):
        # 2 TP hits, 1 SL hit, 1 expired, 1 still open
        tp1 = repo.create(make_signal(status=SignalStatus.PENDING))
        tp1.risk_pips, tp1.pnl_pips = 100.0, 300.0
        repo.update(tp1)
        repo.close_open_signal(tp1.id, 2030.0, SignalStatus.CLOSED_TP, datetime(2026, 1, 1, 12, 0))

        tp2 = repo.create(make_signal(status=SignalStatus.PENDING))
        tp2.risk_pips, tp2.pnl_pips = 100.0, 300.0
        repo.update(tp2)
        repo.close_open_signal(tp2.id, 2030.0, SignalStatus.CLOSED_TP, datetime(2026, 1, 1, 12, 0))

        sl1 = repo.create(make_signal(status=SignalStatus.PENDING))
        sl1.risk_pips, sl1.pnl_pips = 100.0, -100.0
        repo.update(sl1)
        repo.close_open_signal(sl1.id, 1990.0, SignalStatus.CLOSED_SL, datetime(2026, 1, 1, 12, 0))

        expired1 = repo.create(make_signal(status=SignalStatus.PENDING))
        repo.close_open_signal(
            expired1.id, None, SignalStatus.CANCELLED, datetime(2026, 1, 1, 12, 0),
            note_suffix=" [expired after 48h with no resolution]",
        )

        repo.create(make_signal(status=SignalStatus.PENDING))  # still open

        stats = repo.get_performance_stats(days=30)

        assert stats['total_signals'] == 5
        assert stats['tp_hits'] == 2
        assert stats['sl_hits'] == 1
        assert stats['expired'] == 1
        assert stats['still_open'] == 1
        assert stats['closed_manual'] == 0
        assert stats['win_rate'] == pytest.approx(2 / 3 * 100)  # 2 TP out of 3 resolved
        assert stats['avg_r_multiple'] == pytest.approx((3.0 + 3.0 + (-1.0)) / 3)
        assert stats['net_r_multiple'] == pytest.approx(3.0 + 3.0 + (-1.0))

    def test_empty_period_returns_zeroed_stats(self, repo):
        stats = repo.get_performance_stats(days=30)
        assert stats['total_signals'] == 0
        assert stats['win_rate'] == 0.0
        assert stats['avg_r_multiple'] == 0.0

    def test_filters_by_symbol_and_timeframe(self, repo):
        repo.create(make_signal(symbol="XAUUSD", timeframe="1h", status=SignalStatus.PENDING))
        repo.create(make_signal(symbol="XAUUSD", timeframe="4h", status=SignalStatus.PENDING))

        stats = repo.get_performance_stats(days=30, symbol="XAUUSD", timeframe="1h")
        assert stats['total_signals'] == 1

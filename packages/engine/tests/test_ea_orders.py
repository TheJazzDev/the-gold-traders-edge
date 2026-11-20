"""The EA must get each signal at most once, only while trading is LIVE, and
never a stale, closed, signals-only or already-handled one. A wrong answer
here is a real order."""
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from database.broker_fill import BrokerFill, ensure_broker_fills_table
from database.models import Base, Signal, SignalDirection, SignalStatus
from database.settings_repository import SettingsRepository
from trading import ea_orders
from trading.trading_switch import TradingMode

NOW = datetime(2026, 11, 20, 12, 0, 0)


@pytest.fixture
def session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'ea.db'}")
    Base.metadata.create_all(engine)
    ensure_broker_fills_table(engine)
    db = sessionmaker(bind=engine)()
    yield db
    db.close()


def _signal(session, symbol='XAUUSD', status=SignalStatus.PENDING, age_minutes=1, **extra):
    row = Signal(
        timestamp=NOW, symbol=symbol, timeframe='1h', strategy_name='order_block_retest',
        direction=SignalDirection.LONG, entry_price=4012.5, stop_loss=3969.5,
        take_profit=4098.5, status=status, created_at=NOW - timedelta(minutes=age_minutes),
        reference_id=extra.pop('reference_id', None), **extra,
    )
    session.add(row)
    session.commit()
    return row


def _fill(session, signal_id, ticket=555):
    return ea_orders.record_fill(
        session, signal_id, ticket=ticket, lots=0.05, entry_price=4010.1, stop_loss=3967.1,
        take_profit=4096.1, broker_symbol='XAUUSD', account='49910090', now=NOW,
    )


def test_a_new_signal_is_offered_when_live(session):
    row = _signal(session, reference_id='OBR-1120-01')

    orders = ea_orders.pending_orders(session, TradingMode.LIVE, NOW)

    assert [(o.signal_id, o.symbol, o.direction, o.reference_id) for o in orders] == [
        (row.id, 'XAUUSD', 'LONG', 'OBR-1120-01')]


@pytest.mark.parametrize('mode', [TradingMode.OFF, TradingMode.DRY_RUN])
def test_nothing_is_offered_unless_live(session, mode):
    _signal(session)

    assert ea_orders.pending_orders(session, mode, NOW) == []


def test_a_stale_signal_is_not_offered(session):
    _signal(session, age_minutes=16)

    assert ea_orders.pending_orders(session, TradingMode.LIVE, NOW) == []


def test_a_signals_only_symbol_is_not_offered(session):
    _signal(session, symbol='USDJPY')

    assert ea_orders.pending_orders(session, TradingMode.LIVE, NOW) == []


@pytest.mark.parametrize('status', [SignalStatus.ACTIVE, SignalStatus.CLOSED_SL,
                                    SignalStatus.CLOSED_TP, SignalStatus.CANCELLED])
def test_only_pending_signals_are_offered(session, status):
    _signal(session, status=status)

    assert ea_orders.pending_orders(session, TradingMode.LIVE, NOW) == []


def test_a_filled_signal_is_never_offered_again(session):
    row = _signal(session)

    assert _fill(session, row.id) is True

    assert ea_orders.pending_orders(session, TradingMode.LIVE, NOW) == []
    session.refresh(row)
    assert (row.status, row.mt5_ticket, row.actual_entry) == (SignalStatus.ACTIVE, 555, 4010.1)


def test_a_repeated_fill_report_changes_nothing(session):
    row = _signal(session)
    _fill(session, row.id, ticket=555)

    assert _fill(session, row.id, ticket=999) is True

    assert [f.ticket for f in session.query(BrokerFill).all()] == [555]


def test_a_ticket_too_big_for_the_column_goes_in_the_notes(session):
    row = _signal(session)

    _fill(session, row.id, ticket=5_000_000_000)

    session.refresh(row)
    assert row.mt5_ticket is None and '5000000000' in row.notes
    assert session.query(BrokerFill).one().ticket == 5_000_000_000


def test_a_fill_does_not_reopen_a_signal_the_tracker_closed(session):
    row = _signal(session, status=SignalStatus.CLOSED_SL)

    _fill(session, row.id)

    session.refresh(row)
    assert row.status is SignalStatus.CLOSED_SL


def test_a_rejected_signal_is_not_offered_again_and_stays_open(session):
    row = _signal(session)

    assert ea_orders.record_reject(session, row.id, 'lot below minimum') is True

    assert ea_orders.pending_orders(session, TradingMode.LIVE, NOW) == []
    session.refresh(row)
    assert row.status is SignalStatus.PENDING
    assert row.error_message == 'EA: lot below minimum'


def test_a_close_is_kept_on_the_fill_not_the_signal(session):
    row = _signal(session)
    _fill(session, row.id)

    assert ea_orders.record_close(session, row.id, exit_price=3967.1, profit=-21.5,
                                  close_reason='sl', now=NOW) is True
    ea_orders.record_close(session, row.id, exit_price=1.0, profit=99.0,
                           close_reason='tp', now=NOW)  # a repeat must not overwrite

    fill = session.query(BrokerFill).one()
    assert (fill.exit_price, fill.profit, fill.close_reason) == (3967.1, -21.5, 'sl')
    session.refresh(row)
    assert row.status is SignalStatus.ACTIVE and row.actual_exit is None and row.pnl is None


def test_reports_for_unknown_signals_are_refused(session):
    assert _fill(session, 9999) is False
    assert ea_orders.record_reject(session, 9999, 'x') is False
    assert ea_orders.record_close(session, 9999, 1.0, 1.0, 'sl', NOW) is False


def test_poll_text_is_one_line_per_order(session):
    row = _signal(session, reference_id='OBR-1120-01')
    orders = ea_orders.pending_orders(session, TradingMode.LIVE, NOW)

    text = ea_orders.format_poll_response(TradingMode.LIVE, 0.0025, orders)

    assert text == (f"MODE|live\nRISK|0.0025\n"
                    f"ORDER|{row.id}|XAUUSD|LONG|4012.5|3969.5|4098.5|OBR-1120-01\n")


def test_no_orders_go_out_without_a_trusted_risk(session):
    _signal(session)
    orders = ea_orders.pending_orders(session, TradingMode.LIVE, NOW)

    assert ea_orders.format_poll_response(TradingMode.LIVE, None, orders) == "MODE|live\nRISK|0\n"


@pytest.mark.parametrize('raw,expected', [(None, 0.0025), ('0.005', 0.005), ('0.05', None),
                                          ('0', None), ('abc', None)])
def test_risk_setting_is_bounded(monkeypatch, raw, expected):
    if raw is None:
        monkeypatch.delenv('MAX_RISK_PER_TRADE', raising=False)
    else:
        monkeypatch.setenv('MAX_RISK_PER_TRADE', raw)

    assert ea_orders.risk_per_trade() == expected


def test_trading_mode_defaults_to_off_and_follows_the_settings(session):
    assert ea_orders.read_trading_mode(session) is TradingMode.OFF

    repo = SettingsRepository(session)
    repo.initialize_defaults()
    repo.set('auto_trading_enabled', True)
    repo.set('dry_run_mode', False)

    assert ea_orders.read_trading_mode(session) is TradingMode.LIVE

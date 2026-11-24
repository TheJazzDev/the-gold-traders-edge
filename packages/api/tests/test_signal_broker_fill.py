"""A signal's paper outcome and the broker's real fill are shown side by side,
never merged: the demo run exists to compare them."""
import sys
from datetime import datetime
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import get_db
from src.routes.signals import router as signals_router  # puts the engine on sys.path
from src.broker_result import broker_r_multiple

from database.broker_fill import BrokerFill
from database.models import Base, Signal, SignalDirection, SignalStatus


@pytest.fixture
def db():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def client(db):
    app = FastAPI()
    app.include_router(signals_router)
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)


def _signal(db, direction=SignalDirection.LONG):
    row = Signal(timestamp=datetime.utcnow(), symbol='XAUUSD', timeframe='1h',
                 strategy_name='order_block_retest', direction=direction,
                 entry_price=3653.6, stop_loss=3609.44, take_profit=3741.92,
                 confidence=0.7, status=SignalStatus.CLOSED_SL, actual_exit=3609.44,
                 pnl_pips=-441.6, risk_pips=441.6, created_at=datetime.utcnow())
    db.add(row)
    db.commit()
    return row.id


def _fill(db, signal_id, **changes):
    values = dict(signal_id=signal_id, ticket=1499653165, account='49910090',
                  broker_symbol='XAUUSD', lots=0.01, entry_price=3656.49, stop_loss=3612.35,
                  take_profit=3744.83, opened_at=datetime(2026, 11, 23, 18, 15, 27),
                  exit_price=3612.31, profit=-44.18, close_reason='sl',
                  closed_at=datetime(2026, 11, 24, 8, 27, 12))
    values.update(changes)
    db.add(BrokerFill(**values))
    db.commit()


def test_signal_detail_carries_the_broker_fill(client, db):
    signal_id = _signal(db)
    _fill(db, signal_id)

    body = client.get(f'/v1/signals/{signal_id}').json()

    assert body['actual_exit'] == 3609.44  # the paper record is untouched
    broker = body['broker']
    assert broker['ticket'] == 1499653165
    assert broker['lots'] == 0.01
    assert broker['entry_price'] == 3656.49
    assert broker['exit_price'] == 3612.31
    assert broker['profit'] == -44.18
    assert broker['close_reason'] == 'sl'
    assert broker['r_multiple'] == pytest.approx(-1.0009, abs=1e-4)


def test_signal_without_an_order_has_no_broker_block(client, db):
    signal_id = _signal(db)

    assert client.get(f'/v1/signals/{signal_id}').json()['broker'] is None


def test_signal_list_carries_broker_fills(client, db):
    filled, unfilled = _signal(db), _signal(db)
    _fill(db, filled)

    by_id = {row['id']: row for row in client.get('/v1/signals/').json()['signals']}

    assert by_id[filled]['broker']['profit'] == -44.18
    assert by_id[unfilled]['broker'] is None


def test_open_position_has_no_result_yet(client, db):
    signal_id = _signal(db)
    _fill(db, signal_id, exit_price=None, profit=None, close_reason=None, closed_at=None)

    broker = client.get(f'/v1/signals/{signal_id}').json()['broker']

    assert broker['exit_price'] is None
    assert broker['r_multiple'] is None


def test_broker_r_for_a_short_win():
    assert broker_r_multiple('SHORT', entry=1.1000, stop=1.1020, exit_price=1.0960) == pytest.approx(2.0)


def test_broker_r_is_unknown_without_a_stop_distance():
    assert broker_r_multiple('LONG', entry=1.1, stop=1.1, exit_price=1.2) is None

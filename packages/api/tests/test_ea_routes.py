"""The EA endpoints hand out real orders, so they must refuse anyone without
the EA key and give each signal out only once."""
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
from src.ea_auth import EA_KEY_ENV
from src.routes import ea as ea_routes
from src.routes.ea import router as ea_router

from database.models import Base, Signal, SignalDirection, SignalStatus
from database.settings_repository import SettingsRepository

KEY = {'X-EA-Key': 'right'}
FILL = {'ticket': 555, 'lots': 0.05, 'entry_price': 4010.1, 'stop_loss': 3967.1,
        'take_profit': 4096.1, 'broker_symbol': 'XAUUSD', 'account': '49910090'}


@pytest.fixture
def db(monkeypatch):
    monkeypatch.setenv(EA_KEY_ENV, 'right')
    monkeypatch.delenv('MAX_RISK_PER_TRADE', raising=False)
    ea_routes._claims.clear()
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def client(db):
    app = FastAPI()
    app.include_router(ea_router)
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)


def _go_live(db):
    repo = SettingsRepository(db)
    repo.initialize_defaults()
    repo.set('auto_trading_enabled', True)
    repo.set('dry_run_mode', False)


def _signal(db):
    row = Signal(timestamp=datetime.utcnow(), symbol='XAUUSD', timeframe='1h',
                 strategy_name='order_block_retest', direction=SignalDirection.LONG,
                 entry_price=4012.5, stop_loss=3969.5, take_profit=4098.5,
                 status=SignalStatus.PENDING, created_at=datetime.utcnow())
    db.add(row)
    db.commit()
    return row.id


@pytest.mark.parametrize('method,path', [
    ('post', '/v1/ea/poll'), ('post', '/v1/ea/orders/1/fill'),
    ('post', '/v1/ea/orders/1/reject'), ('post', '/v1/ea/orders/1/close'),
    ('get', '/v1/ea/status'),
])
def test_every_route_needs_the_ea_key(client, method, path):
    assert getattr(client, method)(path).status_code == 401
    assert getattr(client, method)(path, headers={'X-EA-Key': 'wrong'}).status_code == 401


def test_no_configured_key_refuses_everything(client, monkeypatch):
    monkeypatch.delenv(EA_KEY_ENV)
    assert client.post('/v1/ea/poll', json={}, headers=KEY).status_code == 503


def test_default_settings_give_no_orders(client, db):
    _signal(db)

    response = client.post('/v1/ea/poll', json={}, headers=KEY)

    assert response.text == 'MODE|off\nRISK|0.0025\n'


def test_an_order_is_given_until_it_is_reported_filled(client, db):
    _go_live(db)
    signal_id = _signal(db)
    expected = f'MODE|live\nRISK|0.0025\nORDER|{signal_id}|XAUUSD|LONG|4012.5|3969.5|4098.5|\n'

    assert client.post('/v1/ea/poll', json={'balance': 10000}, headers=KEY).text == expected
    assert client.post(f'/v1/ea/orders/{signal_id}/fill', json=FILL, headers=KEY).json() == {'ok': True}

    assert client.post('/v1/ea/poll', json={}, headers=KEY).text == 'MODE|live\nRISK|0.0025\n'


def test_only_the_first_terminal_to_ask_is_given_an_order(client, db):
    _go_live(db)
    signal_id = _signal(db)

    laptop = client.post('/v1/ea/poll', json={}, headers=KEY).text
    server = client.post('/v1/ea/poll', json={'terminal': 'railway'}, headers=KEY).text
    laptop_again = client.post('/v1/ea/poll', json={}, headers=KEY).text

    assert f'ORDER|{signal_id}|' in laptop and f'ORDER|{signal_id}|' in laptop_again
    assert server == 'MODE|live\nRISK|0.0025\n'


def test_a_rejected_order_is_not_given_again(client, db):
    _go_live(db)
    signal_id = _signal(db)

    client.post(f'/v1/ea/orders/{signal_id}/reject', json={'reason': 'lot below minimum'}, headers=KEY)

    assert 'ORDER' not in client.post('/v1/ea/poll', json={}, headers=KEY).text


def test_status_shows_the_last_poll_and_the_fill_with_its_close(client, db):
    _go_live(db)
    signal_id = _signal(db)
    client.post('/v1/ea/poll', json={'account': '49910090', 'balance': 10000}, headers=KEY)
    client.post(f'/v1/ea/orders/{signal_id}/fill', json=FILL, headers=KEY)
    client.post(f'/v1/ea/orders/{signal_id}/close',
                json={'exit_price': 3967.1, 'profit': -21.5, 'close_reason': 'sl'}, headers=KEY)

    body = client.get('/v1/ea/status', headers=KEY).json()

    assert body['mode'] == 'live'
    assert body['last_poll']['balance'] == 10000
    assert [(f['ticket'], f['profit'], f['close_reason']) for f in body['fills']] == [(555, -21.5, 'sl')]


def test_reports_for_unknown_signals_are_404(client):
    assert client.post('/v1/ea/orders/9999/fill', json=FILL, headers=KEY).status_code == 404
    assert client.post('/v1/ea/orders/9999/reject', json={'reason': 'x'}, headers=KEY).status_code == 404


def test_a_malformed_fill_is_refused(client, db):
    signal_id = _signal(db)
    bad = {**FILL, 'lots': 0}

    assert client.post(f'/v1/ea/orders/{signal_id}/fill', json=bad, headers=KEY).status_code == 422

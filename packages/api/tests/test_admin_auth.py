"""Every write on the API needs the admin key. The Controls password only
guards the web page, so without this anyone with the URL could change the
trading switches."""
import sys
from pathlib import Path

import pytest
from fastapi import Depends, FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.admin_auth import ADMIN_KEY_ENV, require_admin_key
from src.routes.settings import router as settings_router
from src.routes.signals import router as signals_router

WRITES = {'PUT', 'POST', 'PATCH', 'DELETE'}
ALL_ROUTERS = (settings_router, signals_router)


@pytest.fixture
def client():
    app = FastAPI()

    @app.put('/write', dependencies=[Depends(require_admin_key)])
    def write():
        return {'ok': True}

    return TestClient(app)


def test_no_key_is_refused(client, monkeypatch):
    monkeypatch.setenv(ADMIN_KEY_ENV, 'right')
    assert client.put('/write').status_code == 401


def test_wrong_key_is_refused(client, monkeypatch):
    monkeypatch.setenv(ADMIN_KEY_ENV, 'right')
    assert client.put('/write', headers={'X-Admin-Key': 'wrong'}).status_code == 401


def test_right_key_is_allowed(client, monkeypatch):
    monkeypatch.setenv(ADMIN_KEY_ENV, 'right')
    assert client.put('/write', headers={'X-Admin-Key': 'right'}).status_code == 200


@pytest.mark.parametrize('configured', [None, ''])
def test_an_unconfigured_server_refuses_every_write(client, monkeypatch, configured):
    if configured is None:
        monkeypatch.delenv(ADMIN_KEY_ENV, raising=False)
    else:
        monkeypatch.setenv(ADMIN_KEY_ENV, configured)
    assert client.put('/write', headers={'X-Admin-Key': ''}).status_code == 503


def test_every_write_route_requires_the_key():
    write_routes = [r for router in ALL_ROUTERS for r in router.routes
                    if isinstance(r, APIRoute) and r.methods & WRITES]
    assert len(write_routes) == 5
    for route in write_routes:
        guards = [d.call for d in route.dependant.dependencies]
        assert require_admin_key in guards, route.path

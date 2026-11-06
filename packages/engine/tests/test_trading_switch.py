"""Real orders need the env flag, auto_trading_enabled on and dry_run_mode
off, checked per signal. On 2026-11-06 production had ENABLE_AUTO_TRADING=true
and only a config error stopped orders; the dashboard switches did nothing."""
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from database.connection import DatabaseManager
from database.models import Base
from database.settings_repository import SettingsRepository
from signals.subscribers.mt5_subscriber import MT5Subscriber
from trading.trading_switch import TradingMode, make_trading_mode_reader, resolve_trading_mode


@pytest.mark.parametrize('auto,dry,expected', [
    (False, False, TradingMode.OFF),
    (False, True, TradingMode.OFF),
    (True, True, TradingMode.DRY_RUN),
    (True, False, TradingMode.LIVE),
])
def test_mode_comes_from_both_settings(auto, dry, expected):
    assert resolve_trading_mode(auto_trading_enabled=auto, dry_run_mode=dry) is expected


def _db(tmp_path, **settings):
    url = f"sqlite:///{tmp_path / 'switch.db'}"
    with DatabaseManager(url).session_scope() as session:
        Base.metadata.create_all(bind=session.get_bind())
        repo = SettingsRepository(session)
        repo.initialize_defaults()
        for key, value in settings.items():
            repo.set(key, value)
    return url


def test_default_settings_mean_off(tmp_path):
    assert make_trading_mode_reader(_db(tmp_path))() is TradingMode.OFF


def test_reader_sees_a_change_without_a_restart(tmp_path):
    url = _db(tmp_path, auto_trading_enabled=True)
    read = make_trading_mode_reader(url)
    assert read() is TradingMode.LIVE

    with DatabaseManager(url).session_scope() as session:
        SettingsRepository(session).set('auto_trading_enabled', False)

    assert read() is TradingMode.OFF


def test_unreadable_settings_mean_off(tmp_path):
    missing = f"sqlite:///{tmp_path / 'no-tables.db'}"

    assert make_trading_mode_reader(missing)() is TradingMode.OFF


def _subscriber(mode, **kwargs):
    connection = MagicMock()
    connection.get_account_info.return_value = {'balance': 1000.0, 'equity': 1000.0, 'free_margin': 1000.0}
    risk = MagicMock()
    risk.can_open_position.return_value = (True, '')
    sub = MT5Subscriber(connection=connection, config=MagicMock(), db_manager=MagicMock(),
                        risk_manager=risk, trading_mode=(lambda: mode), **kwargs)
    sub.position_calculator = MagicMock()
    sub.position_calculator.calculate_lot_size.return_value = 0.01
    sub.position_calculator.calculate_risk_amount.return_value = 5.0
    sub.trade_executor = MagicMock()
    sub.trade_executor.execute_signal.return_value = MagicMock(success=False, error_message='stub')
    return sub


def _signal():
    return MagicMock(symbol='EURUSD', direction='LONG', entry_price=1.1, stop_loss=1.09,
                     take_profit=1.12, confidence=0.6)


def test_off_places_no_order_and_touches_nothing():
    sub = _subscriber(TradingMode.OFF)

    assert sub._execute_signal(_signal()) is False
    sub.trade_executor.execute_signal.assert_not_called()
    sub.connection.get_account_info.assert_not_called()


def test_dry_run_setting_places_no_order():
    sub = _subscriber(TradingMode.DRY_RUN)

    assert sub._execute_signal(_signal()) is True
    sub.trade_executor.execute_signal.assert_not_called()


def test_live_places_the_order():
    sub = _subscriber(TradingMode.LIVE)

    sub._execute_signal(_signal())

    sub.trade_executor.execute_signal.assert_called_once()


def test_subscriber_is_off_unless_told_otherwise():
    sub = MT5Subscriber(connection=MagicMock(), config=MagicMock(), db_manager=MagicMock(),
                        risk_manager=MagicMock())
    sub.trade_executor = MagicMock()

    sub._execute_signal(_signal())

    sub.trade_executor.execute_signal.assert_not_called()

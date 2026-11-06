"""The MetaAPI order path, wired against a fake that keeps the installed
SDK's method signatures. No order had ever been placed when this was written:
calls were unawaited and passed arguments the SDK doesn't accept."""
import sys
import threading
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from database.connection import DatabaseManager
from database.models import Base, Signal as SignalRow, SignalDirection, SignalStatus
from signals.subscribers.mt5_subscriber import MT5Subscriber
from trading.async_bridge import AsyncBridge
from trading.broker_levels import align_levels_to_broker
from trading.metaapi_connection import MetaAPIConnection
from trading.mt5_config import MT5Config, MT5ConnectionType
from trading.position_calculator import PositionCalculator
from trading.risk_manager import RiskManager, get_shared_risk_manager
from trading.trade_executor import TradeExecutor
from trading.trading_switch import TradingMode


class FakeRpc:
    def __init__(self, ask=4025.0, bid=4024.5, position_id='5001', error=None):
        self.ask, self.bid, self.position_id, self.error = ask, bid, position_id, error
        self.orders = []
        self.positions = []

    async def get_account_information(self):
        return {'login': 1, 'balance': 10000.0, 'equity': 10000.0, 'freeMargin': 10000.0, 'leverage': 500}

    async def get_symbol_specification(self, symbol):
        size = 100 if symbol.startswith('XAU') else 100000
        return {'digits': 2 if symbol.startswith('XAU') else 5, 'contractSize': size,
                'minVolume': 0.01, 'maxVolume': 50.0, 'volumeStep': 0.01}

    async def get_symbol_price(self, symbol):
        return {'bid': self.bid, 'ask': self.ask}

    async def _order(self, side, symbol, volume, stop_loss=None, take_profit=None, options=None):
        if self.error:
            raise self.error
        self.orders.append(dict(side=side, symbol=symbol, volume=volume, stop_loss=stop_loss,
                                take_profit=take_profit, options=options))
        return {'numericCode': 10009, 'stringCode': 'TRADE_RETCODE_DONE', 'orderId': '1',
                'positionId': self.position_id}

    def create_market_buy_order(self, symbol, volume, stop_loss=None, take_profit=None, options=None):
        return self._order('buy', symbol, volume, stop_loss, take_profit, options)

    def create_market_sell_order(self, symbol, volume, stop_loss=None, take_profit=None, options=None):
        return self._order('sell', symbol, volume, stop_loss, take_profit, options)

    async def get_position(self, position_id, options=None):
        return {'id': position_id, 'openPrice': self.ask}

    async def get_positions(self, options=None):
        return self.positions


def _config(**overrides):
    values = dict(connection_type=MT5ConnectionType.METAAPI, metaapi_token='t', metaapi_account_id='a',
                  max_risk_per_trade=0.01)
    return MT5Config(**{**values, **overrides})


def _connection(rpc=None, **config):
    conn = MetaAPIConnection(_config(**config))
    conn.connection = rpc or FakeRpc()
    conn.connected = True
    return conn


def test_bridge_runs_a_coroutine_from_any_thread():
    bridge = AsyncBridge()

    async def work():
        return threading.current_thread().name

    results = []
    threads = [threading.Thread(target=lambda: results.append(bridge.run(work()))) for _ in range(3)]
    [t.start() for t in threads]
    [t.join() for t in threads]

    assert len(set(results)) == 1 and results[0] != threading.current_thread().name


def test_account_info_works_from_a_worker_thread():
    conn = _connection()
    seen = []

    thread = threading.Thread(target=lambda: seen.append(conn.get_account_info()))
    thread.start()
    thread.join()

    assert seen[0]['free_margin'] == 10000.0


def test_symbol_suffix_is_applied_for_the_broker():
    rpc = FakeRpc()
    conn = _connection(rpc, symbol_suffix='.r')

    info = conn.get_symbol_info('XAUUSD')
    conn.market_order('XAUUSD', 'LONG', 0.01, 4000.0, 4050.0)

    assert info['name'] == 'XAUUSD.r'
    assert rpc.orders[0]['symbol'] == 'XAUUSD.r'


def test_long_is_a_real_buy_with_stops_and_our_magic_number():
    rpc = FakeRpc()

    fill = _connection(rpc, magic_number=777).market_order('XAUUSD', 'LONG', 0.02, 4000.0, 4050.0)

    order = rpc.orders[0]
    assert (order['side'], order['volume'], order['stop_loss'], order['take_profit']) == ('buy', 0.02, 4000.0, 4050.0)
    assert order['options']['magic'] == 777
    assert fill == {'ticket': 5001, 'entry_price': 4025.0}


def test_short_is_a_sell():
    rpc = FakeRpc()

    _connection(rpc).market_order('XAUUSD', 'SHORT', 0.02, 4050.0, 4000.0)

    assert rpc.orders[0]['side'] == 'sell'


@pytest.mark.parametrize('direction,market,expected', [
    ('LONG', 4025.0, (4025.0, 4005.0, 4065.0)),
    ('SHORT', 4025.0, (4025.0, 4045.0, 3985.0)),
])
def test_levels_keep_their_distance_from_the_broker_price(direction, market, expected):
    stop, target = (3980.0, 4040.0) if direction == 'LONG' else (4020.0, 3960.0)

    assert align_levels_to_broker(direction, 4000.0, stop, target, market, digits=2) == expected


def _signal(symbol='XAUUSD', direction='LONG', entry=4000.0, stop=3980.0, target=4040.0):
    return dict(symbol=symbol, direction=direction, entry_price=entry, stop_loss=stop,
                take_profit=target, confidence=0.7)


def test_executor_sends_futures_levels_shifted_onto_the_broker_price():
    rpc = FakeRpc(ask=4025.0, bid=4024.5)
    config = _config()
    conn = _connection(rpc)

    result = TradeExecutor(conn, config, PositionCalculator(config)).execute_signal(_signal(), 10000.0)

    assert result.success, result.error_message
    assert (rpc.orders[0]['stop_loss'], rpc.orders[0]['take_profit']) == (4005.0, 4065.0)
    assert rpc.orders[0]['volume'] == 0.05  # $100 risk over a $20 stop on 100oz lots


def test_short_is_aligned_to_the_bid():
    rpc = FakeRpc(ask=4025.5, bid=4025.0)
    config = _config()

    TradeExecutor(_connection(rpc), config, PositionCalculator(config)).execute_signal(
        _signal(direction='SHORT', stop=4020.0, target=3960.0), 10000.0)

    assert (rpc.orders[0]['stop_loss'], rpc.orders[0]['take_profit']) == (4045.0, 3985.0)


def test_a_broker_rejection_is_a_failed_result_not_a_crash():
    rpc = FakeRpc(error=RuntimeError('market closed'))
    config = _config()

    result = TradeExecutor(_connection(rpc), config, PositionCalculator(config)).execute_signal(_signal(), 10000.0)

    assert not result.success and 'market closed' in result.error_message


def _db(tmp_path):
    manager = DatabaseManager(f"sqlite:///{tmp_path / 'orders.db'}")
    Base.metadata.create_all(manager.engine)
    with manager.session_scope() as session:
        for symbol in ('XAUUSD', 'GBPUSD'):
            session.add(SignalRow(timestamp=datetime(2026, 11, 6, 7), symbol=symbol, timeframe='1h',
                                  strategy_name='s', direction=SignalDirection.LONG, entry_price=4000.0,
                                  stop_loss=3980.0, take_profit=4040.0, confidence=0.7,
                                  status=SignalStatus.PENDING))
    return manager


def _row(manager, symbol):
    with manager.session_scope() as session:
        row = session.query(SignalRow).filter_by(symbol=symbol).one()
        return row.status, row.mt5_ticket, row.actual_entry, row.error_message, row.notes


def _subscriber(manager, rpc):
    config = _config()
    risk = RiskManager(config)
    sub = MT5Subscriber(connection=_connection(rpc), config=config, db_manager=manager, risk_manager=risk,
                        trading_mode=lambda: TradingMode.LIVE)
    return sub, risk


def _validated(symbol='XAUUSD'):
    return MagicMock(symbol=symbol, direction='LONG', entry_price=4000.0, stop_loss=3980.0,
                     take_profit=4040.0, confidence=0.7)


def test_fill_marks_the_signal_for_that_symbol(tmp_path):
    manager = _db(tmp_path)
    sub, risk = _subscriber(manager, FakeRpc())

    assert sub._execute_signal(_validated()) is True

    assert _row(manager, 'XAUUSD')[:3] == (SignalStatus.ACTIVE, 5001, 4025.0)
    assert _row(manager, 'GBPUSD')[0] is SignalStatus.PENDING
    assert [p['ticket'] for p in risk.current_positions] == [5001]


def test_a_ticket_too_big_for_the_column_is_kept_in_the_notes(tmp_path):
    manager = _db(tmp_path)
    sub, _ = _subscriber(manager, FakeRpc(position_id='5000000001'))

    sub._execute_signal(_validated())

    status, ticket, entry, _, notes = _row(manager, 'XAUUSD')
    assert (status, ticket, entry) == (SignalStatus.ACTIVE, None, 4025.0)
    assert '5000000001' in notes


def test_a_rejected_order_keeps_the_signal_in_the_record(tmp_path):
    manager = _db(tmp_path)
    sub, _ = _subscriber(manager, FakeRpc(error=RuntimeError('market closed')))

    assert sub._execute_signal(_validated()) is False

    status, _, _, error, _ = _row(manager, 'XAUUSD')
    assert status is SignalStatus.PENDING and 'market closed' in error


def test_a_database_error_after_a_fill_still_tracks_the_position(tmp_path):
    manager = _db(tmp_path)
    sub, risk = _subscriber(manager, FakeRpc())
    manager.session_scope = MagicMock(side_effect=RuntimeError('db down'))

    assert sub._execute_signal(_validated()) is True
    assert [p['ticket'] for p in risk.current_positions] == [5001]


def test_sync_drops_closed_positions_and_adopts_open_ones():
    risk = RiskManager(_config())
    risk.current_positions = [{'ticket': 1}, {'ticket': 2}]

    risk.sync_with_broker(balance=10000.0, open_tickets=[2, 3])

    assert sorted(p['ticket'] for p in risk.current_positions) == [2, 3]


def test_daily_loss_comes_from_the_balance():
    risk = RiskManager(_config(max_daily_loss=0.03))
    risk.sync_with_broker(balance=10000.0, open_tickets=[])
    risk.sync_with_broker(balance=9650.0, open_tickets=[])

    allowed, reason = risk.can_open_position(account_balance=9650.0, proposed_risk=10.0)

    assert not allowed and 'Daily loss' in reason


def test_workers_share_one_risk_manager():
    config = _config()

    assert get_shared_risk_manager(config) is get_shared_risk_manager(config)


def _worker(svc):
    worker = svc.TimeframeWorker.__new__(svc.TimeframeWorker)
    worker.spec = MagicMock(timeframe='1h')
    worker.enable_trading, worker.mt5_config = True, _config()
    worker.database_url, worker.generator = 'sqlite://', MagicMock()
    return worker


def test_a_broker_failure_leaves_the_worker_generating_signals(monkeypatch):
    import run_multi_timeframe_service as svc

    failing = MagicMock()
    failing.connect.return_value = False
    monkeypatch.setattr(svc, 'create_mt5_connection', lambda config: failing)
    worker = _worker(svc)

    worker._attach_trading()

    worker.generator.add_subscriber.assert_not_called()


def test_a_connected_broker_gets_a_subscriber_that_starts_off(tmp_path, monkeypatch):
    import run_multi_timeframe_service as svc

    working = MagicMock()
    working.connect.return_value = True
    working.get_account_info.return_value = {'balance': 10000.0}
    monkeypatch.setattr(svc, 'create_mt5_connection', lambda config: working)
    worker = _worker(svc)
    worker.database_url = f"sqlite:///{tmp_path / 'off.db'}"

    worker._attach_trading()

    subscriber = worker.generator.add_subscriber.call_args.args[0]
    assert isinstance(subscriber, MT5Subscriber)
    assert subscriber.trading_mode() is TradingMode.OFF


def test_the_metaapi_sdk_is_a_declared_dependency():
    requirements = (Path(__file__).parent.parent / 'requirements.txt').read_text()

    assert 'metaapi-cloud-sdk==29.1.1' in requirements

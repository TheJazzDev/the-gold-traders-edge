"""
One open signal per symbol (B1).

The backtest every live rule was validated on runs with max_open_trades=1,
but live had no such limit: during 2026-09-23..25 up to five XAUUSD shorts
were open at once, mostly on the same order-block zone, and one rally
stopped out five of them together (see
docs/superpowers/2026-09-25-weekly-signal-review.md). The generator now
refuses to publish while the repository still holds an open signal for the
same symbol.
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from backtesting.engine import Signal as StrategySignal, TradeDirection
from database.connection import DatabaseManager
from database.models import Base, Signal, SignalDirection, SignalStatus
from signals.open_signal_gate import make_open_signal_checker
from signals.realtime_generator import RealtimeSignalGenerator


class FakeFeed:
    symbol = "XAUUSD"
    timeframe = "1h"
    is_connected = True

    def __init__(self):
        dates = pd.date_range(start='2026-01-01', periods=5, freq='1h')
        self._df = pd.DataFrame({
            'open': [2000.0] * 5, 'high': [2005.0] * 5,
            'low': [1995.0] * 5, 'close': [2001.0] * 5,
        }, index=dates)

    def get_latest_candles(self, count):
        return self._df


class AlwaysSignals:
    """Strategy stub that fires on every candle."""
    rules_enabled = {'stub': True}

    def evaluate(self, df, idx):
        return StrategySignal(
            time=df.index[idx], direction=TradeDirection.SHORT,
            entry_price=2001.0, stop_loss=2011.0, take_profit=1981.0,
            signal_name='stub', confidence=0.7,
        )


def make_generator(open_signal_checker=None):
    validator = MagicMock()
    validator.validate.return_value = MagicMock(name='validated_signal')
    generator = RealtimeSignalGenerator(
        data_feed=FakeFeed(),
        strategy=AlwaysSignals(),
        validator=validator,
        open_signal_checker=open_signal_checker,
    )
    subscriber = MagicMock()
    generator.add_subscriber(subscriber)
    return generator, subscriber


class TestGeneratorOpenSignalGate:
    def test_suppresses_signal_while_symbol_has_an_open_signal(self):
        generator, subscriber = make_generator(open_signal_checker=lambda: True)

        assert generator.run_once() is None
        subscriber.assert_not_called()
        assert generator.total_signals_generated == 0

    def test_publishes_when_symbol_has_no_open_signal(self):
        generator, subscriber = make_generator(open_signal_checker=lambda: False)

        assert generator.run_once() is not None
        subscriber.assert_called_once()
        assert generator.total_signals_generated == 1

    def test_fails_closed_when_the_check_itself_errors(self):
        """If the open-signal check can't run (e.g. DB unreachable), don't
        publish: the DatabaseSubscriber couldn't record the signal either,
        so outcome tracking and this gate would both lose track of it."""
        def broken():
            raise RuntimeError("db down")

        generator, subscriber = make_generator(open_signal_checker=broken)

        assert generator.run_once() is None
        subscriber.assert_not_called()

    def test_backward_compatible_without_a_checker(self):
        generator, subscriber = make_generator(open_signal_checker=None)

        assert generator.run_once() is not None
        subscriber.assert_called_once()

    def test_checker_not_consulted_when_no_signal_fires(self):
        checker = MagicMock(return_value=True)
        generator, _ = make_generator(open_signal_checker=checker)
        generator.strategy = MagicMock(evaluate=MagicMock(return_value=None))

        generator.run_once()

        checker.assert_not_called()


@pytest.fixture
def database_url(tmp_path):
    url = f"sqlite:///{tmp_path / 'gate.db'}"
    Base.metadata.create_all(DatabaseManager(url).engine)
    return url


def add_signal(database_url, symbol="XAUUSD", timeframe="1h", status=SignalStatus.PENDING):
    with DatabaseManager(database_url).session_scope() as session:
        session.add(Signal(
            timestamp=datetime.utcnow() - timedelta(hours=1),
            symbol=symbol, timeframe=timeframe, strategy_name="Order Block Retest",
            direction=SignalDirection.SHORT, entry_price=2000.0, stop_loss=2010.0,
            take_profit=1980.0, confidence=0.7, risk_pips=100.0, reward_pips=200.0,
            risk_reward_ratio=2.0, status=status,
        ))


class TestMakeOpenSignalChecker:
    def test_false_when_repository_is_empty(self, database_url):
        assert make_open_signal_checker(database_url, "XAUUSD")() is False

    @pytest.mark.parametrize("status", [SignalStatus.PENDING, SignalStatus.ACTIVE])
    def test_true_for_an_open_signal_on_the_same_symbol(self, database_url, status):
        add_signal(database_url, status=status)
        assert make_open_signal_checker(database_url, "XAUUSD")() is True

    @pytest.mark.parametrize("status", [
        SignalStatus.CLOSED_TP, SignalStatus.CLOSED_SL, SignalStatus.CANCELLED,
    ])
    def test_false_once_the_signal_is_closed(self, database_url, status):
        add_signal(database_url, status=status)
        assert make_open_signal_checker(database_url, "XAUUSD")() is False

    def test_other_symbols_do_not_block(self, database_url):
        add_signal(database_url, symbol="GBPUSD")
        assert make_open_signal_checker(database_url, "XAUUSD")() is False
        assert make_open_signal_checker(database_url, "GBPUSD")() is True

    def test_scoped_by_symbol_not_timeframe(self, database_url):
        """The limit is per symbol: an open 15m gold signal still blocks a
        new 1h gold signal (same exposure)."""
        add_signal(database_url, timeframe="15m")
        assert make_open_signal_checker(database_url, "XAUUSD")() is True


class TestWorkerWiring:
    """TimeframeWorker must hand every generator a checker scoped to its
    own symbol — otherwise the gate silently doesn't exist in production."""

    def test_worker_passes_a_symbol_scoped_checker(self, tmp_path, monkeypatch):
        sys.path.insert(0, str(Path(__file__).parent.parent))
        import run_multi_timeframe_service as svc_module
        from unittest.mock import patch

        monkeypatch.setattr(svc_module, "__file__", str(tmp_path / "run_multi_timeframe_service.py"))
        worker = svc_module.TimeframeWorker.__new__(svc_module.TimeframeWorker)
        worker.spec = svc_module.GBPUSD_1H_SPEC
        worker.database_url = f"sqlite:///{tmp_path / 'svc.db'}"
        worker.shared_dedup_subscriber = MagicMock()
        worker.telegram_subscriber = MagicMock()
        worker.enable_trading = False
        worker.mt5_config = None

        with patch.object(svc_module, "create_datafeed"), \
             patch.object(svc_module, "SignalOutcomeTracker"), \
             patch.object(svc_module, "make_open_signal_checker", return_value="checker") as mock_make, \
             patch.object(svc_module, "RealtimeSignalGenerator") as mock_generator_cls:
            worker._run()

        mock_make.assert_called_once_with(worker.database_url, "GBPUSD")
        assert mock_generator_cls.call_args.kwargs["open_signal_checker"] == "checker"

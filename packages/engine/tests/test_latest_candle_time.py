"""The worker reports the newest candle its data feed returned, so the API can
alert when a market stops getting candles.

On 2026-11-26 Yahoo stopped publishing intraday bars for every CME future
(gold included) for over a day. The gold worker kept waking up, found no new
bar and went back to sleep, and nothing said so. Each worker's latest candle
time is now written to the `worker_latest_candles` setting for the API's
candle watchdog to watch.

It is a separate setting, not part of `worker_heartbeat`, because a setting's
value is VARCHAR(500) in Postgres. Adding it to the heartbeat on 2026-11-27
(a8b214f) made every heartbeat write fail in production; SQLite, which these
tests use, ignores the length, so the size tests below check it explicitly.
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import run_multi_timeframe_service as svc_module
from database.connection import DatabaseManager
from database.settings_models import Setting
from database.settings_repository import SettingsRepository
from signals.gold_strategy import GoldStrategy
from signals.realtime_generator import RealtimeSignalGenerator, SignalValidator
from tests.test_realtime_generator import FakeDataFeedWithCandles
from tests.test_worker_heartbeat import FakeWorker, make_service, read_heartbeat

VALUE_LIMIT = Setting.__table__.c.value.type.length
LIVE_WORKER_IDS = [f"{spec.symbol}:{spec.timeframe}" for spec in svc_module.WORKER_SPECS]


def _candles():
    dates = pd.date_range(start='2026-11-25 20:00', periods=5, freq='1h')
    df = pd.DataFrame({
        'open': [2000, 2001, 2002, 2003, 2004],
        'high': [2005, 2006, 2007, 2008, 2009],
        'low': [1995, 1996, 1997, 1998, 1999],
        'close': [2001, 2002, 2003, 2004, 2005],
    }, index=dates)
    return df, dates


def _generator(df, **kwargs):
    strategy = GoldStrategy()
    for name in strategy.rules_enabled:
        strategy.rules_enabled[name] = False
    return RealtimeSignalGenerator(
        data_feed=FakeDataFeedWithCandles(df), strategy=strategy,
        validator=SignalValidator(), **kwargs)


def _read_setting_raw(db_url, key):
    with DatabaseManager(db_url).session_scope() as session:
        return SettingsRepository(session).get_setting(key).value


def _read_latest_candles(db_url):
    with DatabaseManager(db_url).session_scope() as session:
        return SettingsRepository(session).get('worker_latest_candles', default={})


def _busy_workers():
    """Every live worker, with worst-case-sized values."""
    workers = {}
    for worker_id in LIVE_WORKER_IDS:
        worker = FakeWorker(is_running=True, candles=99999, signals=9999)
        worker.generator.latest_candle_time = pd.Timestamp('2026-11-26 04:00')
        workers[worker_id] = worker
    return workers


class TestGeneratorRemembersLatestCandle:
    def test_starts_unknown(self):
        df, _ = _candles()
        assert _generator(df).latest_candle_time is None

    def test_records_the_newest_candle_the_feed_returned(self):
        df, dates = _candles()
        generator = _generator(df)
        generator.run_once()
        assert generator.latest_candle_time == dates[-1]

    def test_records_it_even_when_the_candle_was_already_processed(self):
        # After a restart the worker skips the candle it already handled, but
        # the feed still delivered it: data is flowing, so no alert is due.
        df, dates = _candles()
        generator = _generator(df, last_processed_candle_getter=lambda: dates[-1])
        generator.run_once()
        assert generator.latest_candle_time == dates[-1]


class TestLatestCandlesSetting:
    def test_written_as_iso_text_per_worker(self, tmp_path):
        db_url = f"sqlite:///{tmp_path / 'heartbeat.db'}"
        service = make_service(db_url)
        worker = FakeWorker(is_running=True, candles=3, signals=0)
        worker.generator.latest_candle_time = pd.Timestamp('2026-11-26 04:00')
        service.workers = {'XAUUSD:1h': worker}

        service._save_heartbeat()

        assert _read_latest_candles(db_url) == {'XAUUSD:1h': '2026-11-26T04:00:00'}

    def test_null_before_the_first_candle(self, tmp_path):
        db_url = f"sqlite:///{tmp_path / 'heartbeat.db'}"
        service = make_service(db_url)
        service.workers = {'XAUUSD:1h': FakeWorker(is_running=True, candles=0, signals=0)}

        service._save_heartbeat()

        assert _read_latest_candles(db_url) == {'XAUUSD:1h': None}

    def test_kept_out_of_the_heartbeat(self, tmp_path):
        db_url = f"sqlite:///{tmp_path / 'heartbeat.db'}"
        service = make_service(db_url)
        service.workers = _busy_workers()

        service._save_heartbeat()

        for data in read_heartbeat(db_url)['workers'].values():
            assert 'latest_candle_time' not in data


class TestPayloadsFitTheColumn:
    """Postgres rejects a setting value over VARCHAR(500); SQLite does not."""

    def test_heartbeat_fits_with_every_live_worker(self, tmp_path):
        db_url = f"sqlite:///{tmp_path / 'heartbeat.db'}"
        service = make_service(db_url)
        service.workers = _busy_workers()

        service._save_heartbeat()

        assert len(_read_setting_raw(db_url, 'worker_heartbeat')) <= VALUE_LIMIT

    def test_latest_candles_fit_with_every_live_worker(self, tmp_path):
        db_url = f"sqlite:///{tmp_path / 'heartbeat.db'}"
        service = make_service(db_url)
        service.workers = _busy_workers()

        service._save_heartbeat()

        raw = _read_setting_raw(db_url, 'worker_latest_candles')
        assert len(json.loads(raw)) == len(LIVE_WORKER_IDS)
        assert len(raw) <= VALUE_LIMIT

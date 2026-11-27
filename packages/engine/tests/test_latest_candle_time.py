"""The worker reports the newest candle its data feed returned, so the API can
alert when a market stops getting candles.

On 2026-11-26 Yahoo stopped publishing intraday bars for every CME future
(gold included) for over a day. The gold worker kept waking up, found no new
bar and went back to sleep, and nothing said so. The heartbeat now carries each
worker's latest candle time for the API's candle watchdog to watch.
"""
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import run_multi_timeframe_service as svc_module
from signals.gold_strategy import GoldStrategy
from signals.realtime_generator import RealtimeSignalGenerator, SignalValidator
from tests.test_realtime_generator import FakeDataFeedWithCandles
from tests.test_worker_heartbeat import FakeWorker, make_service, read_heartbeat


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


class TestHeartbeatCarriesLatestCandle:
    def test_written_as_iso_text(self, tmp_path):
        db_url = f"sqlite:///{tmp_path / 'heartbeat.db'}"
        service = make_service(db_url)
        worker = FakeWorker(is_running=True, candles=3, signals=0)
        worker.generator.latest_candle_time = pd.Timestamp('2026-11-26 04:00')
        service.workers = {'XAUUSD:1h': worker}

        service._save_heartbeat()

        payload = read_heartbeat(db_url)
        assert payload['workers']['XAUUSD:1h']['latest_candle_time'] == '2026-11-26T04:00:00'

    def test_null_before_the_first_candle(self, tmp_path):
        db_url = f"sqlite:///{tmp_path / 'heartbeat.db'}"
        service = make_service(db_url)
        service.workers = {'XAUUSD:1h': FakeWorker(is_running=True, candles=0, signals=0)}

        service._save_heartbeat()

        assert read_heartbeat(db_url)['workers']['XAUUSD:1h']['latest_candle_time'] is None

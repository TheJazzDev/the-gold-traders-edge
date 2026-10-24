"""Tests for the per-evaluation candle log: live writes the exact frame it
evaluated, so a live-vs-backtest mismatch can be replayed on live's own
input instead of on Yahoo's (later revised) history.
"""
import logging
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from signals.candle_log import CANDLE_LOG_PREFIX, format_candle_log, parse_candle_log


def _frame(n=5):
    index = pd.date_range('2026-10-15 03:00', periods=n, freq='h')
    return pd.DataFrame({
        'open': [4181.299805 + i for i in range(n)],
        'high': [4183.299805 + i for i in range(n)],
        'low': [4165.100098 + i for i in range(n)],
        'close': [4165.600098 + i for i in range(n)],
        'volume': [4427 + i for i in range(n)],
    }, index=index)


def test_round_trip_returns_the_same_candles():
    df = _frame()
    line = format_candle_log(df, 'XAUUSD', '1h')
    symbol, timeframe, parsed = parse_candle_log(line)
    assert (symbol, timeframe) == ('XAUUSD', '1h')
    assert list(parsed.index) == list(df.index)
    for col in ('open', 'high', 'low', 'close'):
        assert parsed[col].to_numpy() == pytest.approx(df[col].to_numpy(), abs=1e-6)


def test_line_is_one_line_and_greppable():
    line = format_candle_log(_frame(), 'EURUSD', '1h')
    assert '\n' not in line
    assert line.startswith(CANDLE_LOG_PREFIX)


def test_parse_finds_the_payload_inside_a_full_log_line():
    line = format_candle_log(_frame(), 'XAUUSD', '1h')
    logged = f"2026-10-15 08:15:55,096 - signals.realtime_generator - INFO - {line}"
    _, _, parsed = parse_candle_log(logged)
    assert len(parsed) == 5


def test_run_once_logs_the_frame_it_evaluated(caplog):
    from signals.realtime_generator import RealtimeSignalGenerator

    df = _frame(30)

    class Feed:
        symbol, timeframe, is_connected = 'XAUUSD', '1h', True

        def get_latest_candles(self, count=None):
            return df

    generator = RealtimeSignalGenerator(data_feed=Feed())
    with caplog.at_level(logging.INFO, logger='signals.realtime_generator'):
        generator.run_once()

    lines = [r.getMessage() for r in caplog.records if CANDLE_LOG_PREFIX in r.getMessage()]
    assert len(lines) == 1
    _, _, parsed = parse_candle_log(lines[0])
    assert list(parsed.index) == list(df.index)

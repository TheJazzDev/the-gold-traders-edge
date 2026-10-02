"""Weekly live-vs-backtest parity check.

On 2026-10-02 live stood at −5R over 17 trades while a replay of the same
period through the backtest scored +5R. The gap was all plumbing (gold
candles evaluated 10 min early, weekend expiry, an outage, stacking), and
it had looked like a losing strategy for a month. This check replays each
week and shows where live and the backtest disagree, so the next gap shows
up in the weekly report instead of being mistaken for a bad week.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from backtesting.engine import Signal, TradeDirection
from backtesting.parity_replay import (
    TradeOutcome, build_parity_text, compare, live_outcome, replay_outcomes,
)


def t(symbol, when, outcome, r, direction='LONG'):
    return TradeOutcome(symbol=symbol, time=pd.Timestamp(when), direction=direction, outcome=outcome, r=r)


class TestLiveOutcome:
    def test_maps_live_statuses(self):
        tp = live_outcome('GBPUSD', '2026-09-25 07:00', 'LONG', 'closed_tp', pnl_pips=46.0, risk_pips=23.0, notes='')
        expired = live_outcome('GBPUSD', '2026-09-25 07:00', 'LONG', 'cancelled', None, 23.0,
                               notes='x [expired after 48.0h with no resolution]')
        still_open = live_outcome('GBPUSD', '2026-09-25 07:00', 'LONG', 'active', None, 23.0, notes='')

        assert (tp.outcome, tp.r) == ('tp', 2.0)
        assert (expired.outcome, expired.r) == ('expired', None)
        assert still_open.outcome == 'open'

    def test_cancelled_without_expiry_note_is_ignored(self):
        assert live_outcome('XAUUSD', '2026-09-04 14:00', 'LONG', 'cancelled', None, 10.0, notes='manual') is None


class TestCompare:
    def test_matching_trades_report_no_mismatches(self):
        live = [t('EURUSD', '2026-10-01 07:00', 'tp', 2.0)]
        replay = [t('EURUSD', '2026-10-01 07:00', 'tp', 2.0)]

        report = compare(live, replay)

        assert report['EURUSD'].mismatches == []
        assert report['EURUSD'].live_r == report['EURUSD'].replay_r == 2.0

    def test_the_arlb_0925_weekend_expiry_case(self):
        live = [t('GBPUSD', '2026-09-25 07:00', 'expired', None),
                t('GBPUSD', '2026-09-28 07:00', 'sl', -1.0)]
        replay = [t('GBPUSD', '2026-09-25 07:00', 'tp', 2.0)]

        report = compare(live, replay)['GBPUSD']

        assert report.live_r == -1.0
        assert report.replay_r == 2.0
        assert [m.kind for m in report.mismatches] == ['outcome', 'live_only']

    def test_replay_only_trade_is_flagged(self):
        report = compare([], [t('XAUUSD', '2026-09-21 02:00', 'tp', 2.0, 'SHORT')])['XAUUSD']

        assert [m.kind for m in report.mismatches] == ['replay_only']


class TestBuildParityText:
    def test_flags_a_gap_and_lists_mismatches(self):
        live = [t('GBPUSD', '2026-09-25 07:00', 'expired', None),
                t('GBPUSD', '2026-09-28 07:00', 'sl', -1.0)]
        replay = [t('GBPUSD', '2026-09-25 07:00', 'tp', 2.0)]

        text = build_parity_text(compare(live, replay), days=7)

        assert 'GBPUSD' in text
        assert 'live -1.0R' in text and 'backtest +2.0R' in text
        assert '09-25 07:00 LONG: live expired, backtest TP' in text
        assert '09-28 07:00 LONG: live only (SL)' in text

    def test_clean_week_says_so(self):
        same = [t('EURUSD', '2026-10-01 07:00', 'tp', 2.0)]

        text = build_parity_text(compare(same, same), days=7)

        assert '✅' in text and 'only' not in text


class TestReplayOutcomes:
    def test_replays_only_trades_inside_the_window(self):
        index = pd.date_range('2026-09-28 00:00', periods=48, freq='h')
        high = np.full(48, 100.5)
        high[30] = 111.0  # TP for a long from 100 with TP 110
        df = pd.DataFrame({'open': 100.0, 'high': high, 'low': 99.5, 'close': 100.0,
                           'volume': 1.0}, index=index)

        def strategy_func(frame, i):
            if frame.index[i].hour != 7:
                return None
            return Signal(time=frame.index[i], direction=TradeDirection.LONG, entry_price=100.0,
                          stop_loss=95.0, take_profit=110.0, signal_name='t')

        out = replay_outcomes('EURUSD', df, strategy_func, start=pd.Timestamp('2026-09-28 05:00'),
                              warmup=5, expiry_hours=48)

        # 09-28 07:00 entry hits TP at candle 30 (09-29 06:00); the 09-29
        # 07:00 signal opens after and is still open at the end.
        assert [(o.time, o.outcome, o.r) for o in out] == [
            (pd.Timestamp('2026-09-28 07:00'), 'tp', 2.0),
            (pd.Timestamp('2026-09-29 07:00'), 'open', None),
        ]

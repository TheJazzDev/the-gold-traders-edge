"""Signal expiry counts market hours, not wall-clock hours.

Live ARLB-0925-01 (GBPUSD LONG, Fri 2026-09-25 07:00) was cancelled at
Sun 09-27 23:00 "after 48h": 64 wall-clock hours, but only ~16 of them with
the market open. Its TP hit Mon 09-28 16:00. The cancel also freed the
one-open-signal slot, so live then took ARLB-0928-01, which lost — a 3R
swing (+2R → −1R) from a clock that kept running over the weekend.

The backtest had no expiry at all, so it disagreed with live either way.
Both now use the same market-hours expiry.
"""
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from backtesting.engine import BacktestEngine, Signal, TradeDirection, TradeStatus
from signals.outcome_tracker import OpenSignalLike, OutcomeAction, evaluate_signal_outcome
from utils.market_hours import market_hours_between


class TestMarketHoursBetween:
    def test_weekday_span_counts_every_hour(self):
        assert market_hours_between(datetime(2026, 9, 28, 7), datetime(2026, 9, 30, 7)) == 48

    def test_weekend_is_not_counted(self):
        # Fri 07:00 -> Fri 21:00 close = 14h, Sun 21:00 open -> 23:00 = 2h.
        assert market_hours_between(datetime(2026, 9, 25, 7), datetime(2026, 9, 27, 23)) == 16

    def test_span_entirely_inside_the_weekend_is_zero(self):
        assert market_hours_between(datetime(2026, 9, 26, 3), datetime(2026, 9, 26, 20)) == 0

    def test_span_over_two_weekends(self):
        # Fri 09-25 07:00 -> Mon 10-05 07:00: 240 wall-clock hours, minus
        # two 48h weekends.
        assert market_hours_between(datetime(2026, 9, 25, 7), datetime(2026, 10, 5, 7)) == 144


class TestLiveExpiryUsesMarketHours:
    SIGNAL = OpenSignalLike(
        id=1, direction="LONG", entry_price=1.32308,
        stop_loss=1.32078, take_profit=1.32768,
        timestamp=datetime(2026, 9, 25, 7, 0),
    )

    @staticmethod
    def _quiet_candle():
        return pd.Series({'open': 1.324, 'high': 1.325, 'low': 1.323, 'close': 1.324})

    def test_arlb_0925_is_not_expired_on_sunday_night(self):
        action = evaluate_signal_outcome(
            self.SIGNAL, self._quiet_candle(), datetime(2026, 9, 27, 23, 0), expiry_hours=48)

        assert action == OutcomeAction.NONE

    def test_arlb_0925_still_reaches_its_monday_take_profit(self):
        tp_candle = pd.Series({'open': 1.326, 'high': 1.3278, 'low': 1.3255, 'close': 1.327})

        action = evaluate_signal_outcome(
            self.SIGNAL, tp_candle, datetime(2026, 9, 28, 16, 0), expiry_hours=48)

        assert action == OutcomeAction.CLOSED_TP

    def test_expires_once_market_hours_exceed_the_limit(self):
        # Fri 07:00 + 14h Fri + 35h Mon/Tue (Sun 21:00 -> Tue 08:00) = 49h.
        action = evaluate_signal_outcome(
            self.SIGNAL, self._quiet_candle(), datetime(2026, 9, 29, 8, 0), expiry_hours=48)

        assert action == OutcomeAction.EXPIRED


class TestBacktestModelsTheSameExpiry:
    @staticmethod
    def _flat_df(start, periods):
        index = pd.date_range(start=start, periods=periods, freq='h')
        return pd.DataFrame({'open': 100.0, 'high': 100.5, 'low': 99.5, 'close': 100.0,
                             'volume': np.ones(periods)}, index=index)

    @staticmethod
    def _signal_on_first_candle(df, i):
        if i != 0:
            return None
        return Signal(time=df.index[0], direction=TradeDirection.LONG, entry_price=100.0,
                      stop_loss=95.0, take_profit=110.0, signal_name='test')

    def test_trade_with_no_resolution_expires(self):
        df = self._flat_df('2026-09-28 07:00', 72)  # Mon -> Thu, all market hours
        engine = BacktestEngine(initial_balance=10000, commission=0.0, slippage=0.0)

        result = engine.run(df, self._signal_on_first_candle, expiry_hours=48)

        trade = result.trades[0]
        assert trade.status == TradeStatus.EXPIRED
        assert trade.exit_time == pd.Timestamp('2026-09-30 08:00')  # first candle past 48 market hours
        assert trade.pnl == 0

    def test_weekend_does_not_expire_a_backtest_trade(self):
        df = self._flat_df('2026-09-25 07:00', 60)  # Fri 07:00 -> Sun 18:00
        engine = BacktestEngine(initial_balance=10000, commission=0.0, slippage=0.0)

        result = engine.run(df, self._signal_on_first_candle, expiry_hours=48)

        assert result.trades[0].status == TradeStatus.CLOSED_MANUAL  # still open at the end

    def test_no_expiry_by_default(self):
        df = self._flat_df('2026-09-28 07:00', 72)
        engine = BacktestEngine(initial_balance=10000, commission=0.0, slippage=0.0)

        result = engine.run(df, self._signal_on_first_candle)

        assert result.trades[0].status == TradeStatus.CLOSED_MANUAL

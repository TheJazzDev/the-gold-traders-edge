"""
Backtests must score the same trade population live publishes (B5).

The tuner filtered only on risk/reward, but live's SignalValidator also
drops anything under min_confidence=0.60, so the backtested trades were a
different set from the live ones. And the test slice was scored with no
history before it, while live always has hundreds of candles to warm up
its indicators.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from backtesting.engine import Signal as StrategySignal, Trade, TradeDirection, TradeStatus
from backtesting.live_parity import (
    PRODUCTION_MIN_CONFIDENCE, PRODUCTION_MIN_RR, live_gated_strategy_func,
    max_losing_streak, resolved_stats, run_on_window,
)


def signal(confidence=0.7, tp=2020.0):
    return StrategySignal(
        time=pd.Timestamp('2026-01-01'), direction=TradeDirection.LONG,
        entry_price=2000.0, stop_loss=1990.0, take_profit=tp,
        signal_name='test', confidence=confidence,
    )


class Stub:
    def __init__(self, sig):
        self.sig = sig

    def evaluate(self, df, idx):
        return self.sig


class TestLiveGatedStrategyFunc:
    def test_matches_live_settings(self):
        assert PRODUCTION_MIN_CONFIDENCE == 0.60
        assert PRODUCTION_MIN_RR == 1.5

    def test_drops_signal_below_min_confidence(self):
        assert live_gated_strategy_func(Stub(signal(confidence=0.55)))(None, 0) is None

    def test_keeps_signal_at_exactly_min_confidence(self):
        """SignalValidator rejects only confidence < min, so 0.60 passes."""
        sig = signal(confidence=0.60)
        assert live_gated_strategy_func(Stub(sig))(None, 0) is sig

    def test_still_drops_signal_below_min_rr(self):
        assert live_gated_strategy_func(Stub(signal(tp=2005.0)))(None, 0) is None

    def test_passes_no_signal_through(self):
        assert live_gated_strategy_func(Stub(None))(None, 0) is None


def trade(status, pnl, t='2026-01-01'):
    return Trade(id=0, entry_time=pd.Timestamp(t), entry_price=2000.0, direction=TradeDirection.LONG,
                 stop_loss=1990.0, take_profit=2020.0, status=status, pnl=pnl)


class TestMaxLosingStreak:
    def test_counts_longest_run_of_losses(self):
        W, L = (TradeStatus.CLOSED_TP, 200.0), (TradeStatus.CLOSED_SL, -100.0)
        trades = [trade(*x) for x in (L, L, W, L, L, L, W, L)]
        assert max_losing_streak(trades) == 3

    def test_zero_when_no_losses(self):
        assert max_losing_streak([trade(TradeStatus.CLOSED_TP, 200.0)]) == 0

    def test_resolved_stats_reports_it(self):
        class R:
            initial_balance = 10000
            trades = [trade(TradeStatus.CLOSED_SL, -100.0), trade(TradeStatus.CLOSED_SL, -100.0),
                      trade(TradeStatus.CLOSED_MANUAL, 50.0), trade(TradeStatus.CLOSED_TP, 200.0)]
        stats = resolved_stats(R())
        assert stats['max_losing_streak'] == 2
        assert stats['total_trades'] == 3


class TestRunOnWindow:
    def _df(self, n=50):
        idx = pd.date_range('2026-01-01', periods=n, freq='1h')
        return pd.DataFrame({'open': 2000.0, 'high': 2001.0, 'low': 1999.0, 'close': 2000.0}, index=idx)

    def test_strategy_sees_warmup_history_but_trades_only_in_window(self):
        df = self._df()
        seen = []

        def strategy_func(frame, idx):
            seen.append((frame.index[idx], idx))
            return None

        run_on_window(df, start=df.index[30], strategy_func=strategy_func, warmup=10)

        # The first candle the strategy is asked about already has 10
        # candles of history behind it.
        first_time, first_idx = seen[0]
        assert first_idx >= 10
        # Nothing before the warm-up window is ever passed in.
        assert all(t >= df.index[20] for t, _ in seen)

    def test_no_trade_opens_before_the_window(self):
        df = self._df()

        def always(frame, idx):
            return StrategySignal(time=frame.index[idx], direction=TradeDirection.LONG,
                                  entry_price=2000.0, stop_loss=1990.0, take_profit=2001.5,
                                  signal_name='t', confidence=0.9)

        result = run_on_window(df, start=df.index[30], strategy_func=always, warmup=10)
        assert result.trades
        assert min(t.entry_time for t in result.trades) >= df.index[30]

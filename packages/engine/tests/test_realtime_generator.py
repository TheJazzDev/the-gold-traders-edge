"""Tests for RealtimeSignalGenerator."""
import sys
from pathlib import Path
import logging

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from signals.gold_strategy import GoldStrategy
from signals.realtime_generator import RealtimeSignalGenerator, SignalValidator
from backtesting.engine import Signal as StrategySignal, TradeDirection


class TestComputeRiskReward:
    """Regression coverage: this is the risk/reward gate tune_strategy.py's
    _production_valid_strategy_func also uses, so tuning and production score
    the same trade population."""

    def test_long_with_positive_risk_and_reward(self):
        signal = StrategySignal(
            time=pd.Timestamp('2026-01-01', tz='UTC'), direction=TradeDirection.LONG,
            entry_price=2000.0, stop_loss=1990.0, take_profit=2020.0,
            signal_name='test',
        )
        risk_pips, reward_pips, rr = SignalValidator.compute_risk_reward(signal)
        assert risk_pips == pytest.approx(100.0)
        assert reward_pips == pytest.approx(200.0)
        assert rr == pytest.approx(2.0)

    def test_short_with_positive_risk_and_reward(self):
        signal = StrategySignal(
            time=pd.Timestamp('2026-01-01', tz='UTC'), direction=TradeDirection.SHORT,
            entry_price=2000.0, stop_loss=2010.0, take_profit=1980.0,
            signal_name='test',
        )
        risk_pips, reward_pips, rr = SignalValidator.compute_risk_reward(signal)
        assert risk_pips == pytest.approx(100.0)
        assert reward_pips == pytest.approx(200.0)
        assert rr == pytest.approx(2.0)

    def test_long_with_stop_above_entry_is_rejected(self):
        signal = StrategySignal(
            time=pd.Timestamp('2026-01-01', tz='UTC'), direction=TradeDirection.LONG,
            entry_price=2000.0, stop_loss=2010.0, take_profit=1980.0,
            signal_name='test',
        )
        assert SignalValidator.compute_risk_reward(signal) is None

    def test_long_with_take_profit_below_entry_is_rejected(self):
        signal = StrategySignal(
            time=pd.Timestamp('2026-01-01', tz='UTC'), direction=TradeDirection.LONG,
            entry_price=2000.0, stop_loss=1990.0, take_profit=1995.0 - 20,
            signal_name='test',
        )
        assert SignalValidator.compute_risk_reward(signal) is None


class TestValidateHandlesNaiveTimestamps:
    """
    Regression coverage for a self-inflicted production outage: fixing the
    Yahoo Finance timezone bug (converting candle timestamps to naive UTC
    at the source, see realtime_feed.py) made every signal.time naive, but
    SignalValidator.validate() still did
    `pd.Timestamp.now(tz='UTC') - pd.Timestamp(signal.time)` — a tz-aware
    minus tz-naive subtraction that raises TypeError. Every signal
    generated in production between that fix deploying and this one being
    caught crashed inside validate() and was silently never published.
    """

    def test_recent_naive_timestamp_does_not_raise(self):
        validator = SignalValidator(min_rr_ratio=1.5)
        recent_naive = pd.Timestamp.now(tz='UTC').tz_localize(None) - pd.Timedelta(minutes=5)
        signal = StrategySignal(
            time=recent_naive, direction=TradeDirection.LONG,
            entry_price=2000.0, stop_loss=1990.0, take_profit=2020.0,
            confidence=0.6, signal_name='test',
        )

        validated = validator.validate(signal, current_price=2000.0, symbol='XAUUSD', timeframe='1h')

        assert validated is not None
        assert validated.timestamp.tzinfo is None

    def test_recent_tz_aware_timestamp_still_works(self):
        """Defensive: a tz-aware signal.time (e.g. a future/alternate data
        feed) must normalize cleanly rather than raise."""
        validator = SignalValidator(min_rr_ratio=1.5)
        recent_aware = pd.Timestamp.now(tz='UTC') - pd.Timedelta(minutes=5)
        signal = StrategySignal(
            time=recent_aware, direction=TradeDirection.LONG,
            entry_price=2000.0, stop_loss=1990.0, take_profit=2020.0,
            confidence=0.6, signal_name='test',
        )

        validated = validator.validate(signal, current_price=2000.0, symbol='XAUUSD', timeframe='1h')

        assert validated is not None
        assert validated.timestamp.tzinfo is None

    def test_old_naive_timestamp_is_rejected_not_crashed(self):
        validator = SignalValidator(min_rr_ratio=1.5)
        old_naive = pd.Timestamp.now(tz='UTC').tz_localize(None) - pd.Timedelta(hours=5)
        signal = StrategySignal(
            time=old_naive, direction=TradeDirection.LONG,
            entry_price=2000.0, stop_loss=1990.0, take_profit=2020.0,
            confidence=0.6, signal_name='test',
        )

        assert validator.validate(signal, current_price=2000.0, symbol='XAUUSD', timeframe='1h') is None


class TestMeetsMinRr:
    """Regression coverage for the fix: reward/risk for an RR-configured
    trade often lands a few ULPs below the intended ratio due to
    floating-point cancellation (e.g. 1.4999999999999998 for a configured
    1.5). A strict `<` comparison silently rejected ~27% of trades at a
    round-number RR target for no economic reason."""

    def test_exact_ratio_passes(self):
        assert SignalValidator.meets_min_rr(1.5, 1.5) is True

    def test_ratio_a_few_ulps_below_target_still_passes(self):
        assert SignalValidator.meets_min_rr(1.4999999999999998, 1.5) is True

    def test_genuinely_below_target_fails(self):
        assert SignalValidator.meets_min_rr(1.4, 1.5) is False

    def test_ratio_above_target_passes(self):
        assert SignalValidator.meets_min_rr(2.0, 1.5) is True


class FakeDataFeed:
    """Minimal stand-in for RealtimeDataFeed, just enough to construct a generator."""
    symbol = "XAUUSD"
    timeframe = "1h"
    is_connected = True

    def connect(self):
        return True

    def disconnect(self):
        return True

    def get_latest_candles(self, count):
        import pandas as pd
        return pd.DataFrame()  # Empty DataFrame stops iteration

    def wait_for_candle_close(self, check_interval):
        raise StopIteration  # Exit loop immediately


class TestStrategyLogLine:
    def test_start_logs_actual_enabled_rules(self, caplog):
        strategy = GoldStrategy()
        strategy.rules_enabled['order_block_retest'] = False

        generator = RealtimeSignalGenerator(
            data_feed=FakeDataFeed(),
            strategy=strategy,
            validator=SignalValidator(),
        )

        with caplog.at_level(logging.INFO):
            generator.start(max_iterations=0)

        messages = [r.message for r in caplog.records]
        # Reflects the actual (disabled) state, not a hardcoded assumption:
        # with the only rule off, the "Strategy: ..." line lists nothing.
        assert "Strategy: " in messages, messages


import pandas as pd
from unittest.mock import MagicMock


class FakeDataFeedWithCandles:
    symbol = "XAUUSD"
    timeframe = "1h"
    is_connected = True

    def __init__(self, df):
        self._df = df

    def connect(self):
        return True

    def get_latest_candles(self, count):
        return self._df

    def wait_for_candle_close(self, check_interval=60):
        pass


class TestOutcomeTrackerWiring:
    def test_run_once_calls_outcome_tracker_with_latest_candle(self):
        dates = pd.date_range(start='2026-01-01', periods=5, freq='1h')
        df = pd.DataFrame({
            'open': [2000, 2001, 2002, 2003, 2004],
            'high': [2005, 2006, 2007, 2008, 2009],
            'low': [1995, 1996, 1997, 1998, 1999],
            'close': [2001, 2002, 2003, 2004, 2005],
        }, index=dates)

        strategy = GoldStrategy()
        for name in strategy.rules_enabled:
            strategy.rules_enabled[name] = False  # no new signals this test

        mock_tracker = MagicMock()
        generator = RealtimeSignalGenerator(
            data_feed=FakeDataFeedWithCandles(df),
            strategy=strategy,
            validator=SignalValidator(),
            outcome_tracker=mock_tracker,
        )

        generator.run_once()

        mock_tracker.check_candle.assert_called_once()
        call_args = mock_tracker.check_candle.call_args
        assert call_args[0][1] == dates[-1]  # candle_time

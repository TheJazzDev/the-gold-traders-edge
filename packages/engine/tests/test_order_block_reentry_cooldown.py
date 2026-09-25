"""
Re-entry cooldown for stopped-out order-block zones (B2).

OBR-0909-01 re-sold the 4434.7-4456.3 zone three hours after OBR-0908-01's
overlapping 4434.3-4448.6 zone had stopped out, and lost the same way
(docs/superpowers/2026-09-25-weekly-signal-review.md). The two came from
different order-block candles, so the cooldown works on price overlap, not
candle identity.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from signals.order_block_zones import detect_order_block, stopped_out_zones
from signals.gold_strategy import GoldStrategy
from backtesting.engine import TradeDirection

FLAT = 1995.0


def flat_df(n=80):
    """Quiet market: every candle 1994-1996, so ATR is ~2 and the SL buffer
    (0.3 * ATR) is ~0.6."""
    idx = pd.date_range('2026-01-01', periods=n, freq='1h')
    return pd.DataFrame({
        'open': [FLAT] * n, 'high': [FLAT + 1] * n,
        'low': [FLAT - 1] * n, 'close': [FLAT + 0.2] * n,
    }, index=idx)


def put(df, i, o, h, l, c):
    df.iloc[i, df.columns.get_loc('open')] = o
    df.iloc[i, df.columns.get_loc('high')] = h
    df.iloc[i, df.columns.get_loc('low')] = l
    df.iloc[i, df.columns.get_loc('close')] = c


def atr_of(df):
    return np.full(len(df), 2.0)


def bearish_block_at(df, i):
    """Strong bearish candle -> bearish zone low=1994.8, high=2010 (its open)."""
    put(df, i, 2010.0, 2010.5, 1994.8, 1996.0)


def retest_bearish(df, i, high=2005.0):
    put(df, i, 1996.0, high, 1995.5, 1997.0)


def detect(df, idx, cooldown):
    return detect_order_block(df, idx, lookback=20, atr=atr_of(df),
                              sl_buffer_atr=0.3, reentry_cooldown_candles=cooldown)


class TestUnchangedWithoutCooldown:
    def test_cooldown_zero_matches_the_original_detector(self):
        df = flat_df()
        bearish_block_at(df, 50)
        put(df, 55, 1996.0, 2015.0, 1995.0, 1996.0)  # would stop out the zone
        retest_bearish(df, 60)

        ob = detect(df, 60, cooldown=0)

        assert ob is not None
        assert (ob['type'], ob['low'], ob['high'], ob['index']) == ('bearish', 1994.8, 2010.0, 50)


class TestStoppedOutZoneIsSkipped:
    def test_retest_after_zone_was_stopped_out_is_blocked(self):
        df = flat_df()
        bearish_block_at(df, 50)
        put(df, 55, 1996.0, 2015.0, 1995.0, 1996.0)  # high > 2010 + 0.6 -> stop-out
        retest_bearish(df, 60)

        assert detect(df, 60, cooldown=20) is None

    def test_retest_without_prior_stop_out_is_allowed(self):
        df = flat_df()
        bearish_block_at(df, 50)
        put(df, 55, 1996.0, 2010.4, 1995.0, 1996.0)  # pokes in but under 2010.6
        retest_bearish(df, 60)

        assert detect(df, 60, cooldown=20) is not None

    def test_cooldown_expires_after_n_candles(self):
        df = flat_df()
        bearish_block_at(df, 50)
        put(df, 55, 1996.0, 2015.0, 1995.0, 1996.0)
        retest_bearish(df, 60)

        assert detect(df, 60, cooldown=5) is None      # 60 - 55 = 5, still cooling
        assert detect(df, 60, cooldown=4) is not None  # expired

    def test_overlapping_zone_from_a_different_candle_is_blocked(self):
        """The OBR-0908-01 / OBR-0909-01 shape: a newer order block over the
        same prices as the one that just failed."""
        df = flat_df()
        bearish_block_at(df, 45)
        put(df, 50, 1996.0, 2015.0, 1995.0, 1996.0)    # zone 45 stops out
        put(df, 52, 2008.0, 2008.5, 1999.0, 1999.5)    # new bearish block 1999-2008, overlaps
        retest_bearish(df, 60, high=2003.0)            # only inside the newer block

        assert detect(df, 60, cooldown=0)['index'] == 45
        assert detect(df, 60, cooldown=20) is None

    def test_new_non_overlapping_block_is_still_traded(self):
        df = flat_df()
        bearish_block_at(df, 45)
        put(df, 50, 1996.0, 2015.0, 1995.0, 1996.0)    # zone 45 stops out
        put(df, 53, 2025.0, 2025.5, 2016.0, 2016.5)    # fresh block 2016-2025, above it
        put(df, 60, 2017.0, 2020.0, 2016.5, 2018.0)    # retests only the fresh block

        ob = detect(df, 60, cooldown=20)
        assert ob is not None and ob['index'] == 53

    def test_stop_out_on_the_current_candle_counts(self):
        """The candle being evaluated has closed, so a stop-out on it is
        known — the same candle that stopped OBR-0924-03 produced
        OBR-0924-04 on an overlapping zone."""
        df = flat_df()
        put(df, 45, 2022.0, 2022.5, 2009.5, 2010.0)    # zone B 2009.5-2022
        put(df, 50, 2010.0, 2010.5, 2004.0, 2004.5)    # zone A 2004-2010, just below B
        # Current candle breaks A's stop (2010.6) and closes inside B.
        put(df, 60, 2005.0, 2012.0, 2004.5, 2011.0)

        assert detect(df, 60, cooldown=0)['index'] == 45
        assert detect(df, 60, cooldown=20) is None


class TestBullishMirror:
    def test_bullish_zone_stopped_out_below_is_blocked(self):
        df = flat_df()
        put(df, 50, 1980.0, 1995.2, 1979.5, 1995.0)    # bullish block low=1980 (open), high=1995.2
        put(df, 55, 1994.0, 1995.0, 1975.0, 1994.0)    # low < 1980 - 0.6 -> stop-out
        put(df, 60, 1994.0, 1995.0, 1985.0, 1994.5)    # retest into the zone

        assert detect(df, 60, cooldown=0)['type'] == 'bullish'
        assert detect(df, 60, cooldown=20) is None


class TestStoppedOutZones:
    def test_reports_zone_and_the_candle_that_stopped_it(self):
        df = flat_df()
        bearish_block_at(df, 50)
        put(df, 55, 1996.0, 2015.0, 1995.0, 1996.0)

        zones = stopped_out_zones(df, 60, atr_of(df), sl_buffer_atr=0.3, start=40)

        assert ('bearish', 1994.8, 2010.0, 55) in [(z.type, z.low, z.high, z.stopped_at) for z in zones]

    def test_cooldown_runs_from_the_most_recent_stop_out(self):
        """OBR-0908-01's zone had already been broken hours before it was
        published, then stopped it out again at 09-09 07:00; OBR-0909-01
        re-sold it 3 candles later. Counting from the first break would
        have let the cooldown lapse in between."""
        df = flat_df()
        bearish_block_at(df, 30)
        put(df, 32, 1996.0, 2015.0, 1995.0, 1996.0)   # first break
        put(df, 56, 1996.0, 2015.0, 1995.0, 1996.0)   # broken again later
        zones = stopped_out_zones(df, 60, atr_of(df), sl_buffer_atr=0.3, start=20)
        assert [z.stopped_at for z in zones if z.low == 1994.8] == [56]

    def test_nan_atr_never_counts_as_a_stop_out(self):
        df = flat_df()
        bearish_block_at(df, 50)
        put(df, 55, 1996.0, 2015.0, 1995.0, 1996.0)

        assert stopped_out_zones(df, 60, np.full(len(df), np.nan), sl_buffer_atr=0.3, start=40) == []


class TestGoldStrategyUsesCooldown:
    def _df(self):
        df = flat_df(120)
        bearish_block_at(df, 100)
        put(df, 105, 1996.0, 2015.0, 1995.0, 1996.0)
        retest_bearish(df, 110)
        return df.iloc[:111]

    def test_default_config_blocks_reentry(self):
        assert GoldStrategy.DEFAULT_CONFIG['reentry_cooldown_candles'] == 20
        strategy = GoldStrategy(config={'atr_period': 14})
        assert strategy.evaluate(self._df(), 110) is None

    def test_cooldown_zero_restores_old_behaviour(self):
        strategy = GoldStrategy(config={'atr_period': 14, 'reentry_cooldown_candles': 0})
        signal = strategy.evaluate(self._df(), 110)
        assert signal is not None and signal.direction == TradeDirection.SHORT

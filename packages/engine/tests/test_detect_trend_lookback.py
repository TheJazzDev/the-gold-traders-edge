"""
detect_trend(lookback=N) must only look at the last N candles.

It used to pass the windowed frame to _trend_by_swings, which ignored it and
built swing points from the whole history (self.df), so Order Block
Retest's "30-candle trend" was really "whatever the last two swings
anywhere were" — including swings far outside the window.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from analysis.technical import TechnicalAnalysis, TrendDirection


def zigzag(n, start, drift, amp=5.0, period=8):
    t = np.arange(n)
    mid = start + drift * t + amp * np.sin(2 * np.pi * t / period)
    return mid


def frame(mid):
    idx = pd.date_range('2026-01-01', periods=len(mid), freq='1h')
    return pd.DataFrame({'open': mid, 'high': mid + 0.5, 'low': mid - 0.5, 'close': mid}, index=idx)


class TestDetectTrendRespectsLookback:
    def test_old_swings_outside_the_window_are_ignored(self):
        """100 candles of zigzag uptrend, then 30 dead-flat candles (no
        swings at all). The last 30 candles have no trend."""
        up = zigzag(100, 1000, 1.0)
        flat = np.full(30, up[-1])
        ta = TechnicalAnalysis(frame(np.concatenate([up, flat])))

        assert ta.detect_trend(lookback=30) == TrendDirection.SIDEWAYS
        assert ta.detect_trend(lookback=130) == TrendDirection.UPTREND

    def test_trend_inside_the_window_is_detected(self):
        up = zigzag(100, 1000, 1.0)
        down = zigzag(40, up[-1], -1.5)
        ta = TechnicalAnalysis(frame(np.concatenate([up, down])))

        assert ta.detect_trend(lookback=40) == TrendDirection.DOWNTREND

    def test_detect_swing_points_unchanged(self):
        """The public swing-point API still scans the full frame."""
        mid = zigzag(60, 1000, 0.5)
        ta = TechnicalAnalysis(frame(mid))
        swings = ta.detect_swing_points(lookback=3, min_strength=1)
        assert len(swings) > 8
        assert swings[0].index < ta.df.index[20]


class TestOrderBlockRetestKeepsValidatedTrend:
    """OBR's confidence bonus was validated with the pre-fix behaviour —
    the last two swing highs/lows anywhere in the frame. Honouring
    lookback=30 literally cut test-slice PF from 1.57 to 1.37 (see the
    2026-09-25 ledger entry), so OBR asks for the whole frame explicitly."""

    def test_obr_asks_detect_trend_for_the_whole_frame(self, monkeypatch):
        sys.path.insert(0, str(Path(__file__).parent))
        from test_trend_gate import bullish_retest_df
        from signals.gold_strategy import GoldStrategy

        calls = []
        original = TechnicalAnalysis.detect_trend

        def spy(self, lookback=50, method="swing"):
            calls.append((lookback, len(self.df)))
            return original(self, lookback=lookback, method=method)

        monkeypatch.setattr(TechnicalAnalysis, 'detect_trend', spy)
        df = bullish_retest_df()
        assert GoldStrategy(config={'atr_period': 14}).evaluate(df, len(df) - 1) is not None
        assert calls and all(lookback == frame_len for lookback, frame_len in calls)

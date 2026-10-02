"""The weekly report's parity section, wired end to end with fakes for the
data feed and the live signals."""
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from backtesting.engine import Signal, TradeDirection
from services.weekly_parity import ParityTarget, build_weekly_parity_text, clone_strategy


class LondonOpenLong:
    """Goes long at 07:00 with 2R, like ARLB."""
    def __init__(self, config=None):
        self.config = config or {}
        self.rules_enabled = {'rule': True}
        self.calls = 0

    def evaluate(self, df, idx):
        self.calls += 1
        if not self.rules_enabled['rule'] or df.index[idx].hour != 7:
            return None
        return Signal(time=df.index[idx], direction=TradeDirection.LONG, entry_price=100.0,
                      stop_loss=95.0, take_profit=110.0, signal_name='rule', confidence=0.7)


def _candles(target, count):
    index = pd.date_range(end='2026-10-02 12:00', periods=count, freq='h')
    df = pd.DataFrame({'open': 100.0, 'high': 100.5, 'low': 99.5, 'close': 100.0, 'volume': 1.0}, index=index)
    df.loc['2026-09-30 10:00', 'high'] = 111.0  # TP for the 09-30 07:00 long
    df.loc['2026-10-01 09:00', 'low'] = 94.0  # SL for the 10-01 07:00 long
    return df


def _target(strategy):
    return ParityTarget(symbol='GBPUSD', timeframe='1h', strategy=strategy, min_rr=1.5,
                        min_confidence=0.6, expiry_hours=48, warmup=30)


def _live(when, status, pnl_pips, notes=''):
    return SimpleNamespace(symbol='GBPUSD', timeframe='1h', timestamp=datetime.fromisoformat(when),
                           direction=SimpleNamespace(value='LONG'), status=SimpleNamespace(value=status),
                           pnl_pips=pnl_pips, risk_pips=5.0, notes=notes)


def test_reports_live_and_backtest_side_by_side():
    live = [
        _live('2026-09-30 07:00', 'closed_sl', -5.0),  # live lost where the backtest won
        _live('2026-10-01 07:00', 'closed_sl', -5.0),
        _live('2026-09-20 07:00', 'closed_tp', 10.0),  # outside the week
    ]

    text = build_weekly_parity_text([_target(LondonOpenLong())], live, _candles, days=3,
                                    now=datetime(2026, 10, 2, 12, 30))

    assert 'GBPUSD: live -2.0R (2) | backtest +1.0R (3)' in text
    assert '09-30 07:00 LONG: live SL, backtest TP' in text
    assert '10-02 07:00 LONG: backtest only (open)' in text


def test_replay_never_touches_the_live_strategy():
    live_strategy = LondonOpenLong()

    build_weekly_parity_text([_target(live_strategy)], [], _candles, days=3,
                             now=datetime(2026, 10, 2, 12, 30))

    assert live_strategy.calls == 0


def test_clone_keeps_rule_toggles():
    s = LondonOpenLong()
    s.rules_enabled['rule'] = False

    assert clone_strategy(s).rules_enabled == {'rule': False}

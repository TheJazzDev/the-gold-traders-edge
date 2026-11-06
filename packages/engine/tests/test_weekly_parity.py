"""The weekly report's parity section, wired end to end with fakes for the
data feed and the live signals."""
import sys
from datetime import datetime, timedelta
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


def _live(when, status, pnl_pips, notes='', closed_at=None, symbol='GBPUSD'):
    return SimpleNamespace(symbol=symbol, timeframe='1h', timestamp=datetime.fromisoformat(when),
                           direction=SimpleNamespace(value='LONG'), status=SimpleNamespace(value=status),
                           pnl_pips=pnl_pips, risk_pips=5.0, notes=notes,
                           closed_at=datetime.fromisoformat(closed_at) if closed_at else None)


def test_reports_live_and_backtest_side_by_side():
    live = [
        _live('2026-09-30 07:00', 'closed_sl', -5.0),  # live lost where the backtest won
        _live('2026-10-01 07:00', 'closed_sl', -5.0),
        _live('2026-09-20 07:00', 'closed_tp', 10.0, closed_at='2026-09-21 09:00'),  # outside the week
    ]

    text = build_weekly_parity_text([_target(LondonOpenLong())], live, _candles, days=3,
                                    now=datetime(2026, 10, 2, 12, 30))

    assert 'GBPUSD: live -2.0R (2) | backtest +1.0R (3)' in text
    assert '09-30 07:00 LONG: live SL, backtest TP' in text
    assert '10-02 07:00 LONG: backtest only (open)' in text


NOW = datetime(2026, 10, 2, 12, 30)  # with days=3, the window opens 09-29 12:30


def _text(live):
    return build_weekly_parity_text([_target(LondonOpenLong())], live, _candles, days=3, now=NOW)


def test_replay_waits_for_a_live_trade_carried_into_the_window():
    # Opened before the window, closed 09-30 09:00: live's one-open gate
    # blocked 09-30 07:00, so that entry isn't a trade live missed.
    carried = _live('2026-09-29 07:00', 'closed_tp', 10.0, closed_at='2026-09-30 09:00')

    text = _text([carried])

    assert '09-30 07:00' not in text
    assert '10-01 07:00 LONG: backtest only (SL)' in text


def test_replay_can_enter_on_the_candle_a_carried_trade_closes():
    carried = _live('2026-09-29 07:00', 'closed_sl', -5.0, closed_at='2026-10-01 07:00')

    assert '10-01 07:00 LONG: backtest only (SL)' in _text([carried])


def test_no_replay_while_a_carried_trade_is_still_open():
    text = _text([_live('2026-09-29 07:00', 'pending', None)])

    assert 'backtest only' not in text


def test_a_carried_trade_only_blocks_its_own_symbol():
    carried = _live('2026-09-29 07:00', 'pending', None, symbol='EURUSD')

    assert '09-30 07:00 LONG: backtest only (TP)' in _text([carried])


def test_a_cancelled_trade_does_not_block_the_replay():
    # Cancelled by hand, not expired: live_outcome drops it, and it left no position.
    cancelled = _live('2026-09-29 07:00', 'cancelled', None, closed_at='2026-10-01 09:00')

    assert '09-30 07:00 LONG: backtest only (TP)' in _text([cancelled])


def test_replay_never_touches_the_live_strategy():
    live_strategy = LondonOpenLong()

    build_weekly_parity_text([_target(live_strategy)], [], _candles, days=3,
                             now=datetime(2026, 10, 2, 12, 30))

    assert live_strategy.calls == 0


def test_clone_keeps_rule_toggles():
    s = LondonOpenLong()
    s.rules_enabled['rule'] = False

    assert clone_strategy(s).rules_enabled == {'rule': False}


def test_a_trade_closing_after_the_last_candle_leaves_the_report_intact():
    carried = _live('2026-09-29 07:00', 'closed_tp', 10.0, closed_at='2026-10-02 13:00')

    assert 'No trades live or in the backtest.' in _text([carried])


def test_weekly_report_sees_a_trade_opened_before_its_week(tmp_path, monkeypatch):
    """ARLB has no expiry, so a trade open at the start of the week can be
    much older than the week. The report must load it to know it's open."""
    import run_multi_timeframe_service as svc_module
    from database.connection import DatabaseManager
    from database.models import Base, Signal as SignalRow, SignalDirection, SignalStatus

    db_url = f"sqlite:///{tmp_path / 'parity.db'}"
    db = DatabaseManager(db_url)
    Base.metadata.create_all(db.engine)
    with db.session_scope() as session:
        session.add(SignalRow(
            timestamp=datetime.utcnow() - timedelta(days=30), symbol='EURUSD', timeframe='1h',
            strategy_name='Asian Range London Breakout', direction=SignalDirection.LONG,
            entry_price=1.1, stop_loss=1.09, take_profit=1.12, confidence=0.6,
            status=SignalStatus.PENDING))

    seen = []
    monkeypatch.setattr(svc_module, 'build_weekly_parity_text',
                        lambda targets, live, fetch, days: seen.extend(s.symbol for s in live) or 'text')
    service = svc_module.MultiTimeframeService.__new__(svc_module.MultiTimeframeService)
    service.database_url, service.workers = db_url, {}

    assert service._build_parity_section() == 'text'
    assert seen == ['EURUSD']

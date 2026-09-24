"""Telegram message formatting: symbol-aware pips/prices + lot-size $ table."""

from datetime import datetime
from types import SimpleNamespace

from signals.subscribers.telegram_messages import (
    format_close_message,
    format_signal_message,
)


def _signal(**kw):
    base = dict(
        direction="LONG", symbol="EURUSD", strategy_name="Asian Range London Breakout",
        timeframe="1h", timestamp=datetime(2026, 9, 24, 7),
        entry_price=1.1397310495376587, stop_loss=1.1369849562644958,
        take_profit=1.1452232360839845, risk_reward_ratio=2.0, confidence=0.6,
        notes="", reference_id="ARLB-0924-01",
    )
    base.update(kw)
    return SimpleNamespace(**base)


class TestSignalMessage:
    def test_eurusd_risk_in_real_pips(self):
        msg = format_signal_message(_signal())
        assert "Risk: 27.5 pips" in msg
        assert "Reward: 54.9 pips" in msg

    def test_eurusd_prices_at_five_decimals(self):
        msg = format_signal_message(_signal())
        assert "Entry: 1.13973" in msg
        assert "Stop Loss: 1.13698" in msg

    def test_gold_lot_size_table(self):
        msg = format_signal_message(_signal(
            symbol="XAUUSD", direction="SHORT", entry_price=4327.1,
            stop_loss=4351.43, take_profit=4278.44,
        ))
        # risk $24.33/oz, reward $48.66/oz
        assert "0.01 lot: -$24.33 / +$48.66" in msg
        assert "1.00 lot: -$2,433.00 / +$4,866.00" in msg


class TestCloseMessage:
    def _close(self, **kw):
        args = dict(
            reference_id="OBR-0923-01", symbol="XAUUSD", direction="SHORT",
            strategy_name="Order Block Retest", entry_price=4327.10009765625,
            exit_price=4278.4374912806925, outcome="closed_tp", r_multiple=2.0,
        )
        args.update(kw)
        return format_close_message(**args)

    def test_gold_tp_reports_pips_and_dollars(self):
        msg = self._close()
        assert "+486.6 pips" in msg
        assert "0.01 lot: +$48.66" in msg
        assert "0.10 lot: +$486.63" in msg

    def test_sl_is_negative(self):
        msg = self._close(outcome="closed_sl", exit_price=4351.43, r_multiple=-1.0)
        assert "0.01 lot: -$24.33" in msg

    def test_eurusd_sl(self):
        msg = self._close(
            symbol="EURUSD", direction="LONG", entry_price=1.1397310495376587,
            exit_price=1.1369849562644958, outcome="closed_sl", r_multiple=-1.0,
        )
        assert "-27.5 pips" in msg
        assert "Exit: 1.13698" in msg
        assert "0.01 lot: -$2.75" in msg
        assert "1.00 lot: -$274.61" in msg

    def test_expiry_has_no_pnl_table(self):
        msg = self._close(outcome="expired", exit_price=None, r_multiple=None)
        assert "lot:" not in msg

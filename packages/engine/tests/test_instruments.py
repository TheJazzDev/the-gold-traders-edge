"""
Per-symbol pip/contract math.

Pip size used to be hardcoded as gold's 0.1 (`* 10`) everywhere, so the
first live EURUSD signal (ARLB-0924-01, entry 1.13973 / SL 1.13698) was
published with "Risk: 0.0 pips" — the raw 0.00275 price gap times 10 —
instead of 27.5 pips.
"""

from datetime import datetime
from types import SimpleNamespace

import pytest

from instruments import (
    format_price,
    lot_size_pnl,
    pip_size,
    price_to_pips,
    usd_pnl,
)
from signals.realtime_generator import SignalValidator
from backtesting.engine import Signal as StrategySignal, TradeDirection
from database.models import Signal, SignalDirection


class TestPipSize:
    def test_gold_pip_is_ten_cents(self):
        assert pip_size("XAUUSD") == 0.1

    @pytest.mark.parametrize("symbol", ["EURUSD", "GBPUSD", "eurusd"])
    def test_major_pip_is_one_ten_thousandth(self, symbol):
        assert pip_size(symbol) == 0.0001

    def test_unknown_symbol_raises(self):
        with pytest.raises(KeyError):
            pip_size("BTCUSD")


class TestPriceToPips:
    def test_live_eurusd_signal(self):
        # ARLB-0924-01 as published
        assert price_to_pips("EURUSD", 1.1397310495376587 - 1.1369849562644958) == pytest.approx(27.46, abs=0.01)

    def test_live_gold_signal_unchanged(self):
        # OBR-0923-01: TP distance published as 486.6 pips
        assert price_to_pips("XAUUSD", 4327.10009765625 - 4278.4374912806925) == pytest.approx(486.63, abs=0.01)


class TestUsdPnl:
    def test_gold_hundred_oz_per_lot(self):
        # $48.66 move on 0.01 lot (1 oz) = $48.66
        assert usd_pnl("XAUUSD", 48.66, 0.01) == pytest.approx(48.66)
        assert usd_pnl("XAUUSD", 48.66, 1.0) == pytest.approx(4866.0)

    def test_eurusd_ten_dollars_per_pip_per_lot(self):
        assert usd_pnl("EURUSD", 0.0010, 1.0) == pytest.approx(100.0)
        assert usd_pnl("EURUSD", 0.0010, 0.01) == pytest.approx(1.0)

    def test_lot_size_table_is_signed(self):
        rows = lot_size_pnl("XAUUSD", -24.33)
        assert rows[0] == (0.01, pytest.approx(-24.33))
        assert all(v < 0 for _, v in rows)


class TestFormatPrice:
    def test_gold_two_decimals(self):
        assert format_price("XAUUSD", 4310.0) == "4310.00"

    def test_eurusd_five_decimals(self):
        # Was rendered "$1.14" for both entry and stop — indistinguishable
        assert format_price("EURUSD", 1.1397310495376587) == "1.13973"


def _strategy_signal(entry, sl, tp, direction=TradeDirection.LONG):
    return StrategySignal(
        time=datetime(2026, 9, 24, 7), direction=direction,
        entry_price=entry, stop_loss=sl, take_profit=tp,
        signal_name="t",
    )


class TestPipsAreSymbolAwareEverywhere:
    def test_validator_risk_reward_eurusd(self):
        sig = _strategy_signal(1.13973, 1.13698, 1.14522)
        risk, reward, rr = SignalValidator.compute_risk_reward(sig, "EURUSD")
        assert risk == pytest.approx(27.5, abs=0.01)
        assert reward == pytest.approx(54.9, abs=0.01)
        assert rr == pytest.approx(2.0, abs=0.01)

    def test_validator_risk_reward_gold(self):
        sig = _strategy_signal(2000.0, 1990.0, 2020.0)
        risk, reward, _ = SignalValidator.compute_risk_reward(sig, "XAUUSD")
        assert (risk, reward) == (pytest.approx(100.0), pytest.approx(200.0))

    def test_model_calculate_risk_reward_eurusd(self):
        s = Signal(symbol="EURUSD", direction=SignalDirection.LONG,
                   entry_price=1.13973, stop_loss=1.13698, take_profit=1.14522)
        s.calculate_risk_reward()
        assert s.risk_pips == pytest.approx(27.5, abs=0.01)

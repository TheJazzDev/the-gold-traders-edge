"""USDJPY is a JPY-quoted pair, so a price move is yen, not dollars. It runs
signals only until the demo order path is proven."""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import run_multi_timeframe_service as svc
from data.realtime_feed import YahooFinanceDataFeed
from instruments import format_price, lot_size_pnl, price_to_pips, usd_pnl, usd_per_quote
from signals.subscribers.telegram_messages import format_close_message, format_signal_message
from trading.mt5_config import MT5Config, MT5ConnectionType
from trading.position_calculator import PositionCalculator

JPY_INFO = {"point": 0.001, "digits": 3, "trade_contract_size": 100_000,
            "volume_step": 0.01, "volume_min": 0.01, "volume_max": 100.0}
EUR_INFO = {**JPY_INFO, "point": 0.00001, "digits": 5}


def calculator():
    return PositionCalculator(MT5Config(connection_type=MT5ConnectionType.METAAPI))


class TestInstrument:
    def test_pip_is_one_hundredth(self):
        assert price_to_pips("USDJPY", 0.77) == pytest.approx(77.0)

    def test_prices_show_three_decimals(self):
        assert format_price("USDJPY", 150.1234) == "150.123"

    def test_usd_quoted_pairs_need_no_conversion(self):
        assert usd_per_quote("EURUSD", 1.15) == 1.0
        assert usd_per_quote("XAUUSD", 4000.0) == 1.0

    def test_yen_converts_at_the_price(self):
        assert usd_per_quote("USDJPY", 150.0) == pytest.approx(1 / 150)

    def test_one_lot_pip_is_about_seven_dollars_at_150(self):
        assert usd_pnl("USDJPY", 0.01, 1.0, price=150.0) == pytest.approx(6.67, abs=0.01)

    def test_yen_pnl_without_a_price_refuses_to_guess(self):
        with pytest.raises(ValueError):
            usd_pnl("USDJPY", 0.01, 1.0)
        with pytest.raises(ValueError):
            lot_size_pnl("USDJPY", 0.01)

    def test_lot_rows_use_the_price(self):
        rows = dict(lot_size_pnl("USDJPY", -0.75, price=150.0))
        assert rows[1.0] == pytest.approx(-500.0)


class TestTelegram:
    def test_signal_dollars_are_converted_from_yen(self):
        signal = SimpleNamespace(
            symbol="USDJPY", direction="LONG", confidence=0.6, entry_price=150.0,
            stop_loss=149.25, take_profit=151.5, timestamp=datetime(2026, 11, 9, 8),
            strategy_name="Asian Range London Breakout", timeframe="1h",
            risk_reward_ratio=2.0, notes="", reference_id="ARLB-1109-01")
        text = format_signal_message(signal)
        assert "Entry: 150.000" in text
        assert "Risk: 75.0 pips" in text
        # 1 lot: 0.75 yen x 100k = 75,000 yen at 149.25; 1.5 x 100k at 151.5
        assert "1.00 lot: -$502.51 / +$990.10" in text

    def test_close_dollars_are_converted_at_the_exit_price(self):
        text = format_close_message(
            reference_id="ARLB-1109-01", symbol="USDJPY", direction="LONG",
            strategy_name="Asian Range London Breakout", entry_price=150.0,
            exit_price=151.5, outcome="closed_tp", r_multiple=2.0)
        assert "1.00 lot: +$990.10" in text


class TestSizing:
    def test_risk_is_a_dollar_amount_on_a_yen_pair(self):
        # $25 risk on a 0.75 yen stop at 149.25: 25 x 149.25 / (0.75 x 100k)
        lots = calculator().calculate_lot_size(
            account_balance=2500, entry_price=150.0, stop_loss=149.25,
            symbol_info=JPY_INFO, symbol="USDJPY", risk_percentage=0.01)
        assert lots == pytest.approx(0.05)

    def test_risk_amount_round_trips_in_dollars(self):
        risk = calculator().calculate_risk_amount(
            lot_size=0.05, entry_price=150.0, stop_loss=149.25,
            symbol_info=JPY_INFO, symbol="USDJPY")
        assert risk == pytest.approx(25.13, abs=0.01)

    def test_usd_quoted_sizing_is_unchanged(self):
        lots = calculator().calculate_lot_size(
            account_balance=2500, entry_price=1.15, stop_loss=1.1475,
            symbol_info=EUR_INFO, symbol="EURUSD", risk_percentage=0.01)
        assert lots == pytest.approx(0.1)

    def test_margin_on_a_yen_pair_is_measured_in_dollars(self):
        # 1 lot is $100,000. At 1:500 that's $200 margin, not 150x that.
        ok, error = calculator().validate_position_size(
            lot_size=1.0, account_balance=1000, account_leverage=500,
            symbol_info=JPY_INFO, entry_price=150.0, symbol="USDJPY")
        assert ok, error

    def test_an_unknown_symbol_fails_instead_of_guessing(self):
        with pytest.raises(KeyError):
            calculator().calculate_lot_size(
                account_balance=2500, entry_price=150.0, stop_loss=149.25,
                symbol_info=JPY_INFO, symbol="CHFJPY", risk_percentage=0.01)


class TestWorker:
    def spec(self):
        return next(s for s in svc.WORKER_SPECS if s.symbol == "USDJPY")

    def test_runs_the_forex_strategy_on_its_own_config(self):
        spec = self.spec()
        assert spec.strategy_class is svc.ForexSessionStrategy
        assert spec.tuned_config_filename == "usdjpy_1h.json"

    def test_is_signals_only(self):
        assert self.spec().orders_enabled is False

    def test_the_existing_markets_can_still_trade(self):
        others = [s for s in svc.WORKER_SPECS if s.symbol != "USDJPY"]
        assert len(others) == 3 and all(s.orders_enabled for s in others)

    def test_never_connects_to_the_broker_even_with_trading_on(self, monkeypatch):
        connect = MagicMock()
        monkeypatch.setattr(svc, "create_mt5_connection", connect)
        worker = svc.TimeframeWorker.__new__(svc.TimeframeWorker)
        worker.spec = self.spec()
        worker.enable_trading = True
        worker.mt5_config = MagicMock()
        worker.generator = MagicMock()
        worker._attach_trading()
        connect.assert_not_called()
        worker.generator.add_subscriber.assert_not_called()

    def test_feed_uses_the_real_usdjpy_ticker(self):
        feed = YahooFinanceDataFeed(symbol="USDJPY", timeframe="1h", lookback_periods=10)
        assert feed.ticker_map["USDJPY"] == "USDJPY=X"

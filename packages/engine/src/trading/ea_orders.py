"""
The server side of the MT5 Expert Advisor link.

The EA runs inside the broker's terminal and asks for orders every few
seconds. It gets a signal once: when it is new, trading is LIVE, and nothing
has been recorded against it. The EA sizes and places the order itself (it
has the broker's contract data) and reports back.

Every doubt is settled as "no order": a missed trade is the safe failure.
"""
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session

from database.broker_fill import BrokerFill
from database.models import Signal, SignalStatus
from database.settings_repository import SettingsRepository
from trading.trading_switch import TradingMode, resolve_trading_mode

DEFAULT_ORDER_SYMBOLS = ("XAUUSD", "EURUSD", "GBPUSD")  # USDJPY is signals only
DEFAULT_RISK_PER_TRADE = 0.0025
MAX_RISK_PER_TRADE = 0.02
DEFAULT_MAX_SIGNAL_AGE_MINUTES = 15
MAX_INT32 = 2**31 - 1  # signals.mt5_ticket is a 32-bit integer
MAX_REASON_LENGTH = 300


@dataclass(frozen=True)
class EaOrder:
    signal_id: int
    symbol: str
    direction: str  # LONG or SHORT
    entry_price: float
    stop_loss: float
    take_profit: float
    reference_id: str


def order_symbols() -> tuple:
    raw = os.getenv("EA_ORDER_SYMBOLS")
    if not raw:
        return DEFAULT_ORDER_SYMBOLS
    return tuple(s.strip().upper() for s in raw.split(",") if s.strip())


def risk_per_trade() -> Optional[float]:
    """Fraction of balance to risk, or None when the setting can't be trusted."""
    try:
        risk = float(os.getenv("MAX_RISK_PER_TRADE", DEFAULT_RISK_PER_TRADE))
    except ValueError:
        return None
    return risk if 0 < risk <= MAX_RISK_PER_TRADE else None


def max_signal_age() -> timedelta:
    try:
        minutes = float(os.getenv("EA_MAX_SIGNAL_AGE_MINUTES", DEFAULT_MAX_SIGNAL_AGE_MINUTES))
    except ValueError:
        minutes = DEFAULT_MAX_SIGNAL_AGE_MINUTES
    return timedelta(minutes=minutes)


def read_trading_mode(session: Session) -> TradingMode:
    try:
        repo = SettingsRepository(session)
        return resolve_trading_mode(
            auto_trading_enabled=repo.get('auto_trading_enabled', default=False) is True,
            dry_run_mode=repo.get('dry_run_mode', default=True) is not False,
        )
    except Exception:
        return TradingMode.OFF


def pending_orders(session: Session, mode: TradingMode, now: datetime) -> List[EaOrder]:
    """Signals the EA should place right now, oldest first."""
    if mode is not TradingMode.LIVE:
        return []
    filled = session.query(BrokerFill.signal_id)
    rows = (
        session.query(Signal)
        .filter(
            Signal.status == SignalStatus.PENDING,
            Signal.error_message.is_(None),
            Signal.symbol.in_(order_symbols()),
            Signal.created_at >= now - max_signal_age(),
            Signal.id.notin_(filled),
        )
        .order_by(Signal.id)
        .all()
    )
    return [
        EaOrder(
            signal_id=row.id,
            symbol=row.symbol,
            direction=row.direction.value,
            entry_price=row.entry_price,
            stop_loss=row.stop_loss,
            take_profit=row.take_profit,
            reference_id=row.reference_id or "",
        )
        for row in rows
    ]


def format_poll_response(mode: TradingMode, risk: Optional[float], orders: List[EaOrder]) -> str:
    """Plain lines, because MQL5 has no JSON parser. Prices keep full
    precision; the EA rounds to the broker's digits."""
    lines = [f"MODE|{mode.value}", f"RISK|{risk if risk is not None else 0}"]
    if risk is not None:
        lines += [
            f"ORDER|{o.signal_id}|{o.symbol}|{o.direction}|{o.entry_price!r}|"
            f"{o.stop_loss!r}|{o.take_profit!r}|{o.reference_id}"
            for o in orders
        ]
    return "\n".join(lines) + "\n"


def record_fill(session: Session, signal_id: int, ticket: int, lots: float, entry_price: float,
                stop_loss: float, take_profit: float, broker_symbol: str,
                account: Optional[str], now: datetime) -> bool:
    """False when the signal doesn't exist. Safe to call twice: the EA
    repeats a report until it gets an answer."""
    signal = session.query(Signal).filter(Signal.id == signal_id).first()
    if signal is None:
        return False
    if session.query(BrokerFill).filter(BrokerFill.signal_id == signal_id).first():
        return True

    session.add(BrokerFill(
        signal_id=signal_id, ticket=ticket, account=account, broker_symbol=broker_symbol,
        lots=lots, entry_price=entry_price, stop_loss=stop_loss, take_profit=take_profit,
        opened_at=now,
    ))
    signal.actual_entry = entry_price
    signal.executed_at = now
    if ticket <= MAX_INT32:
        signal.mt5_ticket = ticket
    else:
        signal.notes = f"{signal.notes or ''} [mt5 ticket {ticket}]".strip()
    if signal.status == SignalStatus.PENDING:  # never reopen a signal the tracker closed
        signal.status = SignalStatus.ACTIVE
    session.commit()
    return True


def record_reject(session: Session, signal_id: int, reason: str) -> bool:
    """The signal stays open on paper; the note stops it being offered again."""
    signal = session.query(Signal).filter(Signal.id == signal_id).first()
    if signal is None:
        return False
    signal.error_message = f"EA: {reason}"[:MAX_REASON_LENGTH]
    session.commit()
    return True


def record_close(session: Session, signal_id: int, exit_price: float, profit: float,
                 close_reason: str, now: datetime) -> bool:
    """Only the broker's side is written; the paper outcome stays the tracker's."""
    fill = session.query(BrokerFill).filter(BrokerFill.signal_id == signal_id).first()
    if fill is None:
        return False
    if fill.closed_at is None:
        fill.exit_price = exit_price
        fill.profit = profit
        fill.close_reason = close_reason[:20]
        fill.closed_at = now
        session.commit()
    return True

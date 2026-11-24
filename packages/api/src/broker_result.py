"""
The broker's side of a signal, for showing next to the paper record.

The two are never merged (see database/broker_fill.py): the paper outcome is
what the backtest comparison runs on, the broker fill is what the account
really got.
"""
from typing import Dict, Iterable, Optional

from sqlalchemy.orm import Session

from database.broker_fill import BrokerFill, ensure_broker_fills_table

from src.models.signal import BrokerFillResponse


def broker_r_multiple(direction: str, entry: float, stop: float,
                      exit_price: Optional[float]) -> Optional[float]:
    """Result in units of the risk actually taken, from the broker's own
    prices. Costs (swap, commission) are in `profit`, not here."""
    risk = abs(entry - stop)
    if exit_price is None or risk == 0:
        return None
    move = exit_price - entry if direction == "LONG" else entry - exit_price
    return move / risk


def broker_fills_for(db: Session, signal_ids: Iterable[int]) -> Dict[int, BrokerFill]:
    ids = list(signal_ids)
    if not ids:
        return {}
    ensure_broker_fills_table(db.get_bind())
    rows = db.query(BrokerFill).filter(BrokerFill.signal_id.in_(ids)).all()
    return {row.signal_id: row for row in rows}


def to_broker_response(fill: Optional[BrokerFill], direction: str) -> Optional[BrokerFillResponse]:
    if fill is None:
        return None
    return BrokerFillResponse(
        ticket=fill.ticket,
        lots=fill.lots,
        entry_price=fill.entry_price,
        stop_loss=fill.stop_loss,
        take_profit=fill.take_profit,
        opened_at=fill.opened_at,
        exit_price=fill.exit_price,
        profit=fill.profit,
        close_reason=fill.close_reason,
        closed_at=fill.closed_at,
        r_multiple=broker_r_multiple(direction, fill.entry_price, fill.stop_loss, fill.exit_price),
    )

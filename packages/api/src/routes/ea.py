"""
Endpoints for the MT5 Expert Advisor (packages/mt5-ea).

The EA polls for orders and reports fills, rejections and closes. The rules
live in the engine's trading/ea_orders.py; this file is only the HTTP layer.
"""
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

engine_src = Path(__file__).parent.parent.parent.parent / "engine" / "src"
sys.path.insert(0, str(engine_src))

from database.broker_fill import BrokerFill, ensure_broker_fills_table
from trading import ea_orders

from src.database import get_db
from src.ea_auth import require_ea_key

router = APIRouter(prefix="/v1/ea", tags=["ea"], dependencies=[Depends(require_ea_key)])

# Last poll, kept in memory: enough to tell whether the terminal is online.
_last_poll: dict = {}


class PollRequest(BaseModel):
    account: Optional[str] = Field(default=None, max_length=40)
    server: Optional[str] = Field(default=None, max_length=80)
    balance: Optional[float] = None
    equity: Optional[float] = None
    open_positions: Optional[int] = None


class FillReport(BaseModel):
    ticket: int = Field(gt=0)
    lots: float = Field(gt=0)
    entry_price: float = Field(gt=0)
    stop_loss: float = Field(gt=0)
    take_profit: float = Field(gt=0)
    broker_symbol: str = Field(min_length=1, max_length=30)
    account: Optional[str] = Field(default=None, max_length=40)


class RejectReport(BaseModel):
    reason: str = Field(min_length=1, max_length=300)


class CloseReport(BaseModel):
    exit_price: float = Field(gt=0)
    profit: float
    close_reason: str = Field(min_length=1, max_length=20)


def _ready(db: Session) -> None:
    ensure_broker_fills_table(db.get_bind())


def _known(found: bool) -> dict:
    if not found:
        raise HTTPException(status_code=404, detail="Unknown signal")
    return {"ok": True}


@router.post("/poll", response_class=PlainTextResponse)
def poll(body: PollRequest, db: Session = Depends(get_db)) -> str:
    _ready(db)
    now = datetime.utcnow()
    _last_poll.clear()
    _last_poll.update(body.model_dump(), at=now.isoformat() + "Z")
    mode = ea_orders.read_trading_mode(db)
    orders = ea_orders.pending_orders(db, mode, now)
    return ea_orders.format_poll_response(mode, ea_orders.risk_per_trade(), orders)


@router.post("/orders/{signal_id}/fill")
def report_fill(signal_id: int, body: FillReport, db: Session = Depends(get_db)) -> dict:
    _ready(db)
    return _known(ea_orders.record_fill(db, signal_id, now=datetime.utcnow(), **body.model_dump()))


@router.post("/orders/{signal_id}/reject")
def report_reject(signal_id: int, body: RejectReport, db: Session = Depends(get_db)) -> dict:
    return _known(ea_orders.record_reject(db, signal_id, body.reason))


@router.post("/orders/{signal_id}/close")
def report_close(signal_id: int, body: CloseReport, db: Session = Depends(get_db)) -> dict:
    _ready(db)
    return _known(ea_orders.record_close(db, signal_id, now=datetime.utcnow(), **body.model_dump()))


@router.get("/status")
def status(db: Session = Depends(get_db)) -> dict:
    """Is the terminal online, and what has it done."""
    _ready(db)
    fills = db.query(BrokerFill).order_by(BrokerFill.id.desc()).limit(20).all()
    return {
        "mode": ea_orders.read_trading_mode(db).value,
        "risk_per_trade": ea_orders.risk_per_trade(),
        "order_symbols": list(ea_orders.order_symbols()),
        "last_poll": dict(_last_poll) or None,
        "fills": [
            {
                "signal_id": f.signal_id, "ticket": f.ticket, "broker_symbol": f.broker_symbol,
                "lots": f.lots, "entry_price": f.entry_price, "stop_loss": f.stop_loss,
                "take_profit": f.take_profit, "opened_at": f.opened_at,
                "exit_price": f.exit_price, "profit": f.profit,
                "close_reason": f.close_reason, "closed_at": f.closed_at,
            }
            for f in fills
        ],
    }

"""
What the broker actually did with a signal.

Kept apart from the signals table on purpose: a signal's status, exit and R
are the paper record, closed from Yahoo candles by the outcome tracker. The
demo run exists to compare that record with real fills, so the two must not
overwrite each other.
"""
from sqlalchemy import BigInteger, Column, DateTime, Float, Integer, String

from database.models import Base


class BrokerFill(Base):
    __tablename__ = "broker_fills"

    id = Column(Integer, primary_key=True, autoincrement=True)
    signal_id = Column(Integer, nullable=False, unique=True, index=True)
    ticket = Column(BigInteger, nullable=False)  # MT5 tickets outgrow 32 bits
    account = Column(String(40), nullable=True)
    broker_symbol = Column(String(30), nullable=False)
    lots = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False)
    take_profit = Column(Float, nullable=False)
    opened_at = Column(DateTime, nullable=False)

    exit_price = Column(Float, nullable=True)
    profit = Column(Float, nullable=True)  # account currency, after commission and swap
    close_reason = Column(String(20), nullable=True)  # sl, tp, manual, other
    closed_at = Column(DateTime, nullable=True)


def ensure_broker_fills_table(engine) -> None:
    """Nothing runs migrations in the deploy path (see models.py), so the
    table is created on demand."""
    BrokerFill.__table__.create(bind=engine, checkfirst=True)

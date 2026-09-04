"""
Database models for trading signals and performance tracking.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, Text, create_engine, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime
import enum

Base = declarative_base()


class SignalDirection(enum.Enum):
    """Signal direction enum."""
    LONG = "LONG"
    SHORT = "SHORT"


class SignalStatus(enum.Enum):
    """Signal status enum."""
    PENDING = "pending"       # Signal generated but not executed
    ACTIVE = "active"         # Trade executed and open
    CLOSED_TP = "closed_tp"   # Closed at take profit
    CLOSED_SL = "closed_sl"   # Closed at stop loss
    CLOSED_MANUAL = "closed_manual"  # Manually closed
    CANCELLED = "cancelled"   # Signal cancelled before execution


class Signal(Base):
    """
    Trading signal model.

    Stores both the signal details and the actual trade performance.
    """
    __tablename__ = "signals"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Human-readable reference (e.g. "OBR-0904-01") — see database/reference_id.py.
    # Nullable: signals created before this column existed have none, and
    # ensure_signal_reference_id_column() adds this column to an
    # already-running database without backfilling old rows.
    reference_id = Column(String(30), unique=True, index=True, nullable=True)

    # Signal metadata
    timestamp = Column(DateTime, nullable=False, index=True)
    symbol = Column(String(10), nullable=False, default="XAUUSD")
    timeframe = Column(String(5), nullable=False, default="4H")
    strategy_name = Column(String(50), nullable=False, default="Momentum Equilibrium")

    # Signal details
    direction = Column(Enum(SignalDirection), nullable=False)
    entry_price = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False)
    take_profit = Column(Float, nullable=False)
    confidence = Column(Float, nullable=True)  # 0.0 to 1.0

    # Risk metrics
    risk_pips = Column(Float, nullable=True)      # Distance to SL in pips
    reward_pips = Column(Float, nullable=True)    # Distance to TP in pips
    risk_reward_ratio = Column(Float, nullable=True)

    # Trade execution (filled when trade is placed)
    status = Column(Enum(SignalStatus), nullable=False, default=SignalStatus.PENDING, index=True)
    mt5_ticket = Column(Integer, nullable=True)   # MT5 order ticket number
    actual_entry = Column(Float, nullable=True)   # Actual entry price (may differ due to slippage)
    actual_exit = Column(Float, nullable=True)    # Actual exit price

    # Performance tracking
    pnl = Column(Float, nullable=True)            # Profit/Loss in dollars
    pnl_pct = Column(Float, nullable=True)        # P&L as percentage
    pnl_pips = Column(Float, nullable=True)       # P&L in pips

    # Timestamps
    executed_at = Column(DateTime, nullable=True)  # When trade was executed
    closed_at = Column(DateTime, nullable=True)    # When trade was closed
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    # Notes and metadata
    notes = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)   # If execution failed

    def __repr__(self):
        return f"<Signal(id={self.id}, {self.direction.value} {self.symbol} @ {self.entry_price}, status={self.status.value})>"

    @property
    def is_open(self):
        """Check if trade is currently open."""
        return self.status == SignalStatus.ACTIVE

    @property
    def is_closed(self):
        """Check if trade is closed."""
        return self.status in [SignalStatus.CLOSED_TP, SignalStatus.CLOSED_SL, SignalStatus.CLOSED_MANUAL]

    @property
    def is_winner(self):
        """Check if trade was profitable."""
        return self.is_closed and self.pnl and self.pnl > 0

    def calculate_risk_reward(self):
        """Calculate and set risk/reward metrics."""
        if self.direction == SignalDirection.LONG:
            self.risk_pips = (self.entry_price - self.stop_loss) * 10
            self.reward_pips = (self.take_profit - self.entry_price) * 10
        else:
            self.risk_pips = (self.stop_loss - self.entry_price) * 10
            self.reward_pips = (self.entry_price - self.take_profit) * 10

        if self.risk_pips > 0:
            self.risk_reward_ratio = self.reward_pips / self.risk_pips

    def to_dict(self):
        """Convert signal to dictionary."""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'strategy': self.strategy_name,
            'direction': self.direction.value,
            'entry_price': self.entry_price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'confidence': self.confidence,
            'status': self.status.value,
            'pnl': self.pnl,
            'pnl_pct': self.pnl_pct,
            'risk_reward_ratio': self.risk_reward_ratio,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


# Database initialization function
def init_database(database_url: str = "sqlite:///signals.db"):
    """
    Initialize the database and create all tables.

    Args:
        database_url: SQLAlchemy database URL
    """
    engine = create_engine(database_url, echo=False)
    Base.metadata.create_all(engine)
    ensure_signal_reference_id_column(engine)
    return engine


def ensure_signal_reference_id_column(engine):
    """
    Base.metadata.create_all() only creates tables that don't exist yet — it
    never alters an existing table's columns. There's no active migration
    runner in this codebase (the alembic/ scaffolding isn't invoked anywhere
    in the deploy path), so adding a column to the already-running
    production `signals` table needs this idempotent check-and-alter
    instead, run every time the schema is initialized.
    """
    inspector = inspect(engine)
    if 'signals' not in inspector.get_table_names():
        return
    columns = {c['name'] for c in inspector.get_columns('signals')}
    if 'reference_id' in columns:
        return
    with engine.begin() as conn:
        conn.execute(text('ALTER TABLE signals ADD COLUMN reference_id VARCHAR(30)'))


if __name__ == "__main__":
    # Test database creation
    print("Creating database schema...")
    engine = init_database("sqlite:///test_signals.db")
    print("✅ Database schema created successfully")
    print(f"Tables: {Base.metadata.tables.keys()}")

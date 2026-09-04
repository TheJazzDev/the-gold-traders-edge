"""
Regression coverage for ensure_signal_reference_id_column(): the same
"Base.metadata.create_all() never alters an existing table" gap already hit
once this session for the settings table's metadata. init_database() must
patch an already-existing `signals` table (as production's is) to add the
reference_id column, not just skip it because the table already exists.
"""
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from database.models import Base, Signal, SignalDirection, SignalStatus, ensure_signal_reference_id_column


def test_adds_column_to_a_table_created_before_the_column_existed(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")

    # Simulate a production table created by an older version of the model
    # (no reference_id column) by creating the table, then dropping the
    # column SQLAlchemy just added — sqlite can't drop columns directly, so
    # instead build the legacy schema by hand.
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "CREATE TABLE signals ("
            "id INTEGER PRIMARY KEY, timestamp DATETIME NOT NULL, "
            "symbol VARCHAR(10) NOT NULL, timeframe VARCHAR(5) NOT NULL, "
            "strategy_name VARCHAR(50) NOT NULL, direction VARCHAR(10) NOT NULL, "
            "entry_price FLOAT NOT NULL, stop_loss FLOAT NOT NULL, take_profit FLOAT NOT NULL, "
            "status VARCHAR(20) NOT NULL, created_at DATETIME, updated_at DATETIME"
            ")"
        )

    columns_before = {c['name'] for c in inspect(engine).get_columns('signals')}
    assert 'reference_id' not in columns_before

    ensure_signal_reference_id_column(engine)

    columns_after = {c['name'] for c in inspect(engine).get_columns('signals')}
    assert 'reference_id' in columns_after


def test_is_a_no_op_when_the_column_already_exists(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'current.db'}")
    Base.metadata.create_all(engine)  # fresh schema already has reference_id

    ensure_signal_reference_id_column(engine)  # must not raise (e.g. duplicate column)

    columns = {c['name'] for c in inspect(engine).get_columns('signals')}
    assert 'reference_id' in columns


def test_is_a_no_op_when_the_table_does_not_exist_yet(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'empty.db'}")
    ensure_signal_reference_id_column(engine)  # must not raise

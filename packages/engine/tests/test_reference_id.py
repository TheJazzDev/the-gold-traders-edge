"""
Tests for human-readable signal reference IDs (e.g. "OBR-0904-01").

Previously signals only had an opaque numeric database id, making them hard
to reference in Telegram/conversation. Format: {RULE_CODE}-{MMDD}-{seq}.
"""
import sys
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from database.models import Base, Signal, SignalDirection, SignalStatus
from database.reference_id import generate_reference_id, rule_code


@pytest.fixture
def session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'reference_id.db'}")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    sess = SessionLocal()
    yield sess
    sess.close()


def insert_signal(session, reference_id, timestamp):
    signal = Signal(
        reference_id=reference_id,
        timestamp=timestamp,
        symbol="XAUUSD",
        timeframe="1h",
        strategy_name="Order Block Retest",
        direction=SignalDirection.SHORT,
        entry_price=2000.0,
        stop_loss=2010.0,
        take_profit=1980.0,
        status=SignalStatus.PENDING,
    )
    session.add(signal)
    session.commit()
    return signal


class TestRuleCode:
    def test_known_rules_use_their_fixed_codes(self):
        assert rule_code("Order Block Retest") == "OBR"
        assert rule_code("Momentum Equilibrium") == "ME"
        assert rule_code("London Session Breakout") == "LSB"
        assert rule_code("Golden Fibonacci") == "GF"
        assert rule_code("ATH Retest") == "ATR"

    def test_unknown_rule_falls_back_to_initialism(self):
        assert rule_code("Some New Rule") == "SNR"


class TestGenerateReferenceId:
    def test_first_signal_of_the_day_is_sequence_one(self, session):
        ref = generate_reference_id(session, "Order Block Retest", datetime(2026, 9, 4, 12, 0))
        assert ref == "OBR-0904-01"

    def test_second_signal_same_rule_same_day_increments(self, session):
        insert_signal(session, "OBR-0904-01", datetime(2026, 9, 4, 12, 0))
        ref = generate_reference_id(session, "Order Block Retest", datetime(2026, 9, 4, 14, 0))
        assert ref == "OBR-0904-02"

    def test_different_rule_same_day_has_its_own_sequence(self, session):
        insert_signal(session, "OBR-0904-01", datetime(2026, 9, 4, 12, 0))
        ref = generate_reference_id(session, "Momentum Equilibrium", datetime(2026, 9, 4, 13, 0))
        assert ref == "ME-0904-01"

    def test_same_rule_different_day_resets_sequence(self, session):
        insert_signal(session, "OBR-0904-01", datetime(2026, 9, 4, 12, 0))
        ref = generate_reference_id(session, "Order Block Retest", datetime(2026, 9, 5, 9, 0))
        assert ref == "OBR-0905-01"

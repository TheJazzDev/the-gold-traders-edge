"""
Human-readable signal reference IDs, e.g. "OBR-0904-01".

Format: {RULE_CODE}-{MMDD}-{sequence within that rule+day, zero-padded to 2}.
Lets a signal be referenced unambiguously in Telegram messages and the UI
instead of only an opaque numeric database id.
"""
from datetime import datetime

from sqlalchemy.orm import Session

from database.models import Signal

# Keyed by the exact RuleResult.rule_name strings produced by
# GoldStrategy's rules (see signals/gold_strategy.py) — this is also what
# gets stored verbatim in Signal.strategy_name.
RULE_CODES = {
    "Momentum Equilibrium": "ME",
    "London Session Breakout": "LSB",
    "Golden Fibonacci": "GF",
    "ATH Retest": "ATR",
    "Order Block Retest": "OBR",
}


def rule_code(strategy_name: str) -> str:
    """Falls back to an uppercased, punctuation-stripped initialism for any
    rule name not in RULE_CODES, so this never raises for an unknown rule."""
    if strategy_name in RULE_CODES:
        return RULE_CODES[strategy_name]
    words = [w for w in strategy_name.split() if w]
    return "".join(w[0] for w in words).upper()[:4] or "SIG"


def generate_reference_id(session: Session, strategy_name: str, when: datetime) -> str:
    """Next reference ID for this rule on this calendar day, e.g. the third
    Order Block Retest signal on Sep 4th is "OBR-0904-03"."""
    code = rule_code(strategy_name)
    date_part = when.strftime("%m%d")
    prefix = f"{code}-{date_part}-"

    existing = (
        session.query(Signal)
        .filter(Signal.reference_id.like(f"{prefix}%"))
        .count()
    )
    sequence = existing + 1
    return f"{prefix}{sequence:02d}"

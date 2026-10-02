"""
Live-vs-backtest parity: replay a window through the backtest and compare
it trade by trade with what live published.

On 2026-10-02 live stood at −5R over 17 trades while the replay of the same
period scored +5R. Every difference was plumbing, not the strategy: gold
candles evaluated before Yahoo had published their last 10 minutes, a
weekend-clock expiry, an outage, stacked signals. None of it was visible
from the weekly stats alone. Running this every week puts any such gap in
the report itself.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import pandas as pd

from backtesting.engine import TradeDirection, TradeStatus
from backtesting.live_parity import StrategyFunc, run_on_window

_REPLAY_OUTCOME = {
    TradeStatus.CLOSED_TP: 'tp',
    TradeStatus.CLOSED_SL: 'sl',
    TradeStatus.EXPIRED: 'expired',
    TradeStatus.CLOSED_MANUAL: 'open',  # still open when the data ends
}
_LIVE_OUTCOME = {'closed_tp': 'tp', 'closed_sl': 'sl', 'pending': 'open', 'active': 'open'}


@dataclass
class TradeOutcome:
    symbol: str
    time: pd.Timestamp  # entry candle's open, naive UTC — live's Signal.timestamp
    direction: str  # 'LONG' / 'SHORT'
    outcome: str  # 'tp' / 'sl' / 'expired' / 'open'
    r: Optional[float]  # resolved trades only


@dataclass
class Mismatch:
    kind: str  # 'outcome' / 'live_only' / 'replay_only'
    live: Optional[TradeOutcome]
    replay: Optional[TradeOutcome]


@dataclass
class SymbolParity:
    live: List[TradeOutcome] = field(default_factory=list)
    replay: List[TradeOutcome] = field(default_factory=list)
    mismatches: List[Mismatch] = field(default_factory=list)

    @property
    def live_r(self) -> float:
        return sum(o.r for o in self.live if o.r is not None)

    @property
    def replay_r(self) -> float:
        return sum(o.r for o in self.replay if o.r is not None)


def live_outcome(symbol, time, direction, status, pnl_pips, risk_pips, notes) -> Optional[TradeOutcome]:
    """A live signal as a TradeOutcome; None for a non-expiry cancel."""
    if status == 'cancelled':
        if '[expired' not in (notes or ''):
            return None
        outcome = 'expired'
    else:
        outcome = _LIVE_OUTCOME.get(status)
        if outcome is None:
            return None
    r = pnl_pips / risk_pips if outcome in ('tp', 'sl') and pnl_pips is not None and risk_pips else None
    return TradeOutcome(symbol=symbol, time=pd.Timestamp(time), direction=direction.upper(),
                        outcome=outcome, r=r)


def replay_outcomes(symbol: str, df: pd.DataFrame, strategy_func: StrategyFunc,
                    start: pd.Timestamp, warmup: int,
                    expiry_hours: Optional[float]) -> List[TradeOutcome]:
    """Backtest df from `start` (with `warmup` candles of history) under live's gates and expiry."""
    first = df.index[df.index >= start][0]
    result = run_on_window(df, first, strategy_func, warmup=warmup, expiry_hours=expiry_hours)

    outcomes = []
    for trade in result.trades:
        outcome = _REPLAY_OUTCOME[trade.status]
        r = None
        if outcome in ('tp', 'sl'):
            sign = 1 if trade.direction == TradeDirection.LONG else -1
            r = round((trade.exit_price - trade.entry_price) * sign / abs(trade.entry_price - trade.stop_loss), 2)
        outcomes.append(TradeOutcome(symbol=symbol, time=pd.Timestamp(trade.entry_time),
                                     direction=trade.direction.name, outcome=outcome, r=r))
    return outcomes


def compare(live: List[TradeOutcome], replay: List[TradeOutcome]) -> Dict[str, SymbolParity]:
    """Pair trades by (symbol, entry candle) and list every disagreement."""
    report: Dict[str, SymbolParity] = {}
    for o in live:
        report.setdefault(o.symbol, SymbolParity()).live.append(o)
    for o in replay:
        report.setdefault(o.symbol, SymbolParity()).replay.append(o)

    for parity in report.values():
        live_by_time = {o.time: o for o in parity.live}
        replay_by_time = {o.time: o for o in parity.replay}
        for when in sorted(set(live_by_time) | set(replay_by_time)):
            lv, rp = live_by_time.get(when), replay_by_time.get(when)
            if lv and rp:
                if lv.outcome != rp.outcome:
                    parity.mismatches.append(Mismatch('outcome', lv, rp))
            elif lv:
                parity.mismatches.append(Mismatch('live_only', lv, None))
            else:
                parity.mismatches.append(Mismatch('replay_only', None, rp))
    return report


def _r(value: float) -> str:
    return f"{value:+.1f}R"


def _label(outcome: str) -> str:
    return outcome.upper() if outcome in ('tp', 'sl') else outcome


def _mismatch_line(m: Mismatch) -> str:
    o = m.live or m.replay
    head = f"  • {o.time.strftime('%m-%d %H:%M')} {o.direction}: "
    if m.kind == 'outcome':
        return head + f"live {_label(m.live.outcome)}, backtest {_label(m.replay.outcome)}"
    if m.kind == 'live_only':
        return head + f"live only ({_label(m.live.outcome)})"
    return head + f"backtest only ({_label(m.replay.outcome)})"


def build_parity_text(report: Dict[str, SymbolParity], days: int) -> str:
    lines = [f"🔁 Backtest parity (last {days} days)"]
    if not report:
        lines.append("No trades live or in the backtest.")
    for symbol in sorted(report):
        p = report[symbol]
        flag = '✅' if not p.mismatches else '⚠️'
        lines.append(f"{flag} {symbol}: live {_r(p.live_r)} ({len(p.live)}) | "
                     f"backtest {_r(p.replay_r)} ({len(p.replay)})")
        lines.extend(_mismatch_line(m) for m in p.mismatches)
    return "\n".join(lines)

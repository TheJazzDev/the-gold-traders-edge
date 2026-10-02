"""
Market-hours arithmetic for signal expiry.

Gold and FX close for the weekend from Friday ~21:00 UTC to Sunday ~21:00
UTC (22:00 in northern-hemisphere winter, and COMEX gold reopens an hour
after FX). Counting a signal's age in wall-clock hours lets that closed
time expire it: ARLB-0925-01 was cancelled Sunday night after only ~16
market hours, then hit TP on Monday. Expiry counts open-market hours
instead, in both live (signals/outcome_tracker.py) and the backtest
(backtesting/engine.py), so the two agree.

The window is fixed at the summer-time edges: in winter it counts one hour
of Friday 21:00-22:00 and Sunday 21:00-22:00 that the market is actually
closed for. That error is two hours a week, far below the expiry windows
(48h+) it feeds.
"""
from datetime import datetime, timedelta

WEEKEND_CLOSE_WEEKDAY = 4  # Friday
WEEKEND_CLOSE_HOUR = 21
WEEKEND_LENGTH = timedelta(hours=48)  # Fri 21:00 -> Sun 21:00 UTC


def _weekend_close_on_or_before(moment: datetime) -> datetime:
    days_back = (moment.weekday() - WEEKEND_CLOSE_WEEKDAY) % 7
    close = (moment - timedelta(days=days_back)).replace(
        hour=WEEKEND_CLOSE_HOUR, minute=0, second=0, microsecond=0)
    if close > moment:
        close -= timedelta(days=7)
    return close


def market_hours_between(start: datetime, end: datetime) -> float:
    """Hours between `start` and `end` (naive UTC) with the market open."""
    if end <= start:
        return 0.0

    closed = timedelta(0)
    weekend_start = _weekend_close_on_or_before(start)
    while weekend_start < end:
        weekend_end = weekend_start + WEEKEND_LENGTH
        overlap = min(end, weekend_end) - max(start, weekend_start)
        if overlap > timedelta(0):
            closed += overlap
        weekend_start += timedelta(days=7)

    return (end - start - closed).total_seconds() / 3600

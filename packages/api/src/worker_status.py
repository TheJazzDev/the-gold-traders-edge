"""
Derives live worker status from the engine's persisted heartbeat, shared by
the /v1/signals/service/status and /v1/settings/service/status routes.

The worker (MultiTimeframeService._save_heartbeat, in
packages/engine/run_multi_timeframe_service.py) writes a JSON heartbeat to
the `worker_heartbeat` setting roughly every 15s. Reading it directly here
(instead of each route re-deriving liveness from signal staleness) is what
lets a worker be reported "running" even when it hasn't generated a new
signal in a while.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

# The worker writes a heartbeat roughly every 15s — anything older than this
# means the worker process itself has stopped updating it (crashed, hung, or
# never started this deploy), regardless of what it last reported.
DEFAULT_STALE_AFTER_SECONDS = 120


@dataclass
class WorkerStatus:
    is_running: bool
    candles_processed: int
    signals_generated: int
    uptime_hours: Optional[float]


def derive_worker_status(
    heartbeat: Dict[str, Any],
    worker_id: str,
    now: datetime,
    stale_after_seconds: int = DEFAULT_STALE_AFTER_SECONDS,
) -> WorkerStatus:
    """Compute real worker status from a heartbeat payload (see module
    docstring). worker_id is "SYMBOL:timeframe" (e.g. "XAUUSD:1h") — an
    exact key lookup, no fallback to a different worker's data, since
    worker IDs are unambiguous once every worker has its own symbol."""
    heartbeat = heartbeat or {}
    workers = heartbeat.get('workers') or {}
    worker_data = workers.get(worker_id)

    if worker_data is None:
        return WorkerStatus(is_running=False, candles_processed=0, signals_generated=0, uptime_hours=None)

    updated_at_raw = heartbeat.get('updated_at')
    heartbeat_age_seconds = (
        (now - datetime.fromisoformat(updated_at_raw)).total_seconds() if updated_at_raw else None
    )
    is_fresh = heartbeat_age_seconds is not None and heartbeat_age_seconds < stale_after_seconds
    is_running = bool(worker_data.get('is_running')) and is_fresh

    # Only report uptime while the worker is actually confirmed running —
    # otherwise a crashed worker would show an ever-growing uptime next to
    # status=stopped, computed from a start_time that's no longer meaningful.
    uptime_hours = None
    start_time_raw = heartbeat.get('start_time')
    if is_running and start_time_raw:
        uptime_hours = (now - datetime.fromisoformat(start_time_raw)).total_seconds() / 3600

    return WorkerStatus(
        is_running=is_running,
        candles_processed=worker_data.get('candles_processed', 0),
        signals_generated=worker_data.get('signals_generated', 0),
        uptime_hours=uptime_hours,
    )

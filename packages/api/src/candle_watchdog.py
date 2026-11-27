"""
Telegram alert when a market stops getting new candles.

Each signal worker writes the newest candle its data feed returned into the
`worker_latest_candles` setting, next to `worker_heartbeat` (see
_save_heartbeat in packages/engine/run_multi_timeframe_service.py). On 2026-11-26 Yahoo stopped
publishing intraday bars for every CME future for over a day; the gold worker
waited silently and no signals were possible. This watches that time and sends
one message when a worker has had no new candle for too many open-market
hours, and one when candles return. Weekends are not counted; holidays are, on
purpose, so a holiday gap also alerts.

CANDLE_SILENCE_ALERT_HOURS   open-market hours without a new candle (default 6;
                             normal gaps reach ~4h around the daily and Sunday reopen)
CANDLE_WATCHDOG_ENABLED      "false" turns this off (default on)
EA_ALERT_CHAT_ID             where to send it (default TELEGRAM_CHAT_ID)
"""
import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

engine_src = Path(__file__).parent.parent.parent / "engine" / "src"
if str(engine_src) not in sys.path:
    sys.path.insert(0, str(engine_src))

from utils.market_hours import market_hours_between  # noqa: E402

from src.ea_watchdog import send_telegram  # noqa: E402

CHECK_EVERY_SECONDS = 300
DEFAULT_LIMIT_HOURS = 6.0


def silence_limit_hours() -> float:
    try:
        hours = float(os.getenv("CANDLE_SILENCE_ALERT_HOURS", str(DEFAULT_LIMIT_HOURS)))
    except ValueError:
        hours = DEFAULT_LIMIT_HOURS
    return max(hours, 1.0)


def enabled() -> bool:
    return os.getenv("CANDLE_WATCHDOG_ENABLED", "true").strip().lower() not in ("false", "0", "no", "off")


def _parse(raw: Optional[str]) -> Optional[datetime]:
    return datetime.fromisoformat(raw) if raw else None


def _label(worker_id: str) -> str:
    return worker_id.replace(":", " ")


class CandleWatchdog:
    """Decides what to say, given the heartbeat's workers and each one's newest candle."""

    def __init__(self):
        self.alerted: set = set()

    def check(self, now: datetime, heartbeat: Dict[str, Any],
              latest_candles: Dict[str, Optional[str]]) -> List[str]:
        messages = []
        heartbeat = heartbeat or {}
        latest_candles = latest_candles or {}
        start_time = _parse(heartbeat.get('start_time'))
        limit = silence_limit_hours()

        for worker_id in (heartbeat.get('workers') or {}):
            latest = _parse(latest_candles.get(worker_id))
            # Before a restarted worker's first candle, count from its start.
            since = latest or start_time
            if since is None:
                continue
            quiet_hours = market_hours_between(since, now)
            silent = quiet_hours > limit

            if silent and worker_id not in self.alerted:
                self.alerted.add(worker_id)
                last = latest.strftime('%Y-%m-%d %H:%M UTC') if latest else "none since restart"
                messages.append(
                    f"⚠️ No new {_label(worker_id)} candle for {int(quiet_hours)} market hours "
                    f"(last candle: {last}). No signals for it until candles return. "
                    "Usually the data feed (Yahoo) has a gap or the market is on holiday."
                )
            elif not silent and worker_id in self.alerted:
                self.alerted.discard(worker_id)
                messages.append(f"✅ {_label(worker_id)} candles are back; signals can fire again.")
        return messages


def _read_settings():
    """The worker heartbeat and each worker's newest candle."""
    from src.database.connection import SessionLocal
    from database.settings_repository import SettingsRepository

    session = SessionLocal()
    try:
        repo = SettingsRepository(session)
        return (repo.get('worker_heartbeat', default={}) or {},
                repo.get('worker_latest_candles', default={}) or {})
    finally:
        session.close()


def _loop() -> None:
    watchdog = CandleWatchdog()
    while True:
        time.sleep(CHECK_EVERY_SECONDS)
        try:
            heartbeat, latest_candles = _read_settings()
            for message in watchdog.check(datetime.utcnow(), heartbeat, latest_candles):
                send_telegram(message)
        except Exception as error:  # an alert must never take the API down
            print(f"Candle watchdog: check failed: {type(error).__name__}: {error}")


def start() -> None:
    """Start the background check unless turned off."""
    if not enabled():
        return
    threading.Thread(target=_loop, daemon=True, name="candle-watchdog").start()

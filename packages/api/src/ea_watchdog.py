"""
Telegram alert when the order terminal goes quiet.

The MT5 terminal on Railway asks the API for orders every few seconds. If it
stops while trading is live, signals are being missed and nobody would know.
This sends one message when it has been silent too long and one when it is back.

EA_WATCH_TERMINAL          the terminal to watch (default "railway"; empty turns this off)
EA_SILENCE_ALERT_MINUTES   how long it may be silent (default 5)
EA_ALERT_CHAT_ID           where to send it (default TELEGRAM_CHAT_ID)
"""
import json
import os
import threading
import time
import urllib.request
from datetime import datetime, timedelta
from typing import Optional

CHECK_EVERY_SECONDS = 60


def watched_terminal() -> str:
    return os.getenv("EA_WATCH_TERMINAL", "railway").strip()


def silence_limit() -> timedelta:
    try:
        minutes = float(os.getenv("EA_SILENCE_ALERT_MINUTES", "5"))
    except ValueError:
        minutes = 5.0
    return timedelta(minutes=max(minutes, 1.0))


class Watchdog:
    """Decides what to say, given when the terminal was last heard from."""

    def __init__(self, started_at: datetime):
        self.started_at = started_at
        self.alerted = False

    def check(self, now: datetime, last_seen: Optional[datetime], live: bool) -> Optional[str]:
        # Before the first poll, count the silence from when the API started.
        heard = last_seen or self.started_at
        silent = now - heard > silence_limit()
        name = watched_terminal()

        if silent and live and not self.alerted:
            self.alerted = True
            minutes = int((now - heard).total_seconds() // 60)
            return (f"⚠️ Order terminal '{name}' has not contacted the server for {minutes} minutes. "
                    "New signals are NOT being placed as orders until it is back.")
        if not silent and self.alerted:
            self.alerted = False
            return f"✅ Order terminal '{name}' is back and asking for orders again."
        return None


def send_telegram(text: str) -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("EA_ALERT_CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return False
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps({"chat_id": chat_id, "text": text}).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status == 200
    except Exception as error:  # an alert must never take the API down
        print(f"EA watchdog: could not send the Telegram alert: {type(error).__name__}")
        return False


def _loop(last_seen_of, is_live) -> None:
    watchdog = Watchdog(datetime.utcnow())
    while True:
        time.sleep(CHECK_EVERY_SECONDS)
        try:
            message = watchdog.check(datetime.utcnow(), last_seen_of(watched_terminal()), is_live())
            if message:
                send_telegram(message)
        except Exception as error:
            print(f"EA watchdog: check failed: {type(error).__name__}: {error}")


def start(last_seen_of, is_live) -> None:
    """Start the background check. Does nothing when no terminal is watched."""
    if not watched_terminal():
        return
    threading.Thread(target=_loop, args=(last_seen_of, is_live), daemon=True, name="ea-watchdog").start()

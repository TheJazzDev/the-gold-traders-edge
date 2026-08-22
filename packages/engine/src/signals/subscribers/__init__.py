"""
Signal Subscribers Package

Subscribers receive validated signals from the RealtimeSignalGenerator
and perform specific actions (save to DB, log, send notifications, etc.).

Available Subscribers:
- DatabaseSubscriber: Saves signals to SQLite database
- LoggerSubscriber: Logs signals to dedicated file
- ConsoleSubscriber: Pretty-prints signals to console
- TelegramSubscriber: Sends signals to a Telegram bot/channel
"""

from .database_subscriber import DatabaseSubscriber
from .logger_subscriber import LoggerSubscriber
from .console_subscriber import ConsoleSubscriber
from .telegram_subscriber import TelegramSubscriber

__all__ = [
    'DatabaseSubscriber',
    'LoggerSubscriber',
    'ConsoleSubscriber',
    'TelegramSubscriber',
]

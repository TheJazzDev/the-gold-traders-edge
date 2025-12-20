"""
Signal Subscribers Package

Subscribers receive validated signals from the RealtimeSignalGenerator
and perform specific actions (save to DB, log, send notifications, etc.).

Available Subscribers:
- DatabaseSubscriber: Saves signals to SQLite database
- LoggerSubscriber: Logs signals to dedicated file
- ConsoleSubscriber: Pretty-prints signals to console
"""

from .database_subscriber import DatabaseSubscriber
from .logger_subscriber import LoggerSubscriber
from .console_subscriber import ConsoleSubscriber

__all__ = [
    'DatabaseSubscriber',
    'LoggerSubscriber',
    'ConsoleSubscriber',
]

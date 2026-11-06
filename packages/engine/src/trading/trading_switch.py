"""
The switch between signals only, dry run and real orders.

ENABLE_AUTO_TRADING only lets the service connect to the broker. Whether an
order goes out is decided per signal from the `auto_trading_enabled` and
`dry_run_mode` settings, so the dashboard can stop trading without a restart.
Anything unreadable counts as OFF: the safe failure is a missed trade.
"""
import logging
from enum import Enum
from typing import Callable

from database.connection import DatabaseManager
from database.settings_repository import SettingsRepository

logger = logging.getLogger(__name__)


class TradingMode(Enum):
    OFF = 'off'
    DRY_RUN = 'dry_run'
    LIVE = 'live'


def resolve_trading_mode(auto_trading_enabled: bool, dry_run_mode: bool) -> TradingMode:
    if not auto_trading_enabled:
        return TradingMode.OFF
    return TradingMode.DRY_RUN if dry_run_mode else TradingMode.LIVE


def make_trading_mode_reader(database_url: str) -> Callable[[], TradingMode]:
    db_manager = DatabaseManager(database_url)

    def read_mode() -> TradingMode:
        try:
            with db_manager.session_scope() as session:
                repo = SettingsRepository(session)
                return resolve_trading_mode(
                    auto_trading_enabled=repo.get('auto_trading_enabled', default=False) is True,
                    dry_run_mode=repo.get('dry_run_mode', default=True) is not False,
                )
        except Exception as e:
            logger.error(f"Could not read trading settings, treating as OFF: {e}")
            return TradingMode.OFF

    return read_mode

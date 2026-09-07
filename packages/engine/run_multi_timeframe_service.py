#!/usr/bin/env python3
"""
Multi-Timeframe Signal Service

Runs signal generators for multiple timeframes simultaneously:
- 5m, 15m, 30m, 1H, 4H, 1D

Each timeframe runs independently in its own thread, generating signals
based on ONLY the 2 proven profitable strategies:
1. Momentum Equilibrium (74% win rate, 3.31 PF)
2. London Session Breakout (58.8% win rate, 2.74 PF)

All signals are saved to the same database with timeframe tagged.
"""

import sys
import os
import json
from pathlib import Path
import logging
import threading
import time
from datetime import datetime
from typing import List, Dict, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from data.realtime_feed import create_datafeed
from signals.gold_strategy import GoldStrategy
from signals.realtime_generator import RealtimeSignalGenerator, SignalValidator
from signals.subscribers import DatabaseSubscriber, LoggerSubscriber, ConsoleSubscriber
from signals.subscribers.mt5_subscriber import MT5Subscriber
from signals.subscribers.telegram_subscriber import TelegramSubscriber
from signals.subscribers.dedup_subscriber import DeduplicationSubscriber
from signals.signal_deduplicator import get_deduplicator
from signals.outcome_tracker import SignalOutcomeTracker
from trading.mt5_config import MT5Config
from trading.mt5_connection import create_mt5_connection
from trading.risk_manager import RiskManager
from database.connection import DatabaseManager
from database.models import Base
from database.signal_repository import SignalRepository
from database.settings_repository import SettingsRepository
from report import build_report_text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(threadName)-10s] - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('multi_timeframe_service.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# Only 1H has been re-tuned and validated against real market data
# (see docs/superpowers/specs/2026-08-22-signal-validation-and-outcome-tracking-design.md).
# The other timeframes are left available in the code but not run live
# until each is independently validated the same way.
TIMEFRAMES = ['1h']

# ALL 5 PROFITABLE RULES - Unprofitable ones deleted from codebase!
PROFITABLE_RULES = [
    'momentum_equilibrium',      # 76% WR, 293% return - ⭐ BEST
    'london_session_breakout',   # 58.8% WR, 2.74 PF - ⭐ STRONG
    'golden_fibonacci',          # 52.6% WR, 44% return
    'ath_retest',                # 38% WR, 30% return
    'order_block_retest',        # Institutional smart money zones
]


class TimeframeWorker:
    """
    Worker thread that runs signal generation for a single timeframe.
    """

    def __init__(
        self,
        timeframe: str,
        database_url: str,
        shared_dedup_subscriber,  # SHARED across all workers
        telegram_subscriber=None,
        enable_trading: bool = False,
        mt5_config: MT5Config = None
    ):
        """
        Initialize timeframe worker.

        Args:
            timeframe: Timeframe to monitor (e.g., '5m', '1h', '4h')
            database_url: Database connection URL
            shared_dedup_subscriber: Shared deduplication subscriber (same instance for all workers)
            telegram_subscriber: Shared Telegram subscriber, used here to notify on
                signal close (TP/SL/expiry) — separate from its role inside
                shared_dedup_subscriber, which notifies on signal creation
            enable_trading: Whether to enable auto-trading via MT5Subscriber
            mt5_config: MT5 configuration (required if enable_trading=True)
        """
        self.timeframe = timeframe
        self.database_url = database_url
        self.shared_dedup_subscriber = shared_dedup_subscriber
        self.telegram_subscriber = telegram_subscriber
        self.enable_trading = enable_trading
        self.mt5_config = mt5_config
        self.is_running = False
        self.thread: threading.Thread = None
        self.generator: RealtimeSignalGenerator = None
        self.mt5_connection = None
        self.risk_manager = None
        self.last_start_time: float = None
        self.restart_backoff_seconds = 10
        self.next_restart_allowed_at: float = None

    def start(self):
        """Start the worker thread."""
        self.thread = threading.Thread(
            target=self._run,
            name=f"TF-{self.timeframe}",
            daemon=True
        )
        self.is_running = True
        self.last_start_time = time.monotonic()
        self.thread.start()
        logger.info(f"✅ Started worker for {self.timeframe}")

    def stop(self):
        """Stop the worker thread."""
        self.is_running = False
        if self.generator:
            self.generator.stop()
        logger.info(f"⏹️  Stopped worker for {self.timeframe}")

    def restart_if_needed(self, min_uptime_seconds: float = 60, max_backoff_seconds: float = 300) -> bool:
        """
        Restart this worker if its thread has died. Previously the monitor
        loop only logged "restarting..." without ever actually restarting
        it — a dead worker (e.g. a data feed hiccup) stayed dead until a
        full manual redeploy, while /health kept reporting healthy since it
        only checks the separate API process.

        Uses exponential backoff so a persistently broken feed doesn't
        hammer the upstream API (or spam logs) every monitor tick: a worker
        that ran for at least `min_uptime_seconds` before dying is treated
        as a fresh failure (backoff resets to 10s); one that keeps dying
        immediately backs off further, capped at `max_backoff_seconds`.
        """
        if self.is_running:
            return False

        now = time.monotonic()
        if self.next_restart_allowed_at is not None and now < self.next_restart_allowed_at:
            return False

        if self.last_start_time is not None and (now - self.last_start_time) >= min_uptime_seconds:
            self.restart_backoff_seconds = 10
        else:
            self.restart_backoff_seconds = min(self.restart_backoff_seconds * 2, max_backoff_seconds)

        self.next_restart_allowed_at = now + self.restart_backoff_seconds
        logger.warning(
            f"⚠️  Worker {self.timeframe} has stopped, restarting "
            f"(backoff if it fails again: {self.restart_backoff_seconds}s)..."
        )
        self.start()
        return True

    def _run(self):
        """Main worker loop."""
        try:
            logger.info(f"🚀 Initializing {self.timeframe} generator...")

            # Load the tuned config for this timeframe if one exists;
            # otherwise fall back to defaults (no other timeframe has a
            # tuned config yet — see TIMEFRAMES above). Done before creating
            # the data feed/generator because both need lookback_periods
            # derived from the config actually in use (see below).
            tuned_config_path = Path(__file__).parent / 'tuned_configs' / f'{self.timeframe}.json'
            if tuned_config_path.exists():
                with open(tuned_config_path) as f:
                    tuned = json.load(f)
                strategy = GoldStrategy(config=tuned['config'])
                for name in strategy.rules_enabled:
                    strategy.rules_enabled[name] = name in tuned['enabled_rules']
                expiry_hours = tuned['expiry_hours']
                logger.info(f"   [{self.timeframe}] Loaded tuned config from {tuned_config_path}")
            else:
                strategy = GoldStrategy()
                expiry_hours = 48.0
                logger.warning(f"   [{self.timeframe}] No tuned config found at {tuned_config_path}, using untuned defaults")

            enabled_names = [name for name, on in strategy.rules_enabled.items() if on]
            logger.info(f"   [{self.timeframe}] Enabled rules: {enabled_names}")

            # The `enabled_strategies` / `min_confidence` / `min_rr_ratio`
            # settings are editable via the admin UI and API, but until now
            # nothing in the engine ever read them back — toggling a
            # strategy off there had no effect on what actually ran. This
            # closure re-reads them once per candle close (see the
            # pre_run_hook wiring below) and mutates the already-running
            # strategy/validator in place; GoldStrategy.evaluate() and
            # SignalValidator.validate() both re-read their state on every
            # call, so no restart is needed for a change to take effect.
            def refresh_settings():
                db_manager = DatabaseManager(self.database_url)
                with db_manager.session_scope() as session:
                    Base.metadata.create_all(bind=session.get_bind())
                    repo = SettingsRepository(session)
                    repo.initialize_defaults()
                    enabled_list = repo.get('enabled_strategies', default=None)
                    min_confidence = repo.get('min_confidence', default=None)
                    min_rr_ratio = repo.get('min_rr_ratio', default=None)

                if enabled_list is not None:
                    for name in strategy.rules_enabled:
                        strategy.set_rule_enabled(name, name in enabled_list)
                if min_confidence is not None:
                    validator.min_confidence = min_confidence
                if min_rr_ratio is not None:
                    validator.min_rr_ratio = min_rr_ratio

                effective = [name for name, on in strategy.rules_enabled.items() if on]
                logger.info(
                    f"   [{self.timeframe}] Settings refreshed — enabled rules: {effective}, "
                    f"min_confidence={validator.min_confidence}, min_rr_ratio={validator.min_rr_ratio}"
                )

            # GoldStrategy.evaluate() refuses to evaluate any rule until
            # current_idx >= max(config['trend_lookback'], 60) (silently
            # returns None, no log, no exception). The data feed/generator
            # both default lookback_periods to 200 candles, which is a
            # no-op with the untuned default config (trend_lookback=50) but
            # is exactly equal to the 1h tuned config's trend_lookback=200 —
            # current_idx then maxes out at 199, permanently below the gate,
            # so no signal could ever fire. Size the fetch comfortably above
            # whatever the active config actually requires.
            lookback_periods = max(200, strategy.config['trend_lookback'] + 50)

            # Create data feed (use setting or environment variable)
            datafeed_type = os.getenv('DATA_FEED_TYPE', 'yahoo')  # Default to yahoo for backward compatibility
            logger.info(f"   [{self.timeframe}] Using data feed: {datafeed_type} (lookback_periods={lookback_periods})")

            data_feed = create_datafeed(
                feed_type=datafeed_type,
                symbol='XAUUSD',
                timeframe=self.timeframe,
                lookback_periods=lookback_periods
            )

            outcome_tracker = SignalOutcomeTracker(
                database_url=self.database_url,
                symbol='XAUUSD',
                timeframe=self.timeframe,
                expiry_hours=expiry_hours,
                telegram_subscriber=self.telegram_subscriber,
            )

            # Create validator. min_rr_ratio/min_confidence are seeded with
            # the settings' own defaults and immediately overwritten by
            # refresh_settings() on the first pre_run_hook call below.
            validator = SignalValidator(min_rr_ratio=1.5, min_confidence=0.0)

            # Create generator
            self.generator = RealtimeSignalGenerator(
                data_feed=data_feed,
                strategy=strategy,
                validator=validator,
                outcome_tracker=outcome_tracker,
                lookback_periods=lookback_periods,
                pre_run_hook=refresh_settings
            )

            # Add SHARED deduplication subscriber (same instance across ALL workers)
            self.generator.add_subscriber(self.shared_dedup_subscriber)

            # Add non-deduplicated subscribers (these show ALL signals for debugging)
            logger_subscriber = LoggerSubscriber()
            self.generator.add_subscriber(logger_subscriber)

            console_subscriber = ConsoleSubscriber()
            self.generator.add_subscriber(console_subscriber)

            # MT5 subscriber - auto-trade signals (if enabled)
            if self.enable_trading and self.mt5_config:
                logger.info(f"   [{self.timeframe}] Enabling auto-trading via MT5Subscriber...")

                # Create MT5 connection (shared across all timeframes via singleton)
                self.mt5_connection = create_mt5_connection(self.mt5_config)
                if not self.mt5_connection.connect():
                    raise RuntimeError(f"[{self.timeframe}] Failed to connect to MT5")

                # Get account info
                account_info = self.mt5_connection.get_account_info()
                logger.info(
                    f"   [{self.timeframe}] Connected to MT5:\n"
                    f"      Account: {account_info.get('login', 'N/A')}\n"
                    f"      Balance: ${account_info.get('balance', 0):.2f}"
                )

                # Create risk manager
                self.risk_manager = RiskManager(self.mt5_config)
                self.risk_manager.set_initial_balance(account_info.get('balance', 0))

                # Create database manager for MT5 subscriber
                db_manager = DatabaseManager(self.database_url)

                # Add MT5 subscriber
                mt5_subscriber = MT5Subscriber(
                    connection=self.mt5_connection,
                    config=self.mt5_config,
                    db_manager=db_manager,
                    risk_manager=self.risk_manager,
                    dry_run=False  # Set to True for testing without executing trades
                )
                self.generator.add_subscriber(mt5_subscriber)
                logger.info(f"   [{self.timeframe}] ✅ Auto-trading ENABLED")
            else:
                logger.info(f"   [{self.timeframe}] Auto-trading DISABLED (signals only)")

            logger.info(f"   [{self.timeframe}] Generator ready, starting loop...")

            # Run generator
            self.generator.start()

        except Exception as e:
            logger.error(f"❌ [{self.timeframe}] Worker failed: {e}", exc_info=True)
            self.is_running = False


class MultiTimeframeService:
    """
    Main service that manages multiple timeframe workers.
    """

    def __init__(self, timeframes: List[str] = None, database_url: str = None, enable_trading: bool = False):
        """
        Initialize multi-timeframe service.

        Args:
            timeframes: List of timeframes to monitor (default: all)
            database_url: Database URL (default: from env or PostgreSQL)
            enable_trading: Whether to enable auto-trading (default: False, signals only)
        """
        self.timeframes = timeframes or TIMEFRAMES
        self.database_url = database_url or os.getenv(
            'DATABASE_URL',
            'postgresql://postgres:postgres@localhost:5432/gold_signals'
        )
        self.enable_trading = enable_trading
        self.mt5_config = None

        # Load MT5 config if trading is enabled
        if self.enable_trading:
            try:
                self.mt5_config = MT5Config.from_env()
                self.mt5_config.validate()
                logger.info("✅ MT5 configuration loaded successfully")
            except Exception as e:
                logger.error(f"❌ Failed to load MT5 config: {e}")
                logger.error("Auto-trading will be DISABLED. Set METAAPI_TOKEN and METAAPI_ACCOUNT_ID in env.")
                self.enable_trading = False

        self.workers: Dict[str, TimeframeWorker] = {}
        self.is_running = False
        self.start_time: datetime = None

        # Cached across calls to _load_last_report_time/_save_last_report_time/
        # _save_heartbeat so the heartbeat's 15s cadence doesn't churn a fresh
        # DatabaseManager (and engine/connection pool) or re-run the full
        # settings-defaults sync on every single write — see _open_settings_repo.
        self._db_manager: Optional[DatabaseManager] = None
        self._settings_ready = False

        # Create SHARED deduplication subscriber (ONE instance for ALL timeframes)
        # DATABASE-BACKED: Loads recent signals from DB on startup to prevent duplicates after restart
        db_subscriber = DatabaseSubscriber(database_url=self.database_url)
        telegram_subscriber = TelegramSubscriber(database_url=self.database_url)
        self.telegram_subscriber = telegram_subscriber  # kept for weekly reports

        self.shared_dedup_subscriber = DeduplicationSubscriber(
            subscribers=[db_subscriber, telegram_subscriber],
            dedup_window_hours=4,
            database_url=self.database_url  # Pass database URL for persistence
        )

        logger.info(
            "✅ Shared deduplication subscriber created "
            "(prevents duplicate signals across all timeframes and restarts)"
        )

    def start(self):
        """Start all timeframe workers."""
        print("\n" + "=" * 80)
        print("📊 MULTI-TIMEFRAME SIGNAL SERVICE")
        print("=" * 80)
        print(f"\n🎯 Monitoring Timeframes: {', '.join(self.timeframes)}")
        for timeframe in self.timeframes:
            tuned_config_path = Path(__file__).parent / 'tuned_configs' / f'{timeframe}.json'
            if tuned_config_path.exists():
                with open(tuned_config_path) as f:
                    enabled = json.load(f)['enabled_rules']
            else:
                enabled = PROFITABLE_RULES
            print(f"📈 [{timeframe}] Enabled Rules ({len(enabled)}):")
            for rule in enabled:
                print(f"   ✅ {rule}")
        print(f"\n💾 Database: {self.database_url}")
        print(f"🤖 Auto-Trading: {'✅ ENABLED' if self.enable_trading else '❌ DISABLED (signals only)'}")
        if self.enable_trading and self.mt5_config:
            print(f"📊 MT5 Connection: {self.mt5_config.connection_type.value}")
        print("\n" + "=" * 80 + "\n")

        self.is_running = True
        self.start_time = datetime.now()

        # Create and start workers for each timeframe
        for timeframe in self.timeframes:
            worker = TimeframeWorker(
                timeframe=timeframe,
                database_url=self.database_url,
                shared_dedup_subscriber=self.shared_dedup_subscriber,  # SHARE the same instance
                telegram_subscriber=self.telegram_subscriber,
                enable_trading=self.enable_trading,
                mt5_config=self.mt5_config
            )
            self.workers[timeframe] = worker
            worker.start()
            time.sleep(2)  # Stagger starts to avoid overwhelming the API

        logger.info(f"🎉 All {len(self.workers)} workers started successfully")

        # Monitor workers
        try:
            self._monitor_loop()
        except KeyboardInterrupt:
            logger.info("\n⏹️  Shutdown requested by user")
            self.stop()

    def stop(self):
        """Stop all workers."""
        logger.info("🛑 Stopping all workers...")
        self.is_running = False

        for timeframe, worker in self.workers.items():
            worker.stop()

        # Flush a final heartbeat with is_running=False for every worker —
        # otherwise the last periodic write (up to heartbeat_interval old)
        # would keep reporting "running" via the API until it aged past the
        # staleness threshold.
        self._save_heartbeat()

        logger.info("✅ All workers stopped")

    def _monitor_loop(self):
        """
        Monitor all workers and display status periodically.
        Also sends keep-alive pings to prevent Railway from sleeping,
        and a weekly performance report to Telegram.
        """
        last_status_time = datetime.now()
        last_keepalive_time = datetime.now()
        last_heartbeat_time = None
        last_report_time = self._load_last_report_time()
        status_interval = 300  # 5 minutes
        keepalive_interval = 240  # 4 minutes (ping API to keep it awake)
        heartbeat_interval = 15  # seconds; see _save_heartbeat
        report_interval = 7 * 24 * 3600  # weekly

        while self.is_running:
            time.sleep(10)  # Check every 10 seconds

            # Persist live worker status so the API can report real state
            # instead of guessing liveness from signal staleness.
            if last_heartbeat_time is None or (datetime.now() - last_heartbeat_time).total_seconds() >= heartbeat_interval:
                self._save_heartbeat()
                last_heartbeat_time = datetime.now()

            if last_report_time is None or (datetime.now() - last_report_time).total_seconds() >= report_interval:
                self._send_weekly_report()
                last_report_time = datetime.now()
                self._save_last_report_time(last_report_time)

            # Check if any workers have died, restarting them if so
            if self.is_running:
                for timeframe, worker in self.workers.items():
                    worker.restart_if_needed()

            # Send keep-alive ping to prevent Railway sleep
            if (datetime.now() - last_keepalive_time).total_seconds() >= keepalive_interval:
                self._send_keepalive()
                last_keepalive_time = datetime.now()

            # Display status periodically
            if (datetime.now() - last_status_time).total_seconds() >= status_interval:
                self._display_status()
                last_status_time = datetime.now()

    def _send_keepalive(self):
        """
        Send a keep-alive ping to the API health endpoint.
        This prevents Railway from putting the service to sleep.
        """
        try:
            import requests
            # Ping the health endpoint (running in the same container via supervisor)
            port = os.getenv('PORT', '8000')
            url = f"http://localhost:{port}/health"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                logger.debug("✓ Keep-alive ping successful")
            else:
                logger.warning(f"⚠️  Keep-alive ping returned {response.status_code}")
        except Exception as e:
            logger.debug(f"Keep-alive ping failed (expected during startup): {e}")

    def _display_status(self):
        """Display service status."""
        uptime = datetime.now() - self.start_time
        hours = uptime.total_seconds() / 3600

        print("\n" + "=" * 80)
        print(f"📊 SERVICE STATUS - Uptime: {hours:.1f} hours")
        print("=" * 80)

        # Show status of each worker
        for timeframe, worker in self.workers.items():
            status = "🟢 RUNNING" if worker.is_running else "🔴 STOPPED"
            signals = worker.generator.total_signals_generated if worker.generator else 0
            candles = worker.generator.total_candles_processed if worker.generator else 0

            print(f"{timeframe:>4} | {status} | Candles: {candles:>5} | Signals: {signals:>3}")

        print("=" * 80 + "\n")

    def _save_heartbeat(self):
        """
        Persist live worker status to the settings table so the API can
        report real state instead of guessing liveness from signal
        staleness (see MEMORY: /v1/signals/service/status and
        /v1/settings/service/status both used to report "stopped" for a
        perfectly healthy worker that simply hadn't generated a new signal
        recently). Called every ~15s from _monitor_loop — deliberately cheap
        (see _get_db_manager/_open_settings_repo) since this runs for the
        entire life of the process.
        """
        try:
            payload = {
                'updated_at': datetime.now().isoformat(),
                'start_time': self.start_time.isoformat() if self.start_time else None,
                'workers': {
                    timeframe: {
                        'is_running': worker.is_running,
                        'candles_processed': worker.generator.total_candles_processed if worker.generator else 0,
                        'signals_generated': worker.generator.total_signals_generated if worker.generator else 0,
                    }
                    for timeframe, worker in self.workers.items()
                },
            }
            with self._get_db_manager().session_scope() as session:
                repo = self._open_settings_repo(session)
                setting = repo.get_setting('worker_heartbeat')
                if setting:
                    setting.set_typed_value(payload)
        except Exception as e:
            logger.error(f"Failed to persist worker heartbeat: {e}", exc_info=True)

    def _get_db_manager(self) -> DatabaseManager:
        """A single DatabaseManager (engine/connection pool) reused for the life of the process."""
        if getattr(self, '_db_manager', None) is None:
            self._db_manager = DatabaseManager(self.database_url)
        return self._db_manager

    def _open_settings_repo(self, session) -> SettingsRepository:
        """
        Ensure the settings table and its default rows exist, then return a
        repo bound to `session`. The table-create + metadata-defaults sync
        (a query per DEFAULT_SETTINGS row) only needs to happen once per
        process — repeating it on every _save_heartbeat call (every ~15s)
        would mean sustained, unnecessary DB chatter for no benefit.
        """
        if not getattr(self, '_settings_ready', False):
            Base.metadata.create_all(bind=session.get_bind())
            SettingsRepository(session).initialize_defaults()
            self._settings_ready = True
        return SettingsRepository(session)

    def _load_last_report_time(self) -> Optional[datetime]:
        """
        Load when the weekly report was last sent, persisted in the settings
        table so the 7-day schedule survives service restarts/redeploys
        instead of resetting to "now" every time (it used to be in-memory
        only, so a service that never stays up for 7 straight days would
        never send a report).

        Returns None if it has never been sent (or on any DB error), which
        the caller treats as "send one now".
        """
        try:
            with self._get_db_manager().session_scope() as session:
                repo = self._open_settings_repo(session)
                raw = repo.get('weekly_report_last_sent_at', default='')
            return datetime.fromisoformat(raw) if raw else None
        except Exception as e:
            logger.error(f"Failed to load last weekly report time: {e}", exc_info=True)
            return None

    def _save_last_report_time(self, when: datetime):
        """Persist when the weekly report was last sent (see _load_last_report_time)."""
        try:
            with self._get_db_manager().session_scope() as session:
                repo = self._open_settings_repo(session)
                setting = repo.get_setting('weekly_report_last_sent_at')
                if setting:
                    setting.value = when.isoformat()
        except Exception as e:
            logger.error(f"Failed to persist last weekly report time: {e}", exc_info=True)

    def _send_weekly_report(self):
        """Send the last 7 days of signal performance stats to Telegram."""
        from database.connection import DatabaseManager
        try:
            db_manager = DatabaseManager(self.database_url)
            with db_manager.session_scope() as session:
                repo = SignalRepository(session)
                stats = repo.get_performance_stats(days=7)

            message = "📅 Weekly Performance Report\n\n" + build_report_text(stats, days=7)
            self.telegram_subscriber.send_custom_message(message)
            logger.info("✅ Weekly performance report sent to Telegram")
        except Exception as e:
            logger.error(f"Failed to send weekly report: {e}", exc_info=True)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Multi-Timeframe Gold Signal Service',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--timeframes', '-t',
        nargs='+',
        choices=['5m', '15m', '30m', '1h', '4h', '1d'],
        help='Timeframes to monitor (default: all)'
    )

    parser.add_argument(
        '--database',
        type=str,
        help='Database URL (default: from DATABASE_URL env)'
    )

    parser.add_argument(
        '--enable-trading',
        action='store_true',
        help='Enable auto-trading via MT5 (requires METAAPI_TOKEN and METAAPI_ACCOUNT_ID env vars)'
    )

    args = parser.parse_args()

    # Check if trading should be enabled (CLI flag or environment variable)
    enable_trading = args.enable_trading or os.getenv('ENABLE_AUTO_TRADING', '').lower() in ['true', '1', 'yes']

    if enable_trading:
        logger.info("🤖 Auto-trading ENABLED - signals will be executed on MT5 account")
    else:
        logger.info("📊 Signals-only mode - trades will NOT be executed (set --enable-trading or ENABLE_AUTO_TRADING=true to enable)")

    # Create and start service
    service = MultiTimeframeService(
        timeframes=args.timeframes,
        database_url=args.database,
        enable_trading=enable_trading
    )

    try:
        service.start()
    except Exception as e:
        logger.error(f"❌ Service failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

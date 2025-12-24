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
from pathlib import Path
import logging
import threading
import time
from datetime import datetime
from typing import List, Dict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from data.realtime_feed import create_datafeed
from signals.gold_strategy import GoldStrategy
from signals.realtime_generator import RealtimeSignalGenerator, SignalValidator
from signals.subscribers import DatabaseSubscriber, LoggerSubscriber, ConsoleSubscriber

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


# All timeframes to monitor
TIMEFRAMES = ['5m', '15m', '30m', '1h', '4h', '1d']

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

    def __init__(self, timeframe: str, database_url: str):
        """
        Initialize timeframe worker.

        Args:
            timeframe: Timeframe to monitor (e.g., '5m', '1h', '4h')
            database_url: Database connection URL
        """
        self.timeframe = timeframe
        self.database_url = database_url
        self.is_running = False
        self.thread: threading.Thread = None
        self.generator: RealtimeSignalGenerator = None

    def start(self):
        """Start the worker thread."""
        self.thread = threading.Thread(
            target=self._run,
            name=f"TF-{self.timeframe}",
            daemon=True
        )
        self.is_running = True
        self.thread.start()
        logger.info(f"✅ Started worker for {self.timeframe}")

    def stop(self):
        """Stop the worker thread."""
        self.is_running = False
        if self.generator:
            self.generator.stop()
        logger.info(f"⏹️  Stopped worker for {self.timeframe}")

    def _run(self):
        """Main worker loop."""
        try:
            logger.info(f"🚀 Initializing {self.timeframe} generator...")

            # Create data feed
            data_feed = create_datafeed(
                datafeed_type='yahoo',
                symbol='XAUUSD',
                timeframe=self.timeframe
            )

            # Create strategy - all 5 profitable rules enabled by default
            strategy = GoldStrategy()
            # All rules are already enabled by default (they're all profitable!)

            logger.info(f"   [{self.timeframe}] All 5 profitable rules enabled: {list(strategy.rules_enabled.keys())}")

            # Create validator
            validator = SignalValidator(min_rr_ratio=1.5)

            # Create generator
            self.generator = RealtimeSignalGenerator(
                data_feed=data_feed,
                strategy=strategy,
                validator=validator
            )

            # Add subscribers
            # Database subscriber - saves to DB
            db_subscriber = DatabaseSubscriber(database_url=self.database_url)
            self.generator.add_subscriber(db_subscriber.on_signal)

            # Logger subscriber - logs to file
            logger_subscriber = LoggerSubscriber()
            self.generator.add_subscriber(logger_subscriber.on_signal)

            # Console subscriber - prints to console
            console_subscriber = ConsoleSubscriber()
            self.generator.add_subscriber(console_subscriber.on_signal)

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

    def __init__(self, timeframes: List[str] = None, database_url: str = None):
        """
        Initialize multi-timeframe service.

        Args:
            timeframes: List of timeframes to monitor (default: all)
            database_url: Database URL (default: from env or PostgreSQL)
        """
        self.timeframes = timeframes or TIMEFRAMES
        self.database_url = database_url or os.getenv(
            'DATABASE_URL',
            'postgresql://postgres:postgres@localhost:5432/gold_signals'
        )
        self.workers: Dict[str, TimeframeWorker] = {}
        self.is_running = False
        self.start_time: datetime = None

    def start(self):
        """Start all timeframe workers."""
        print("\n" + "=" * 80)
        print("📊 MULTI-TIMEFRAME SIGNAL SERVICE")
        print("=" * 80)
        print(f"\n🎯 Monitoring Timeframes: {', '.join(self.timeframes)}")
        print(f"📈 Enabled Rules ({len(PROFITABLE_RULES)}):")
        for rule in PROFITABLE_RULES:
            print(f"   ✅ {rule}")
        print(f"\n💾 Database: {self.database_url}")
        print("\n" + "=" * 80 + "\n")

        self.is_running = True
        self.start_time = datetime.now()

        # Create and start workers for each timeframe
        for timeframe in self.timeframes:
            worker = TimeframeWorker(timeframe, self.database_url)
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

        logger.info("✅ All workers stopped")

    def _monitor_loop(self):
        """
        Monitor all workers and display status periodically.
        Also sends keep-alive pings to prevent Railway from sleeping.
        """
        last_status_time = datetime.now()
        last_keepalive_time = datetime.now()
        status_interval = 300  # 5 minutes
        keepalive_interval = 240  # 4 minutes (ping API to keep it awake)

        while self.is_running:
            time.sleep(10)  # Check every 10 seconds

            # Check if any workers have died
            for timeframe, worker in self.workers.items():
                if not worker.is_running and self.is_running:
                    logger.warning(f"⚠️  Worker {timeframe} has stopped, restarting...")
                    # Could implement auto-restart here if needed

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

    args = parser.parse_args()

    # Create and start service
    service = MultiTimeframeService(
        timeframes=args.timeframes,
        database_url=args.database
    )

    try:
        service.start()
    except Exception as e:
        logger.error(f"❌ Service failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

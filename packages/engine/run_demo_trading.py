#!/usr/bin/env python3
"""
Demo Trading Service Runner
Runs signal generation + automatic trade execution on MT5 demo account
"""

import argparse
import logging
import sys
import signal
import asyncio
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from database.connection import DatabaseManager
from signals.realtime_generator import RealtimeSignalGenerator
from signals.subscribers.database_subscriber import DatabaseSubscriber
from signals.subscribers.logger_subscriber import LoggerSubscriber
from signals.subscribers.console_subscriber import ConsoleSubscriber
from signals.subscribers.mt5_subscriber import MT5Subscriber
from signals.gold_strategy import GoldStrategy
from data.realtime_feed import create_datafeed
from trading.mt5_config import MT5Config
from trading.mt5_connection import create_mt5_connection
from trading.risk_manager import RiskManager
from trading.position_manager import PositionManager

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('demo_trading.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DemoTradingService:
    """Main service orchestrator for demo trading"""

    def __init__(self, mt5_config: MT5Config, dry_run: bool = False):
        self.mt5_config = mt5_config
        self.dry_run = dry_run
        self.running = False

        # Components
        self.mt5_connection = None
        self.db_manager = None
        self.risk_manager = None
        self.position_manager = None
        self.signal_generator = None
        self.datafeed = None

    def initialize(self):
        """Initialize all components"""
        logger.info("Initializing demo trading service...")

        # 1. MT5 Connection
        logger.info("Connecting to MT5...")
        self.mt5_connection = create_mt5_connection(self.mt5_config)

        if not self.mt5_connection.connect():
            raise RuntimeError("Failed to connect to MT5")

        account_info = self.mt5_connection.get_account_info()
        logger.info(
            f"Connected to MT5:\n"
            f"  Account: {account_info['login']}\n"
            f"  Balance: ${account_info['balance']:.2f}\n"
            f"  Leverage: 1:{account_info['leverage']}"
        )

        # 2. Database
        logger.info("Initializing database...")
        self.db_manager = DatabaseManager()

        # 3. Risk Manager
        logger.info("Initializing risk manager...")
        self.risk_manager = RiskManager(self.mt5_config)
        self.risk_manager.set_initial_balance(account_info['balance'])

        # 4. Position Manager
        logger.info("Initializing position manager...")
        self.position_manager = PositionManager(
            connection=self.mt5_connection,
            db_manager=self.db_manager,
            risk_manager=self.risk_manager,
            update_interval_seconds=60
        )

        # Sync positions on startup
        self.position_manager.sync_positions_on_startup()

        # 5. Data Feed
        logger.info("Initializing data feed...")
        self.datafeed = create_datafeed(
            feed_type=os.getenv("DATAFEED_TYPE", "yahoo"),
            symbol=self.mt5_config.symbol,
            timeframe="4H"
        )

        if not self.datafeed.connect():
            raise RuntimeError("Failed to connect to data feed")

        # 6. Strategy
        logger.info("Loading trading strategy...")
        # Use only Momentum Equilibrium strategy (best performer - Rule 5)
        strategy = GoldStrategy(enabled_rules=[5])

        # 7. Subscribers
        logger.info("Setting up signal subscribers...")
        subscribers = [
            DatabaseSubscriber(self.db_manager),
            LoggerSubscriber(log_file="signals.log"),
            ConsoleSubscriber(verbose=True),
            MT5Subscriber(
                connection=self.mt5_connection,
                config=self.mt5_config,
                db_manager=self.db_manager,
                risk_manager=self.risk_manager,
                dry_run=self.dry_run
            )
        ]

        # 8. Signal Generator
        logger.info("Initializing signal generator...")
        self.signal_generator = RealtimeSignalGenerator(
            datafeed=self.datafeed,
            strategy=strategy,
            subscribers=subscribers
        )

        logger.info("✅ All components initialized successfully!")

    async def start(self):
        """Start the demo trading service"""
        if self.running:
            logger.warning("Service already running")
            return

        self.running = True
        logger.info(
            f"\n{'='*70}\n"
            f"🚀 DEMO TRADING SERVICE STARTED\n"
            f"{'='*70}\n"
            f"Mode: {'DRY RUN (no real trades)' if self.dry_run else 'LIVE DEMO TRADING'}\n"
            f"Symbol: {self.mt5_config.symbol}\n"
            f"Max Risk/Trade: {self.mt5_config.max_risk_per_trade*100}%\n"
            f"Max Positions: {self.mt5_config.max_positions}\n"
            f"Max Daily Loss: {self.mt5_config.max_daily_loss*100}%\n"
            f"{'='*70}"
        )

        # Start position monitoring
        await self.position_manager.start_monitoring()

        # Start signal generation
        try:
            self.signal_generator.start()

            # Keep running
            while self.running:
                await asyncio.sleep(1)

        except KeyboardInterrupt:
            logger.info("Received shutdown signal...")
        finally:
            await self.shutdown()

    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down demo trading service...")
        self.running = False

        # Stop signal generation
        if self.signal_generator:
            self.signal_generator.stop()

        # Stop position monitoring
        if self.position_manager:
            await self.position_manager.stop_monitoring()

        # Disconnect from MT5
        if self.mt5_connection:
            self.mt5_connection.disconnect()

        # Disconnect data feed
        if self.datafeed:
            self.datafeed.disconnect()

        # Print final statistics
        if self.risk_manager:
            logger.info("\nFinal Statistics:")
            logger.info(f"  Risk Summary: {self.risk_manager.get_risk_summary(0)}")
            logger.info(f"  Weekly Stats: {self.risk_manager.get_weekly_stats()}")

        logger.info("✅ Demo trading service shut down successfully")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Demo Trading Service")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode (don't execute trades)")
    parser.add_argument("--config", action="store_true", help="Show configuration and exit")
    args = parser.parse_args()

    # Load MT5 configuration
    mt5_config = MT5Config.from_env()

    if args.config:
        print("\nMT5 Configuration:")
        print(mt5_config)
        return

    # Validate config
    try:
        mt5_config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        logger.error("\nPlease set the following environment variables:")
        logger.error("  MT5_CONNECTION_TYPE=direct|metaapi")
        logger.error("  For direct: MT5_LOGIN, MT5_PASSWORD, MT5_SERVER")
        logger.error("  For metaapi: METAAPI_TOKEN, METAAPI_ACCOUNT_ID")
        sys.exit(1)

    # Create and run service
    service = DemoTradingService(mt5_config=mt5_config, dry_run=args.dry_run)

    try:
        service.initialize()
        asyncio.run(service.start())
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

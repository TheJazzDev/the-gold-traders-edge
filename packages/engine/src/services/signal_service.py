"""
Signal Service - Main Production Service

This is the main orchestrator that runs 24/7 to generate real-time trading signals.

It combines:
- Data Feed (Yahoo Finance, MT5, or MetaAPI)
- Signal Generator (Momentum Equilibrium strategy)
- Signal Validator (quality control)
- Signal Publishers (Database, Logger, Console)

Features:
- Configuration management via environment variables
- Health monitoring with heartbeat logging
- Graceful startup and shutdown
- Error handling and recovery
- Status reporting
"""

import sys
import os
from pathlib import Path
import logging
import signal as sys_signal
import time
from typing import Optional, Dict
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.realtime_feed import create_datafeed, RealtimeDataFeed
from signals.gold_strategy import GoldStrategy
from signals.realtime_generator import RealtimeSignalGenerator, SignalValidator
from signals.subscribers import DatabaseSubscriber, LoggerSubscriber, ConsoleSubscriber


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('signal_service.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ServiceConfig:
    """
    Service configuration from environment variables.

    Environment Variables:
    - DATAFEED_TYPE: Data source (yahoo/mt5/metaapi) [default: yahoo]
    - SYMBOL: Trading symbol [default: XAUUSD]
    - TIMEFRAME: Candle timeframe [default: 4H]
    - DATABASE_URL: Database URL [default: sqlite:///signals.db]
    - ENABLE_DATABASE: Enable database subscriber [default: true]
    - ENABLE_LOGGER: Enable file logger [default: true]
    - ENABLE_CONSOLE: Enable console output [default: true]
    - MIN_RR_RATIO: Minimum R:R ratio [default: 1.5]
    - HEARTBEAT_INTERVAL: Minutes between heartbeat logs [default: 5]
    """

    def __init__(self):
        # Data feed configuration
        self.datafeed_type = os.getenv('DATAFEED_TYPE', 'yahoo')
        self.symbol = os.getenv('SYMBOL', 'XAUUSD')
        self.timeframe = os.getenv('TIMEFRAME', '4H')

        # Database configuration
        self.database_url = os.getenv('DATABASE_URL', 'sqlite:///signals.db')

        # Subscriber configuration
        self.enable_database = os.getenv('ENABLE_DATABASE', 'true').lower() == 'true'
        self.enable_logger = os.getenv('ENABLE_LOGGER', 'true').lower() == 'true'
        self.enable_console = os.getenv('ENABLE_CONSOLE', 'true').lower() == 'true'

        # Signal validation configuration
        self.min_rr_ratio = float(os.getenv('MIN_RR_RATIO', '1.5'))

        # Health monitoring
        self.heartbeat_interval = int(os.getenv('HEARTBEAT_INTERVAL', '5'))  # minutes

    def to_dict(self) -> Dict:
        """Convert configuration to dictionary."""
        return {
            'datafeed_type': self.datafeed_type,
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'database_url': self.database_url,
            'enable_database': self.enable_database,
            'enable_logger': self.enable_logger,
            'enable_console': self.enable_console,
            'min_rr_ratio': self.min_rr_ratio,
            'heartbeat_interval': self.heartbeat_interval,
        }

    def validate(self) -> bool:
        """Validate configuration."""
        if self.datafeed_type not in ['yahoo', 'mt5', 'metaapi']:
            logger.error(f"Invalid datafeed_type: {self.datafeed_type}")
            return False

        if self.timeframe not in ['1H', '4H', '1D']:
            logger.error(f"Invalid timeframe: {self.timeframe}")
            return False

        if self.min_rr_ratio < 1.0:
            logger.error(f"Invalid min_rr_ratio: {self.min_rr_ratio}")
            return False

        return True


class SignalService:
    """
    Main signal generation service.

    This service runs continuously to generate trading signals in real-time.
    """

    def __init__(self, config: Optional[ServiceConfig] = None):
        """
        Initialize signal service.

        Args:
            config: Service configuration (default: from environment variables)
        """
        self.config = config or ServiceConfig()
        self.is_running = False
        self.data_feed: Optional[RealtimeDataFeed] = None
        self.generator: Optional[RealtimeSignalGenerator] = None
        self.start_time: Optional[datetime] = None
        self.last_heartbeat: Optional[datetime] = None

        # Register signal handlers for graceful shutdown
        sys_signal.signal(sys_signal.SIGINT, self._signal_handler)
        sys_signal.signal(sys_signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.stop()

    def _create_data_feed(self) -> RealtimeDataFeed:
        """Create and configure data feed."""
        logger.info(f"Creating data feed: {self.config.datafeed_type}")

        feed = create_datafeed(
            feed_type=self.config.datafeed_type,
            symbol=self.config.symbol,
            timeframe=self.config.timeframe
        )

        return feed

    def _create_strategy(self) -> GoldStrategy:
        """Create and configure trading strategy."""
        logger.info("Creating strategy: Momentum Equilibrium only")

        strategy = GoldStrategy()

        # Disable all rules except Momentum Equilibrium
        for rule_name in strategy.rules_enabled.keys():
            strategy.rules_enabled[rule_name] = False

        strategy.rules_enabled['momentum_equilibrium'] = True

        return strategy

    def _setup_subscribers(self, generator: RealtimeSignalGenerator):
        """Setup signal subscribers."""
        logger.info("Setting up subscribers...")

        # Database subscriber
        if self.config.enable_database:
            db_subscriber = DatabaseSubscriber(database_url=self.config.database_url)
            generator.add_subscriber(db_subscriber)
            logger.info("✅ DatabaseSubscriber enabled")

        # Logger subscriber
        if self.config.enable_logger:
            logger_subscriber = LoggerSubscriber(log_file='signals.log')
            generator.add_subscriber(logger_subscriber)
            logger.info("✅ LoggerSubscriber enabled")

        # Console subscriber
        if self.config.enable_console:
            console_subscriber = ConsoleSubscriber(use_colors=True, verbose=True)
            generator.add_subscriber(console_subscriber)
            logger.info("✅ ConsoleSubscriber enabled")

        if not any([self.config.enable_database, self.config.enable_logger, self.config.enable_console]):
            logger.warning("⚠️  No subscribers enabled!")

    def _log_heartbeat(self):
        """Log heartbeat to show service is alive."""
        now = datetime.now()

        if self.last_heartbeat is None:
            self.last_heartbeat = now
            return

        # Check if it's time for heartbeat
        minutes_since_last = (now - self.last_heartbeat).total_seconds() / 60

        if minutes_since_last >= self.config.heartbeat_interval:
            uptime = now - self.start_time
            uptime_hours = uptime.total_seconds() / 3600

            logger.info("=" * 70)
            logger.info("💓 HEARTBEAT - Service Status")
            logger.info("=" * 70)
            logger.info(f"Status: RUNNING")
            logger.info(f"Uptime: {uptime_hours:.2f} hours")
            logger.info(f"Candles processed: {self.generator.total_candles_processed}")
            logger.info(f"Signals generated: {self.generator.total_signals_generated}")

            if self.generator.total_candles_processed > 0:
                signal_rate = (self.generator.total_signals_generated /
                              self.generator.total_candles_processed) * 100
                logger.info(f"Signal rate: {signal_rate:.2f}%")

            logger.info("=" * 70)

            self.last_heartbeat = now

    def _wait_with_price_updates(self, check_interval: int = 30):
        """
        Wait for next candle close while showing real-time price updates.

        Args:
            check_interval: Seconds between price checks (default: 30)
        """
        import time
        from datetime import datetime, timedelta

        # Calculate next candle close time
        now = datetime.now()
        tf_hours = {"1H": 1, "4H": 4, "1D": 24}
        hours = tf_hours.get(self.config.timeframe, 4)

        current_hour = now.hour
        next_close_hour = ((current_hour // hours) + 1) * hours

        if next_close_hour >= 24:
            next_close = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        else:
            next_close = now.replace(hour=next_close_hour, minute=0, second=0, microsecond=0)

        last_price = None

        while self.is_running:
            now = datetime.now()

            # Check if candle has closed
            if now >= next_close:
                break

            # Get current price
            try:
                current_price = self.data_feed.get_current_price()

                # Calculate time remaining
                time_remaining = next_close - now
                hours = int(time_remaining.total_seconds() // 3600)
                minutes = int((time_remaining.total_seconds() % 3600) // 60)
                seconds = int(time_remaining.total_seconds() % 60)

                # Calculate price change
                change_str = ""
                if last_price is not None:
                    change = current_price - last_price
                    change_pct = (change / last_price) * 100
                    change_symbol = "+" if change >= 0 else ""
                    change_str = f" | Change: {change_symbol}${change:.2f} ({change_symbol}{change_pct:.3f}%)"

                # Display real-time update (simple format for web compatibility)
                timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
                logger.info(f"[{timestamp}] LIVE: Gold Price ${current_price:,.2f}{change_str} | Next candle in {hours}h {minutes}m {seconds}s")

                last_price = current_price

            except Exception as e:
                logger.warning(f"Failed to get current price: {e}")

            # Sleep until next check
            time.sleep(check_interval)

    def start(self, max_iterations: Optional[int] = None):
        """
        Start the signal service.

        Args:
            max_iterations: Maximum iterations (for testing). None = infinite
        """
        logger.info("=" * 70)
        logger.info("🚀 STARTING SIGNAL SERVICE")
        logger.info("=" * 70)

        # Validate configuration
        if not self.config.validate():
            logger.error("❌ Configuration validation failed!")
            return

        # Log configuration
        logger.info("\n📋 Configuration:")
        for key, value in self.config.to_dict().items():
            logger.info(f"   {key}: {value}")

        try:
            # Create data feed
            self.data_feed = self._create_data_feed()

            # Connect to data feed
            logger.info("\n🔌 Connecting to data feed...")
            if not self.data_feed.connect():
                logger.error("❌ Failed to connect to data feed!")
                return

            # Create strategy
            strategy = self._create_strategy()

            # Create validator
            validator = SignalValidator(min_rr_ratio=self.config.min_rr_ratio)

            # Create signal generator
            self.generator = RealtimeSignalGenerator(
                data_feed=self.data_feed,
                strategy=strategy,
                validator=validator
            )

            # Setup subscribers
            self._setup_subscribers(self.generator)

            # Start signal generation
            logger.info("\n" + "=" * 70)
            logger.info("✅ SERVICE STARTED SUCCESSFULLY")
            logger.info("=" * 70)
            logger.info(f"Symbol: {self.config.symbol}")
            logger.info(f"Timeframe: {self.config.timeframe}")
            logger.info(f"Strategy: Momentum Equilibrium")
            logger.info(f"Data Feed: {self.config.datafeed_type}")
            logger.info(f"Subscribers: {len(self.generator.subscribers)}")
            logger.info("=" * 70)
            logger.info("\n⏳ Waiting for signals...\n")

            self.is_running = True
            self.start_time = datetime.now()
            self.last_heartbeat = datetime.now()

            iteration = 0

            while self.is_running:
                # Check iteration limit (for testing)
                if max_iterations and iteration >= max_iterations:
                    logger.info(f"Reached max iterations ({max_iterations})")
                    break

                iteration += 1

                # Run signal generation
                self.generator.run_once()

                # Log heartbeat
                self._log_heartbeat()

                # Wait for next candle close with real-time price monitoring
                if self.is_running:  # Check again in case stopped during run_once
                    self._wait_with_price_updates(check_interval=30)

        except KeyboardInterrupt:
            logger.info("\n⏹️  Interrupted by user")
        except Exception as e:
            logger.error(f"❌ Fatal error: {e}", exc_info=True)
        finally:
            self.stop()

    def stop(self):
        """Stop the service gracefully."""
        if not self.is_running:
            return

        logger.info("\n" + "=" * 70)
        logger.info("⏹️  STOPPING SIGNAL SERVICE")
        logger.info("=" * 70)

        self.is_running = False

        # Disconnect data feed
        if self.data_feed and self.data_feed.is_connected:
            logger.info("Disconnecting data feed...")
            self.data_feed.disconnect()

        # Log final statistics
        if self.generator and self.start_time:
            runtime = datetime.now() - self.start_time
            runtime_hours = runtime.total_seconds() / 3600

            logger.info("\n📊 FINAL STATISTICS")
            logger.info("=" * 70)
            logger.info(f"Runtime: {runtime_hours:.2f} hours")
            logger.info(f"Candles processed: {self.generator.total_candles_processed}")
            logger.info(f"Signals generated: {self.generator.total_signals_generated}")

            if self.generator.total_candles_processed > 0:
                signal_rate = (self.generator.total_signals_generated /
                              self.generator.total_candles_processed) * 100
                logger.info(f"Signal rate: {signal_rate:.2f}%")

        logger.info("=" * 70)
        logger.info("✅ SERVICE STOPPED SUCCESSFULLY")
        logger.info("=" * 70)

    def get_status(self) -> Dict:
        """Get current service status."""
        if not self.is_running or not self.generator:
            return {
                'status': 'STOPPED',
                'uptime_hours': 0,
                'candles_processed': 0,
                'signals_generated': 0
            }

        uptime = datetime.now() - self.start_time
        uptime_hours = uptime.total_seconds() / 3600

        return {
            'status': 'RUNNING',
            'uptime_hours': uptime_hours,
            'candles_processed': self.generator.total_candles_processed,
            'signals_generated': self.generator.total_signals_generated,
            'signal_rate': (
                (self.generator.total_signals_generated / self.generator.total_candles_processed * 100)
                if self.generator.total_candles_processed > 0
                else 0
            )
        }


if __name__ == "__main__":
    """Run the signal service."""
    print("\n" + "=" * 70)
    print("📊 GOLD TRADER'S EDGE - SIGNAL SERVICE")
    print("=" * 70)
    print("\nPress Ctrl+C to stop the service\n")

    # Create and start service
    service = SignalService()
    service.start()

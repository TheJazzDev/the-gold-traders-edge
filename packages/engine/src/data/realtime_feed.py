"""
Real-time data feed for XAUUSD signal generation.

This module provides an abstraction layer for fetching real-time market data
from various sources. It supports:
- Yahoo Finance (cross-platform, ~15min delay, free)
- MetaTrader 5 (Windows only, requires MT5 terminal)
- MetaAPI (cloud MT5, cross-platform, paid)

The design allows easy switching between data sources without changing
the signal generation code.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import pandas as pd
import time
import os
from enum import Enum


class DataFeedType(Enum):
    """Supported data feed types."""
    YAHOO_FINANCE = "yahoo"
    MT5_LOCAL = "mt5"
    META_API = "metaapi"


class RealtimeDataFeed(ABC):
    """
    Abstract base class for real-time data feeds.

    All implementations must provide:
    - Connection management
    - Latest candle fetching
    - Candle close detection
    - Historical data for indicators
    """

    def __init__(
        self,
        symbol: str = "XAUUSD",
        timeframe: str = "4H",
        lookback_periods: int = 200
    ):
        """
        Initialize data feed.

        Args:
            symbol: Trading symbol (default: XAUUSD)
            timeframe: Candle timeframe (default: 4H)
            lookback_periods: Number of historical candles to fetch for indicators
        """
        self.symbol = symbol
        self.timeframe = timeframe
        self.lookback_periods = lookback_periods
        self.is_connected = False
        self.last_candle_time: Optional[datetime] = None

    @abstractmethod
    def connect(self) -> bool:
        """
        Establish connection to data source.

        Returns:
            True if connection successful, False otherwise
        """
        pass

    @abstractmethod
    def disconnect(self):
        """Close connection to data source."""
        pass

    @abstractmethod
    def get_latest_candles(self, count: int = None) -> pd.DataFrame:
        """
        Fetch latest candles.

        Args:
            count: Number of candles to fetch (default: lookback_periods)

        Returns:
            DataFrame with columns: open, high, low, close, volume
            Index: datetime
        """
        pass

    @abstractmethod
    def get_current_price(self) -> float:
        """
        Get current market price.

        Returns:
            Current bid/ask price
        """
        pass

    def is_new_candle(self, current_candle_time: datetime) -> bool:
        """
        Check if a new candle has formed.

        Args:
            current_candle_time: Timestamp of latest candle

        Returns:
            True if new candle detected
        """
        if self.last_candle_time is None:
            self.last_candle_time = current_candle_time
            return True

        if current_candle_time > self.last_candle_time:
            self.last_candle_time = current_candle_time
            return True

        return False

    def wait_for_candle_close(self, check_interval: int = 60):
        """
        Wait until next candle closes.

        Args:
            check_interval: Seconds between checks (default: 60)
        """
        # Calculate time to next candle close
        now = datetime.now()

        # Map timeframe to hours
        tf_hours = {
            "1H": 1, "4H": 4, "1D": 24
        }
        hours = tf_hours.get(self.timeframe, 4)

        # Calculate next candle close time
        # For 4H: 00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC
        current_hour = now.hour
        next_close_hour = ((current_hour // hours) + 1) * hours

        if next_close_hour >= 24:
            next_close = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        else:
            next_close = now.replace(hour=next_close_hour, minute=0, second=0, microsecond=0)

        wait_seconds = (next_close - now).total_seconds()

        print(f"⏳ Next {self.timeframe} candle closes at {next_close.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"   Waiting {wait_seconds / 60:.1f} minutes...")

        # Wait until candle close
        while datetime.now() < next_close:
            time.sleep(check_interval)

    def get_timeframe_minutes(self) -> int:
        """Get timeframe in minutes."""
        tf_map = {
            "1M": 1, "5M": 5, "15M": 15, "30M": 30,
            "1H": 60, "4H": 240, "1D": 1440
        }
        return tf_map.get(self.timeframe, 240)


class YahooFinanceDataFeed(RealtimeDataFeed):
    """
    Yahoo Finance data feed implementation.

    Pros:
    - Free
    - Cross-platform
    - No account required

    Cons:
    - ~15-20 minute delay
    - Rate limits
    - Not true real-time

    Best for: Development, testing, demo
    """

    def __init__(
        self,
        symbol: str = "XAUUSD",
        timeframe: str = "4H",
        lookback_periods: int = 200
    ):
        super().__init__(symbol, timeframe, lookback_periods)
        self.yf_ticker = None

        # Map XAUUSD to Yahoo ticker
        self.ticker_map = {
            "XAUUSD": "GC=F",  # Gold futures
            "XAGUSD": "SI=F",  # Silver futures
        }

    def connect(self) -> bool:
        """Initialize Yahoo Finance connection."""
        try:
            import yfinance as yf
            self.yf_ticker = yf.Ticker(self.ticker_map.get(self.symbol, "GC=F"))
            self.is_connected = True
            print(f"✅ Connected to Yahoo Finance ({self.ticker_map.get(self.symbol)})")
            return True
        except ImportError:
            print("❌ yfinance not installed. Install with: pip install yfinance")
            return False
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False

    def disconnect(self):
        """Close connection (not needed for Yahoo Finance)."""
        self.is_connected = False
        self.yf_ticker = None

    def get_latest_candles(self, count: int = None) -> pd.DataFrame:
        """
        Fetch latest candles from Yahoo Finance.

        Args:
            count: Number of candles (default: lookback_periods)

        Returns:
            DataFrame with OHLCV data
        """
        if not self.is_connected:
            raise ConnectionError("Not connected. Call connect() first.")

        count = count or self.lookback_periods

        # Map timeframe to yfinance interval
        interval_map = {
            "1M": "1m", "5M": "5m", "15M": "15m", "30M": "30m",
            "1H": "1h", "2H": "2h", "4H": "4h", "1D": "1d"
        }
        interval = interval_map.get(self.timeframe, "4h")

        # Calculate period (Yahoo has limits on historical data)
        # For intraday: max 730 days
        # For daily: unlimited
        if interval in ["1m", "5m", "15m", "30m", "1h", "2h", "4h"]:
            period_days = min(count * self.get_timeframe_minutes() // 1440 + 30, 730)
        else:
            period_days = count

        # Fetch data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days)

        df = self.yf_ticker.history(
            start=start_date.strftime("%Y-%m-%d"),
            end=end_date.strftime("%Y-%m-%d"),
            interval=interval
        )

        # Standardize columns
        df.columns = [col.lower() for col in df.columns]
        df = df[['open', 'high', 'low', 'close', 'volume']].copy()

        # Return last N candles
        return df.tail(count)

    def get_current_price(self) -> float:
        """Get current market price from Yahoo Finance."""
        if not self.is_connected:
            raise ConnectionError("Not connected. Call connect() first.")

        # Get latest quote
        data = self.yf_ticker.history(period="1d", interval="1m")
        if data.empty:
            raise ValueError("No price data available")

        return float(data['Close'].iloc[-1])


class MT5DataFeed(RealtimeDataFeed):
    """
    MetaTrader 5 local data feed (Windows only).

    IMPORTANT: This only works on Windows with MT5 terminal installed.
    For macOS/Linux, use YahooFinanceDataFeed or MetaAPIDataFeed.

    Pros:
    - True real-time data
    - No delays
    - Can execute trades directly

    Cons:
    - Windows only
    - Requires MT5 terminal running
    - Requires broker account

    Best for: Production on Windows server

    Setup:
    1. Install MT5 terminal
    2. Open demo/live account
    3. Install MetaTrader5 package: pip install MetaTrader5
    4. Configure credentials in environment variables
    """

    def __init__(
        self,
        symbol: str = "XAUUSD",
        timeframe: str = "4H",
        lookback_periods: int = 200,
        login: Optional[int] = None,
        password: Optional[str] = None,
        server: Optional[str] = None
    ):
        super().__init__(symbol, timeframe, lookback_periods)
        self.login = login or int(os.getenv("MT5_LOGIN", "0"))
        self.password = password or os.getenv("MT5_PASSWORD", "")
        self.server = server or os.getenv("MT5_SERVER", "")
        self.mt5 = None

    def connect(self) -> bool:
        """
        Connect to MetaTrader 5.

        Returns:
            True if connection successful
        """
        try:
            import MetaTrader5 as MT5
            self.mt5 = MT5
        except ImportError:
            print("❌ MetaTrader5 package not available")
            print("   This package only works on Windows")
            print("   For macOS/Linux, use YahooFinanceDataFeed or MetaAPIDataFeed")
            return False

        # Initialize MT5
        if not self.mt5.initialize():
            print(f"❌ MT5 initialize() failed: {self.mt5.last_error()}")
            return False

        # Login if credentials provided
        if self.login and self.password and self.server:
            authorized = self.mt5.login(
                login=self.login,
                password=self.password,
                server=self.server
            )

            if not authorized:
                print(f"❌ MT5 login failed: {self.mt5.last_error()}")
                self.mt5.shutdown()
                return False

            print(f"✅ Connected to MT5: {self.server} (Account: {self.login})")
        else:
            print("✅ Connected to MT5 (terminal account)")

        self.is_connected = True
        return True

    def disconnect(self):
        """Disconnect from MT5."""
        if self.mt5:
            self.mt5.shutdown()
        self.is_connected = False

    def get_latest_candles(self, count: int = None) -> pd.DataFrame:
        """
        Fetch latest candles from MT5.

        Args:
            count: Number of candles

        Returns:
            DataFrame with OHLCV data
        """
        if not self.is_connected:
            raise ConnectionError("Not connected. Call connect() first.")

        count = count or self.lookback_periods

        # Map timeframe
        tf_map = {
            "1M": self.mt5.TIMEFRAME_M1,
            "5M": self.mt5.TIMEFRAME_M5,
            "15M": self.mt5.TIMEFRAME_M15,
            "30M": self.mt5.TIMEFRAME_M30,
            "1H": self.mt5.TIMEFRAME_H1,
            "4H": self.mt5.TIMEFRAME_H4,
            "1D": self.mt5.TIMEFRAME_D1,
        }
        timeframe = tf_map.get(self.timeframe, self.mt5.TIMEFRAME_H4)

        # Fetch candles
        rates = self.mt5.copy_rates_from_pos(self.symbol, timeframe, 0, count)

        if rates is None or len(rates) == 0:
            raise ValueError(f"No data for {self.symbol}")

        # Convert to DataFrame
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df = df.set_index('time')

        # Rename columns
        df = df.rename(columns={
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'tick_volume': 'volume'
        })

        return df[['open', 'high', 'low', 'close', 'volume']]

    def get_current_price(self) -> float:
        """Get current market price from MT5."""
        if not self.is_connected:
            raise ConnectionError("Not connected. Call connect() first.")

        tick = self.mt5.symbol_info_tick(self.symbol)
        if tick is None:
            raise ValueError(f"No tick data for {self.symbol}")

        # Return bid price
        return tick.bid


class MetaAPIDataFeed(RealtimeDataFeed):
    """
    MetaAPI cloud data feed (cross-platform).

    MetaAPI provides cloud access to MT4/MT5 accounts from any platform.

    Pros:
    - Cross-platform (macOS, Linux, Windows)
    - Cloud-based, no terminal needed
    - Reliable infrastructure

    Cons:
    - Paid service ($49/month)
    - Requires MetaAPI account
    - Additional latency

    Best for: Production deployment on any platform

    Setup:
    1. Sign up at https://metaapi.cloud/
    2. Add your MT5 demo/live account
    3. Get API token
    4. Install: pip install metaapi-cloud-sdk
    5. Set environment variable: METAAPI_TOKEN

    Documentation: https://metaapi.cloud/docs/
    """

    def __init__(
        self,
        symbol: str = "XAUUSD",
        timeframe: str = "4H",
        lookback_periods: int = 200,
        token: Optional[str] = None,
        account_id: Optional[str] = None
    ):
        super().__init__(symbol, timeframe, lookback_periods)
        self.token = token or os.getenv("METAAPI_TOKEN", "")
        self.account_id = account_id or os.getenv("METAAPI_ACCOUNT_ID", "")
        self.api = None
        self.account = None
        self.connection = None

    def connect(self) -> bool:
        """Connect to MetaAPI."""
        try:
            from metaapi_cloud_sdk import MetaApi
        except ImportError:
            print("❌ metaapi-cloud-sdk not installed")
            print("   Install with: pip install metaapi-cloud-sdk")
            return False

        if not self.token or not self.account_id:
            print("❌ MetaAPI credentials not configured")
            print("   Set METAAPI_TOKEN and METAAPI_ACCOUNT_ID environment variables")
            return False

        try:
            # Initialize API
            self.api = MetaApi(self.token)
            self.account = self.api.metatrader_account_api.get_account(self.account_id)

            # Wait until account is deployed and connected
            self.account.deploy()
            self.account.wait_connected()

            # Create connection
            self.connection = self.account.get_rpc_connection()
            self.connection.connect()
            self.connection.wait_synchronized()

            self.is_connected = True
            print(f"✅ Connected to MetaAPI (Account: {self.account_id})")
            return True

        except Exception as e:
            print(f"❌ MetaAPI connection failed: {e}")
            return False

    def disconnect(self):
        """Disconnect from MetaAPI."""
        if self.connection:
            self.connection.close()
        self.is_connected = False

    def get_latest_candles(self, count: int = None) -> pd.DataFrame:
        """Fetch latest candles from MetaAPI."""
        if not self.is_connected:
            raise ConnectionError("Not connected. Call connect() first.")

        count = count or self.lookback_periods

        # Fetch candles
        candles = self.connection.get_candles(
            symbol=self.symbol,
            timeframe=self.timeframe,
            count=count
        )

        # Convert to DataFrame
        df = pd.DataFrame(candles)
        df['time'] = pd.to_datetime(df['time'])
        df = df.set_index('time')

        return df[['open', 'high', 'low', 'close', 'volume']]

    def get_current_price(self) -> float:
        """Get current market price from MetaAPI."""
        if not self.is_connected:
            raise ConnectionError("Not connected. Call connect() first.")

        symbol_price = self.connection.get_symbol_price(self.symbol)
        return symbol_price['bid']


def create_datafeed(
    feed_type: str = None,
    symbol: str = "XAUUSD",
    timeframe: str = "4H",
    lookback_periods: int = 200,
    **kwargs
) -> RealtimeDataFeed:
    """
    Factory function to create appropriate data feed.

    Args:
        feed_type: Type of feed ("yahoo", "mt5", "metaapi")
                   If None, auto-detects based on platform and config
        symbol: Trading symbol
        timeframe: Candle timeframe
        lookback_periods: Number of historical candles
        **kwargs: Additional arguments for specific feed types

    Returns:
        Configured data feed instance

    Example:
        # Auto-detect (uses Yahoo Finance on macOS, MT5 on Windows if available)
        feed = create_datafeed()

        # Explicitly use Yahoo Finance
        feed = create_datafeed(feed_type="yahoo")

        # Use MetaAPI
        feed = create_datafeed(
            feed_type="metaapi",
            token="your-token",
            account_id="your-account-id"
        )
    """
    # Auto-detect if not specified
    if feed_type is None:
        feed_type = os.getenv("DATAFEED_TYPE", "yahoo")

    feed_type = feed_type.lower()

    if feed_type == "yahoo":
        return YahooFinanceDataFeed(symbol, timeframe, lookback_periods)

    elif feed_type == "mt5":
        return MT5DataFeed(
            symbol, timeframe, lookback_periods,
            login=kwargs.get('login'),
            password=kwargs.get('password'),
            server=kwargs.get('server')
        )

    elif feed_type == "metaapi":
        return MetaAPIDataFeed(
            symbol, timeframe, lookback_periods,
            token=kwargs.get('token'),
            account_id=kwargs.get('account_id')
        )

    else:
        raise ValueError(f"Unknown feed type: {feed_type}")


if __name__ == "__main__":
    """Test the data feed."""
    print("=" * 70)
    print("🔄 TESTING REAL-TIME DATA FEED")
    print("=" * 70)

    # Create data feed (auto-detect)
    print("\n1. Creating data feed...")
    feed = create_datafeed(feed_type="yahoo")

    # Connect
    print("\n2. Connecting...")
    if not feed.connect():
        print("❌ Connection failed!")
        exit(1)

    # Fetch latest candles
    print("\n3. Fetching latest 10 candles...")
    df = feed.get_latest_candles(count=10)
    print(df)
    print(f"\n   Latest close: ${df['close'].iloc[-1]:.2f}")

    # Get current price
    print("\n4. Getting current price...")
    current_price = feed.get_current_price()
    print(f"   Current price: ${current_price:.2f}")

    # Test new candle detection
    print("\n5. Testing candle close detection...")
    latest_time = df.index[-1]
    print(f"   Latest candle time: {latest_time}")
    print(f"   Is new candle: {feed.is_new_candle(latest_time)}")
    print(f"   Is new candle (again): {feed.is_new_candle(latest_time)}")

    # Disconnect
    print("\n6. Disconnecting...")
    feed.disconnect()

    print("\n" + "=" * 70)
    print("✅ DATA FEED TEST COMPLETE!")
    print("=" * 70)

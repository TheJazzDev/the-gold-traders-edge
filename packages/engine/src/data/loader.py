"""
Data Loader Module
Handles fetching and loading historical gold (XAUUSD) data from various sources.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Tuple
import requests
import io
import zipfile
import os


class GoldDataLoader:
    """
    Loader for historical gold (XAUUSD) price data.
    
    Supports multiple data sources:
    - Yahoo Finance (via yfinance)
    - HistData.com (free CSV downloads)
    - Local CSV files
    """
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.raw_dir = self.data_dir / "raw"
        self.processed_dir = self.data_dir / "processed"
        
        # Create directories if they don't exist
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
    
    def load_from_yfinance(
        self, 
        start_date: str = "2015-01-01",
        end_date: Optional[str] = None,
        interval: str = "1h"
    ) -> pd.DataFrame:
        """
        Load gold data from Yahoo Finance.
        
        Args:
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date (defaults to today)
            interval: Data interval ('1m', '5m', '15m', '1h', '1d', '1wk')
        
        Returns:
            DataFrame with OHLCV data
        """
        try:
            import yfinance as yf
        except ImportError:
            raise ImportError("Please install yfinance: pip install yfinance")
        
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        # Gold ticker on Yahoo Finance
        ticker = "GC=F"  # Gold futures
        
        print(f"Fetching gold data from Yahoo Finance...")
        print(f"Period: {start_date} to {end_date}, Interval: {interval}")
        
        gold = yf.Ticker(ticker)
        df = gold.history(start=start_date, end=end_date, interval=interval)
        
        # Standardize column names
        df.columns = [col.lower() for col in df.columns]
        df = df.rename(columns={
            'open': 'open',
            'high': 'high', 
            'low': 'low',
            'close': 'close',
            'volume': 'volume'
        })
        
        # Keep only OHLCV columns
        df = df[['open', 'high', 'low', 'close', 'volume']].copy()
        
        print(f"Loaded {len(df)} candles")
        return df
    
    def load_from_csv(
        self,
        filepath: str,
        date_column: str = 'datetime',
        date_format: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Load gold data from a local CSV file.

        Args:
            filepath: Path to CSV file
            date_column: Name of the datetime column
            date_format: Date format string (auto-detected if None)

        Returns:
            DataFrame with OHLCV data
        """
        print(f"Loading data from {filepath}...")

        df = pd.read_csv(filepath)

        # Try to identify and parse datetime column (case-insensitive)
        possible_date_cols = ['datetime', 'date', 'time', 'timestamp', 'Datetime', 'Date', 'DateTime', 'Time']

        date_col_found = None
        for col in possible_date_cols:
            if col in df.columns:
                date_col_found = col
                break

        if date_col_found:
            df[date_col_found] = pd.to_datetime(df[date_col_found], format=date_format, utc=True)
            df = df.set_index(date_col_found)

        # Standardize column names
        df.columns = [col.lower() for col in df.columns]

        # Rename common variations
        rename_map = {
            'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume',
            'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'
        }
        df = df.rename(columns=rename_map)

        print(f"Loaded {len(df)} candles")
        return df
    
    def download_histdata(
        self,
        year: int,
        month: Optional[int] = None,
        timeframe: str = "M1"
    ) -> pd.DataFrame:
        """
        Download data from HistData.com (free source).
        
        Note: This requires manual download from histdata.com as they don't have
        a direct API. This method processes already downloaded files.
        
        Args:
            year: Year of data
            month: Month (1-12) or None for full year
            timeframe: Timeframe (M1, M5, M15, M30, H1, H4, D1)
        
        Returns:
            DataFrame with OHLCV data
        """
        # HistData format: HISTDATA_COM_ASCII_XAUUSD_M12024.zip
        if month:
            filename = f"HISTDATA_COM_ASCII_XAUUSD_{timeframe}{year}{month:02d}.zip"
        else:
            filename = f"HISTDATA_COM_ASCII_XAUUSD_{timeframe}{year}.zip"
        
        filepath = self.raw_dir / filename
        
        if not filepath.exists():
            print(f"File not found: {filepath}")
            print(f"\nTo download HistData:")
            print(f"1. Go to https://www.histdata.com/download-free-forex-historical-data/")
            print(f"2. Select XAU/USD (Gold)")
            print(f"3. Download {timeframe} data for {year}")
            print(f"4. Save to: {self.raw_dir}")
            return pd.DataFrame()
        
        # Extract and parse
        with zipfile.ZipFile(filepath, 'r') as z:
            csv_name = z.namelist()[0]
            with z.open(csv_name) as f:
                # HistData format: DateTime,Open,High,Low,Close,Volume
                df = pd.read_csv(
                    f,
                    names=['datetime', 'open', 'high', 'low', 'close', 'volume'],
                    parse_dates=['datetime'],
                    sep=';'
                )
        
        df = df.set_index('datetime')
        print(f"Loaded {len(df)} candles from HistData")
        return df
    
    def resample_timeframe(
        self, 
        df: pd.DataFrame, 
        target_timeframe: str = "4h"
    ) -> pd.DataFrame:
        """
        Resample data to a higher timeframe.
        
        Args:
            df: DataFrame with OHLCV data
            target_timeframe: Target timeframe ('5min', '15min', '1h', '4h', '1D')
        
        Returns:
            Resampled DataFrame
        """
        ohlc_dict = {
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }
        
        # Map common timeframe strings to pandas offset strings
        tf_map = {
            '5min': '5min', '5m': '5min', 'M5': '5min',
            '15min': '15min', '15m': '15min', 'M15': '15min',
            '30min': '30min', '30m': '30min', 'M30': '30min',
            '1h': '1h', 'H1': '1h', '1H': '1h',
            '4h': '4h', 'H4': '4h', '4H': '4h',
            '1D': '1D', 'D1': '1D', 'D': '1D', '1d': '1D',
            '1W': '1W', 'W1': '1W', 'W': '1W'
        }
        
        tf = tf_map.get(target_timeframe, target_timeframe)
        
        resampled = df.resample(tf).agg(ohlc_dict)
        resampled = resampled.dropna()
        
        print(f"Resampled to {target_timeframe}: {len(resampled)} candles")
        return resampled
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and validate OHLCV data.
        
        - Removes duplicates
        - Handles missing values
        - Validates OHLC relationships
        - Removes outliers
        """
        original_len = len(df)
        
        # Remove duplicates
        df = df[~df.index.duplicated(keep='first')]
        
        # Drop rows with missing values
        df = df.dropna()
        
        # Validate OHLC relationships (High >= Open, Close, Low)
        invalid_mask = (
            (df['high'] < df['open']) | 
            (df['high'] < df['close']) |
            (df['high'] < df['low']) |
            (df['low'] > df['open']) |
            (df['low'] > df['close'])
        )
        df = df[~invalid_mask]
        
        # Remove extreme outliers (price changes > 10% in one candle)
        pct_change = df['close'].pct_change().abs()
        df = df[pct_change < 0.10]
        
        removed = original_len - len(df)
        if removed > 0:
            print(f"Cleaned data: removed {removed} invalid rows")
        
        return df
    
    def save_processed(
        self, 
        df: pd.DataFrame, 
        filename: str = "xauusd_processed.csv"
    ) -> Path:
        """Save processed data to CSV."""
        filepath = self.processed_dir / filename
        df.to_csv(filepath)
        print(f"Saved processed data to {filepath}")
        return filepath
    
    def load_processed(self, filename: str = "xauusd_processed.csv") -> pd.DataFrame:
        """Load previously processed data."""
        filepath = self.processed_dir / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Processed data not found: {filepath}")
        
        df = pd.read_csv(filepath, index_col=0, parse_dates=True)
        print(f"Loaded processed data: {len(df)} candles")
        return df


def generate_sample_data(
    start_date: str = "2020-01-01",
    end_date: str = "2024-12-01",
    timeframe: str = "4h"
) -> pd.DataFrame:
    """
    Generate synthetic gold price data for testing.
    
    This creates realistic-looking price action with trends,
    retracements, and volatility similar to XAUUSD.
    """
    # Parse dates
    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)
    
    # Generate datetime index based on timeframe
    tf_map = {'1h': 'h', '4h': '4h', '1D': 'D'}
    freq = tf_map.get(timeframe, '4h')
    
    # Create index (exclude weekends for forex)
    dates = pd.date_range(start=start, end=end, freq=freq)
    dates = dates[dates.dayofweek < 5]  # Remove weekends
    
    n = len(dates)
    
    # Starting price around $1800
    base_price = 1800
    
    # Generate trending price with mean reversion
    np.random.seed(42)  # For reproducibility
    
    # Random walk with drift
    returns = np.random.normal(0.0001, 0.003, n)  # Small positive drift
    
    # Add some trending behavior
    trend = np.cumsum(np.random.normal(0, 0.001, n))
    
    # Add mean reversion
    mean_rev = np.zeros(n)
    for i in range(1, n):
        mean_rev[i] = -0.01 * (np.cumsum(returns[:i])[-1])
    
    cumulative_returns = np.cumsum(returns + trend + mean_rev)
    close_prices = base_price * np.exp(cumulative_returns)
    
    # Generate OHLC from close prices
    volatility = 0.002  # Intrabar volatility
    
    high = close_prices * (1 + np.abs(np.random.normal(0, volatility, n)))
    low = close_prices * (1 - np.abs(np.random.normal(0, volatility, n)))
    
    # Open is previous close with small gap
    open_prices = np.roll(close_prices, 1) * (1 + np.random.normal(0, 0.0005, n))
    open_prices[0] = base_price
    
    # Ensure OHLC validity
    high = np.maximum(high, np.maximum(open_prices, close_prices))
    low = np.minimum(low, np.minimum(open_prices, close_prices))
    
    # Volume (higher on volatile days)
    price_change = np.abs(np.diff(close_prices, prepend=close_prices[0]))
    volume = 1000 + price_change * 100 + np.random.exponential(500, n)
    
    df = pd.DataFrame({
        'open': open_prices,
        'high': high,
        'low': low,
        'close': close_prices,
        'volume': volume.astype(int)
    }, index=dates)
    
    print(f"Generated {len(df)} synthetic candles from {start_date} to {end_date}")
    return df


if __name__ == "__main__":
    # Example usage
    loader = GoldDataLoader()
    
    # Try to load from Yahoo Finance
    try:
        df = loader.load_from_yfinance(
            start_date="2023-01-01",
            end_date="2024-12-01",
            interval="1h"
        )
        
        # Resample to 4H
        df_4h = loader.resample_timeframe(df, "4h")
        
        # Clean data
        df_clean = loader.clean_data(df_4h)
        
        # Save
        loader.save_processed(df_clean, "xauusd_4h.csv")
        
    except Exception as e:
        print(f"Could not load from yfinance: {e}")
        print("Generating sample data instead...")
        
        df = generate_sample_data()
        loader.save_processed(df, "xauusd_sample_4h.csv")

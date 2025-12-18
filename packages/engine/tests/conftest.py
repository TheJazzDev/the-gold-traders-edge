"""
Pytest configuration and shared fixtures.
"""

import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add src to path for all tests
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))


@pytest.fixture
def sample_ohlcv_df():
    """Generate sample OHLCV DataFrame for testing."""
    np.random.seed(42)
    dates = pd.date_range(start='2024-01-01', periods=200, freq='4h')
    
    # Generate realistic price data
    base_price = 2000
    returns = np.random.normal(0.0001, 0.002, len(dates))
    cumulative_returns = np.cumsum(returns)
    close = base_price * np.exp(cumulative_returns)
    
    # Generate OHLC from close
    volatility = 0.002
    high = close * (1 + np.abs(np.random.normal(0, volatility, len(dates))))
    low = close * (1 - np.abs(np.random.normal(0, volatility, len(dates))))
    open_prices = np.roll(close, 1) * (1 + np.random.normal(0, 0.0005, len(dates)))
    open_prices[0] = base_price
    
    # Ensure OHLC validity
    high = np.maximum(high, np.maximum(open_prices, close))
    low = np.minimum(low, np.minimum(open_prices, close))
    
    df = pd.DataFrame({
        'open': open_prices,
        'high': high,
        'low': low,
        'close': close,
        'volume': np.random.randint(1000, 10000, len(dates))
    }, index=dates)
    
    return df


@pytest.fixture
def uptrend_df():
    """Generate uptrending OHLCV data."""
    np.random.seed(123)
    dates = pd.date_range(start='2024-01-01', periods=100, freq='4h')
    
    # Strong uptrend
    close = 2000 + np.arange(100) * 5 + np.random.normal(0, 2, 100)
    high = close + np.abs(np.random.normal(0, 3, 100))
    low = close - np.abs(np.random.normal(0, 3, 100))
    open_prices = close - np.random.uniform(0, 3, 100)
    
    high = np.maximum(high, np.maximum(open_prices, close))
    low = np.minimum(low, np.minimum(open_prices, close))
    
    return pd.DataFrame({
        'open': open_prices,
        'high': high,
        'low': low,
        'close': close,
        'volume': np.random.randint(1000, 10000, 100)
    }, index=dates)


@pytest.fixture
def downtrend_df():
    """Generate downtrending OHLCV data."""
    np.random.seed(456)
    dates = pd.date_range(start='2024-01-01', periods=100, freq='4h')
    
    # Strong downtrend
    close = 2500 - np.arange(100) * 5 + np.random.normal(0, 2, 100)
    high = close + np.abs(np.random.normal(0, 3, 100))
    low = close - np.abs(np.random.normal(0, 3, 100))
    open_prices = close + np.random.uniform(0, 3, 100)
    
    high = np.maximum(high, np.maximum(open_prices, close))
    low = np.minimum(low, np.minimum(open_prices, close))
    
    return pd.DataFrame({
        'open': open_prices,
        'high': high,
        'low': low,
        'close': close,
        'volume': np.random.randint(1000, 10000, 100)
    }, index=dates)

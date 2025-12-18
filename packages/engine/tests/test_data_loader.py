"""
Tests for the Data Loader module.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import tempfile
import os
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from data.loader import GoldDataLoader, generate_sample_data


class TestGoldDataLoader:
    """Tests for GoldDataLoader class."""

    @pytest.fixture
    def loader(self, tmp_path):
        """Create a loader with temporary directory."""
        return GoldDataLoader(data_dir=str(tmp_path))

    @pytest.fixture
    def sample_csv(self, tmp_path):
        """Create a sample CSV file."""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='4h')
        df = pd.DataFrame({
            'datetime': dates,
            'open': np.random.uniform(1900, 2100, 100),
            'high': np.random.uniform(1950, 2150, 100),
            'low': np.random.uniform(1850, 2050, 100),
            'close': np.random.uniform(1900, 2100, 100),
            'volume': np.random.randint(1000, 10000, 100)
        })
        
        # Ensure OHLC validity
        df['high'] = df[['open', 'high', 'close']].max(axis=1)
        df['low'] = df[['open', 'low', 'close']].min(axis=1)
        
        csv_path = tmp_path / 'test_data.csv'
        df.to_csv(csv_path, index=False)
        return csv_path

    def test_loader_initialization(self, loader):
        """Test loader creates directories."""
        assert loader.raw_dir.exists()
        assert loader.processed_dir.exists()

    def test_load_from_csv(self, loader, sample_csv):
        """Test loading data from CSV."""
        df = loader.load_from_csv(str(sample_csv))
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 100
        assert 'open' in df.columns
        assert 'high' in df.columns
        assert 'low' in df.columns
        assert 'close' in df.columns

    def test_resample_timeframe(self, loader, sample_csv):
        """Test resampling to higher timeframe."""
        df = loader.load_from_csv(str(sample_csv))
        
        # Resample 4h to 1D
        resampled = loader.resample_timeframe(df, '1D')
        
        assert len(resampled) < len(df)
        assert 'open' in resampled.columns

    def test_clean_data(self, loader):
        """Test data cleaning."""
        # Create data with some issues
        dates = pd.date_range(start='2024-01-01', periods=10, freq='4h')
        df = pd.DataFrame({
            'open': [100, 100, 100, 100, 100, 100, 100, 100, 100, 100],
            'high': [110, 110, 110, 110, 110, 110, 110, 110, 110, 110],
            'low': [90, 90, 90, 90, 90, 90, 90, 90, 90, 90],
            'close': [105, 105, 105, 105, 105, 105, 105, 105, 105, 105],
            'volume': [1000] * 10
        }, index=dates)
        
        # Add an invalid row (high < low)
        df.loc[dates[5], 'high'] = 80
        df.loc[dates[5], 'low'] = 120
        
        cleaned = loader.clean_data(df)
        
        # Invalid row should be removed
        assert len(cleaned) < len(df)

    def test_save_and_load_processed(self, loader):
        """Test saving and loading processed data."""
        dates = pd.date_range(start='2024-01-01', periods=50, freq='4h')
        df = pd.DataFrame({
            'open': np.random.uniform(1900, 2100, 50),
            'high': np.random.uniform(1950, 2150, 50),
            'low': np.random.uniform(1850, 2050, 50),
            'close': np.random.uniform(1900, 2100, 50),
            'volume': np.random.randint(1000, 10000, 50)
        }, index=dates)
        
        # Save
        filepath = loader.save_processed(df, 'test_processed.csv')
        assert filepath.exists()
        
        # Load
        loaded = loader.load_processed('test_processed.csv')
        assert len(loaded) == len(df)


class TestGenerateSampleData:
    """Tests for generate_sample_data function."""

    def test_generate_sample_data_default(self):
        """Test generating sample data with defaults."""
        df = generate_sample_data()
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert 'open' in df.columns
        assert 'high' in df.columns
        assert 'low' in df.columns
        assert 'close' in df.columns
        assert 'volume' in df.columns

    def test_generate_sample_data_custom_dates(self):
        """Test generating sample data with custom date range."""
        df = generate_sample_data(
            start_date='2023-01-01',
            end_date='2023-06-01',
            timeframe='4h'
        )
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert df.index[0] >= pd.Timestamp('2023-01-01')

    def test_generate_sample_data_ohlc_validity(self):
        """Test that generated data has valid OHLC relationships."""
        df = generate_sample_data()
        
        # High should be >= Open, Close
        assert (df['high'] >= df['open']).all()
        assert (df['high'] >= df['close']).all()
        
        # Low should be <= Open, Close
        assert (df['low'] <= df['open']).all()
        assert (df['low'] <= df['close']).all()

    def test_generate_sample_data_no_weekends(self):
        """Test that generated data excludes weekends."""
        df = generate_sample_data()
        
        # Check that no Saturday (5) or Sunday (6) data
        weekdays = df.index.dayofweek
        assert not (weekdays == 5).any()
        assert not (weekdays == 6).any()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

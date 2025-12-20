"""
Data package for loading historical and real-time market data.
"""

from .loader import GoldDataLoader, generate_sample_data

__all__ = ['GoldDataLoader', 'generate_sample_data']

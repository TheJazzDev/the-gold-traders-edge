# Gold Signal Engine

A professional forex signal application focused on gold (XAUUSD) trading with backtesting capabilities.

## Features

- **Real-time Signal Generation**: Based on proven gold trading patterns
- **Comprehensive Backtesting**: Validate strategies against historical data
- **Technical Analysis**: Fibonacci retracements, swing highs/lows, trend detection
- **Risk Management**: Automated stop-loss and take-profit calculations
- **MT5 Integration**: (Phase 3) Direct trade execution via MetaTrader 5

## Project Structure

```
gold-signal-engine/
├── src/
│   ├── data/           # Data fetching and processing
│   ├── analysis/       # Technical analysis (Fib, swings, etc.)
│   ├── backtesting/    # Backtesting engine
│   ├── signals/        # Signal generation logic
│   └── utils/          # Helper functions
├── tests/              # Unit and integration tests
├── data/
│   ├── raw/            # Raw downloaded data
│   └── processed/      # Cleaned and processed data
├── config/             # Configuration files
└── notebooks/          # Jupyter notebooks for exploration
```

## Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/gold-signal-engine.git
cd gold-signal-engine

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Quick Start

```python
from src.backtesting.engine import BacktestEngine
from src.signals.gold_strategy import GoldStrategy

# Initialize
engine = BacktestEngine()
strategy = GoldStrategy()

# Run backtest
results = engine.run(strategy, start_date="2020-01-01", end_date="2024-12-01")
print(results.summary())
```

## Trading Rules

This engine implements 5 core gold trading rules:
1. [To be documented]
2. [To be documented]
3. [To be documented]
4. [To be documented]
5. [To be documented]

## License

MIT License

## Disclaimer

This software is for educational purposes only. Trading forex involves significant risk. Past performance does not guarantee future results.

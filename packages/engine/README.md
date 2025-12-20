# Gold Signal Engine 🥇

The core trading engine for **The Gold Trader's Edge** platform. Implements profitable gold (XAU/USD) trading strategies validated on 2+ years of real data.

## Features

- **Profitable Strategies Only**: All rules tested and validated on 2023-2025 real data
- **Comprehensive Backtesting**: Full P&L tracking, win rates, drawdown analysis
- **Technical Analysis**: Fibonacci, swing detection, momentum, market sessions
- **Smart Money Concepts**: Order blocks, institutional zones
- **Risk Management**: ATR-based stops, configurable R:R ratios

## Trading Strategies

All strategies validated on XAUUSD 4H data (2023-2025):

| Strategy | Win Rate | Profit Factor | Performance | Status |
|----------|----------|---------------|-------------|--------|
| **Momentum Equilibrium** | 74.0% | 3.31 | +$21K profit | ⭐ STAR PERFORMER |
| **London Session Breakout** | 58.8% | 2.74 | +$2.6K profit | ✅ STRONG |
| **Golden Fibonacci** | 49.1% | 1.31 | +$2.2K profit | ⚠️  MARGINAL |
| **Order Block Retest** | 38.6% | 1.14 | +$2.1K profit | ⚠️  MARGINAL |
| **ATH/ATL Retest** | 38.3% | 1.06 | +$287 profit | ⚠️  MARGINAL |
| **Bollinger Squeeze** | 31.2% | 1.07 | +$87 profit | ⚠️  MARGINAL |

**Default Configuration**: Uses Momentum Equilibrium + London Breakout (top 2 performers)

## Installation

```bash
cd packages/engine

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Quick Start

### Run Backtest (Command Line)

```bash
# Run with default strategies (momentum + london)
python run_backtest.py

# Test star performer only
python run_backtest.py --rules momentum

# Test multiple strategies
python run_backtest.py --rules momentum,london,fibonacci

# Use your own data
python run_backtest.py --data path/to/your/xauusd.csv

# Custom risk settings
python run_backtest.py --balance 50000 --risk 1.5

# Export results
python run_backtest.py --output results.json

# Available strategy names:
#   momentum, equilibrium  - Momentum Equilibrium (⭐ best performer)
#   london                 - London Session Breakout
#   fibonacci, golden      - Golden Fibonacci 61.8%
#   orderblock             - Order Block Retest
#   ath                    - ATH/ATL Retest
#   bollinger              - Bollinger Squeeze
```

### Run Backtest (Python)

```python
import sys
sys.path.insert(0, 'src')

from data.loader import generate_sample_data
from signals.gold_strategy import GoldStrategy, create_strategy_function
from backtesting.engine import BacktestEngine

# Load data
df = generate_sample_data(start_date="2023-01-01", end_date="2024-01-01")

# Initialize strategy
strategy = GoldStrategy()

# Enable specific strategies (optional)
strategy.set_rule_enabled('golden_fibonacci', True)
strategy.set_rule_enabled('order_block_retest', False)

# Run backtest
engine = BacktestEngine(initial_balance=10000, position_size_pct=2.0)
result = engine.run(df, create_strategy_function(strategy))

# View results
print(result.summary())

# Export trades to DataFrame
trades_df = result.to_dataframe()
```

### Using Real Data

```python
from data.loader import GoldDataLoader

loader = GoldDataLoader()

# From Yahoo Finance
df = loader.load_from_yfinance(
    start_date="2022-01-01",
    end_date="2024-01-01",
    interval="1h"
)

# Resample to 4H
df = loader.resample_timeframe(df, "4h")

# Clean data
df = loader.clean_data(df)
```

## Project Structure

```
packages/engine/
├── src/
│   ├── data/
│   │   └── loader.py          # Data fetching (yfinance, CSV, HistData)
│   ├── analysis/
│   │   └── technical.py       # Fib, swings, trends, ATR, RSI
│   ├── backtesting/
│   │   └── engine.py          # Backtest engine with P&L tracking
│   └── signals/
│       └── gold_strategy.py   # The 6 gold trading rules
├── config/
│   └── default.yaml           # Strategy configuration
├── run_backtest.py            # CLI backtest runner
└── requirements.txt
```

## Configuration

Edit `config/default.yaml` to customize:

```yaml
strategy:
  fib_tolerance: 0.015      # 1.5% tolerance around Fib levels
  swing_lookback: 5         # Candles for swing detection
  trend_lookback: 50        # Candles for trend analysis

risk:
  position_size_pct: 2.0    # Risk 2% per trade
  default_rr_ratio: 2.0     # Take profit at 2:1 R:R
```

## Backtest Results (Momentum Equilibrium Only)

```
╔══════════════════════════════════════════════════════════════╗
║                    BACKTEST RESULTS                          ║
╠══════════════════════════════════════════════════════════════╣
║  Period: 2023-12-18 to 2025-12-17 (2 years)
║
║  PERFORMANCE
║  Initial Balance:     $10,000.00
║  Final Balance:       $31,180.39
║  Net Profit:          $21,180.39 (211.80%) ⭐
║
║  TRADE STATISTICS
║  Total Trades:        104
║  Winning Trades:      77
║  Losing Trades:       27
║  Win Rate:            74.04%
║
║  PROFIT METRICS
║  Profit Factor:       3.31
║  Average Win:         $401.76
║  Average Loss:        $345.89
║  Largest Win:         $1,179.07
║  Max Drawdown:        9.07%
║  Sharpe Ratio:        8.67
╚══════════════════════════════════════════════════════════════╝
```

**Real Data**: Tested on actual XAUUSD 4H candles from 2023-2025.
**Next Step**: Paper trading for 30-60 days before live deployment.

## Data Sources

| Source | Type | Notes |
|--------|------|-------|
| Yahoo Finance | Free | `GC=F` (Gold Futures), limited history |
| HistData.com | Free | Download manually, high quality M1 data |
| Dukascopy | Free | Tick data, requires manual download |
| Your Broker | Varies | Export from MT5/MT4 |

## Testing the Strategy

1. **Generate Sample Data**: Quick test with synthetic data
2. **Historical Backtest**: Test on real historical data
3. **Walk-Forward Test**: Split data into train/test periods
4. **Paper Trading**: Run live signals without real money
5. **Live Trading**: After validation, connect to MT5

## Disclaimer

⚠️ **This software is for educational purposes only.** Trading forex/gold involves significant risk of loss. Past backtest performance does not guarantee future results. Always use proper risk management and never trade with money you cannot afford to lose.

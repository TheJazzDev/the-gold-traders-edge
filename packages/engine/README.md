# Gold Signal Engine 🥇

The core trading engine for **The Gold Trader's Edge** platform. Implements 6 proven gold (XAU/USD) trading rules with comprehensive backtesting.

## Features

- **6 Gold Trading Rules**: Based on years of XAU/USD study and backtesting
- **Comprehensive Backtesting**: Full P&L tracking, win rates, drawdown analysis
- **Technical Analysis**: Fibonacci, swing detection, CHoCH/BOS, reversal patterns
- **Market Structure Detection**: Identifies trend changes and continuations
- **Risk Management**: ATR-based stops, configurable R:R ratios

## The 6 Gold Hard Facts

| Rule | Name | Description |
|------|------|-------------|
| 1 | **61.8% Golden Retracement** | Price always retraces to 61.8% - enter on CHoCH/BOS confirmation |
| 2 | **78.6% Deep Discount** | High probability entry zone with liquidity sweep confirmation |
| 3 | **23.6% Shallow Pullback** | Strong momentum continuation - minimal retracement |
| 4 | **Consolidation Break** | Choppy candles = correction, enter on range break |
| 5 | **ATH Breakout Retest** | Safe trend entry after ATH break + pullback + consolidation |
| 6 | **50% Momentum** | Equilibrium entry in high momentum environments |

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
# Run with all rules on sample data
python run_backtest.py

# Custom date range
python run_backtest.py --start 2023-01-01 --end 2024-06-01

# Test specific rules only
python run_backtest.py --rules 1,2,5

# Use your own data
python run_backtest.py --data path/to/your/xauusd.csv

# Custom risk settings
python run_backtest.py --balance 50000 --risk 1.5

# Export results
python run_backtest.py --output results.json
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

# Disable specific rules (optional)
strategy.set_rule_enabled('rule_3_236_shallow_pullback', False)

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

## Backtest Results Example

```
╔══════════════════════════════════════════════════════════════╗
║                    BACKTEST RESULTS                          ║
╠══════════════════════════════════════════════════════════════╣
║  Period: 2023-01-02 to 2024-05-31
║  
║  PERFORMANCE
║  Initial Balance:     $10,000.00
║  Final Balance:       $11,502.06
║  Net Profit:          $1,502.06 (15.02%)
║  
║  TRADE STATISTICS
║  Total Trades:        23
║  Winning Trades:      12
║  Losing Trades:       11
║  Win Rate:            52.17%
║  
║  PROFIT METRICS
║  Profit Factor:       1.64
║  Average Win:         $339.53
║  Average Loss:        $225.49
║  Sharpe Ratio:        3.75
╚══════════════════════════════════════════════════════════════╝
```

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

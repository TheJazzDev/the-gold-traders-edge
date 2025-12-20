# Real-Time Data Feed Guide

This guide explains how to configure and use different data feeds for the real-time signal generation system.

---

## Overview

The system supports **three data feed options**:

| Data Feed | Platform | Cost | Delay | Best For |
|-----------|----------|------|-------|----------|
| **Yahoo Finance** | All | Free | ~15 min | Development, Testing |
| **MetaTrader 5** | Windows | Free* | Real-time | Production (Windows) |
| **MetaAPI** | All | $49/mo | Real-time | Production (Any Platform) |

*Requires broker account (demo or live)

---

## 1. Yahoo Finance (Default)

**Recommended for**: Development and testing on macOS/Linux

### Pros
- ✅ Free
- ✅ Cross-platform (macOS, Linux, Windows)
- ✅ No account required
- ✅ Easy setup

### Cons
- ❌ ~15-20 minute delay
- ❌ Not true real-time
- ❌ Rate limits

### Setup

```bash
# Install yfinance
pip install yfinance

# No configuration needed - works out of the box
```

### Usage

```python
from src.data.realtime_feed import create_datafeed

# Create Yahoo Finance feed
feed = create_datafeed(feed_type="yahoo")

# Connect
feed.connect()

# Get latest candles
df = feed.get_latest_candles(count=200)

# Get current price
price = feed.get_current_price()

# Check for new candle
if feed.is_new_candle(df.index[-1]):
    print("New candle detected!")

# Disconnect
feed.disconnect()
```

### Environment Variables

```bash
# Optional: Set default feed type
export DATAFEED_TYPE=yahoo
```

---

## 2. MetaTrader 5 (Windows Only)

**Recommended for**: Production deployment on Windows servers

### Pros
- ✅ True real-time data
- ✅ No delays
- ✅ Can execute trades directly
- ✅ Free with broker account

### Cons
- ❌ Windows only
- ❌ Requires MT5 terminal installed
- ❌ Requires broker account

### Setup

#### Step 1: Install MT5 Terminal

1. Download MT5 from your broker (e.g., XM, FTMO, ICMarkets)
2. Install MT5 on Windows
3. Open a **demo account** (recommended for testing)

#### Step 2: Install Python Package

```bash
pip install MetaTrader5
```

**NOTE**: This only works on Windows. On macOS/Linux you'll get an import error.

#### Step 3: Configure Credentials

```bash
# Set environment variables
export MT5_LOGIN=12345678
export MT5_PASSWORD=your_password
export MT5_SERVER=YourBroker-Demo
export DATAFEED_TYPE=mt5
```

Or store in `.env` file:

```env
MT5_LOGIN=12345678
MT5_PASSWORD=your_password
MT5_SERVER=YourBroker-Demo
DATAFEED_TYPE=mt5
```

### Usage

```python
from src.data.realtime_feed import create_datafeed

# Create MT5 feed
feed = create_datafeed(
    feed_type="mt5",
    login=12345678,
    password="your_password",
    server="YourBroker-Demo"
)

# Or use environment variables
feed = create_datafeed(feed_type="mt5")

# Connect
if feed.connect():
    df = feed.get_latest_candles(count=200)
    print(f"Latest price: {df['close'].iloc[-1]}")
    feed.disconnect()
```

### Testing on Windows

```bash
# Test MT5 connection
python src/data/realtime_feed.py
```

---

## 3. MetaAPI (Cloud MT5)

**Recommended for**: Production on macOS/Linux or cloud deployment

### Pros
- ✅ Cross-platform (works everywhere)
- ✅ Cloud-based (no terminal needed)
- ✅ True real-time data
- ✅ Can execute trades
- ✅ Reliable infrastructure

### Cons
- ❌ Paid service ($49/month)
- ❌ Requires account signup
- ❌ Additional latency (cloud)

### Setup

#### Step 1: Create MetaAPI Account

1. Go to https://metaapi.cloud/
2. Sign up for an account
3. Choose a pricing plan ($49/month recommended)

#### Step 2: Add MT5 Account

1. In MetaAPI dashboard, click "Add Account"
2. Enter your MT5 broker credentials
3. Wait for account to deploy (~2 minutes)
4. Copy your **API Token** and **Account ID**

#### Step 3: Install SDK

```bash
pip install metaapi-cloud-sdk
```

#### Step 4: Configure

```bash
export METAAPI_TOKEN=your_api_token_here
export METAAPI_ACCOUNT_ID=your_account_id_here
export DATAFEED_TYPE=metaapi
```

Or in `.env`:

```env
METAAPI_TOKEN=your_api_token_here
METAAPI_ACCOUNT_ID=your_account_id_here
DATAFEED_TYPE=metaapi
```

### Usage

```python
from src.data.realtime_feed import create_datafeed

# Create MetaAPI feed
feed = create_datafeed(
    feed_type="metaapi",
    token="your_token",
    account_id="your_account_id"
)

# Or use environment variables
feed = create_datafeed(feed_type="metaapi")

# Connect (this will deploy and sync account)
if feed.connect():
    df = feed.get_latest_candles(count=200)
    feed.disconnect()
```

### MetaAPI Documentation

- Full docs: https://metaapi.cloud/docs/
- Python SDK: https://github.com/metaapi/metaapi-python-sdk
- API reference: https://metaapi.cloud/docs/client/

---

## Switching Between Feeds

### Method 1: Environment Variable

```bash
# Development (macOS/Linux)
export DATAFEED_TYPE=yahoo

# Production (Windows)
export DATAFEED_TYPE=mt5

# Production (Cloud/macOS)
export DATAFEED_TYPE=metaapi
```

Then use auto-detection:

```python
feed = create_datafeed()  # Uses DATAFEED_TYPE env variable
```

### Method 2: Explicit Selection

```python
# Development
feed = create_datafeed(feed_type="yahoo")

# Production Windows
feed = create_datafeed(feed_type="mt5")

# Production Cloud
feed = create_datafeed(feed_type="metaapi")
```

---

## Production Recommendations

### Phase 1: Development (Current)
- **Feed**: Yahoo Finance
- **Platform**: macOS/Linux
- **Purpose**: Build and test signal generation logic

### Phase 2: Paper Trading
- **Feed**: MetaAPI or MT5
- **Platform**: Any
- **Purpose**: Validate signals on demo account for 30 days

### Phase 3: Live Trading
- **Feed**: MetaAPI (recommended) or MT5
- **Platform**: Cloud server or Windows VPS
- **Purpose**: Execute real trades with real money

---

## Troubleshooting

### Yahoo Finance Issues

**Problem**: "No data returned"
- **Solution**: Yahoo Finance may be rate-limiting. Wait 5 minutes and retry.

**Problem**: "yfinance not installed"
- **Solution**: `pip install yfinance`

### MT5 Issues

**Problem**: "MetaTrader5 package not available"
- **Solution**: You're on macOS/Linux. Use Yahoo Finance or MetaAPI instead.

**Problem**: "MT5 initialize() failed"
- **Solution**: Make sure MT5 terminal is installed and running on Windows.

**Problem**: "MT5 login failed"
- **Solution**: Check login credentials. Ensure MT5 server name is correct.

### MetaAPI Issues

**Problem**: "Connection failed"
- **Solution**: Check API token and account ID. Ensure account is deployed in MetaAPI dashboard.

**Problem**: "metaapi-cloud-sdk not installed"
- **Solution**: `pip install metaapi-cloud-sdk`

---

## Code Examples

### Complete Example: Signal Generation Loop

```python
from src.data.realtime_feed import create_datafeed
from src.signals.gold_strategy import GoldStrategy
from datetime import datetime
import time

# Create data feed
feed = create_datafeed(feed_type="yahoo")  # or "mt5" or "metaapi"

if not feed.connect():
    print("❌ Failed to connect")
    exit(1)

# Create strategy
strategy = GoldStrategy()

print("🔄 Starting real-time signal generation...")

while True:
    try:
        # Fetch latest candles
        df = feed.get_latest_candles(count=200)

        # Check if new candle closed
        latest_time = df.index[-1]
        if feed.is_new_candle(latest_time):
            print(f"\n🕐 New candle at {latest_time}")

            # Generate signals
            signals = strategy.generate_signals(df)

            if signals:
                for signal in signals:
                    print(f"📊 SIGNAL: {signal['direction']} @ ${signal['entry']:.2f}")
                    print(f"   SL: ${signal['stop_loss']:.2f} | TP: ${signal['take_profit']:.2f}")
                    # TODO: Save to database, send to Telegram, etc.

        # Wait for next candle close
        feed.wait_for_candle_close(check_interval=60)

    except KeyboardInterrupt:
        print("\n⏹️  Stopping...")
        break
    except Exception as e:
        print(f"❌ Error: {e}")
        time.sleep(60)  # Wait 1 minute before retry

feed.disconnect()
print("✅ Disconnected")
```

---

## Performance Comparison

| Metric | Yahoo Finance | MT5 | MetaAPI |
|--------|---------------|-----|---------|
| Latency | ~15 minutes | <1 second | ~1-2 seconds |
| Reliability | 95%* | 99%** | 99.5% |
| Cost | Free | Free*** | $49/month |
| Setup Time | 2 minutes | 15 minutes | 10 minutes |
| Cross-platform | Yes | No | Yes |

\* Yahoo Finance can have occasional outages
\*\* Depends on MT5 terminal uptime
\*\*\* Requires broker account

---

## Next Steps

1. **Test locally** with Yahoo Finance
2. **Validate** signal logic with historical data
3. **Deploy** to Windows server with MT5 OR cloud with MetaAPI
4. **Run** paper trading for 30 days
5. **Go live** when validated

---

*Last Updated: December 20, 2025*

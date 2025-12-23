# Demo Trading Setup Guide

**Phase 2: Automated Trade Execution on MT5 Demo Account**

This guide will help you set up and run automated trading on a MetaTrader 5 demo account.

---

## 🎯 Overview

The demo trading system will:
- ✅ Generate signals in real-time (4H timeframe)
- ✅ Automatically execute trades on MT5 demo account
- ✅ Set stop loss and take profit automatically
- ✅ Track positions in real-time
- ✅ Enforce risk management rules
- ✅ Update web dashboard with live trades
- ✅ Store all trades in database

---

## 📋 Prerequisites

### Option 1: Direct MT5 (Windows Only)
- ✅ Windows operating system
- ✅ MetaTrader 5 terminal installed
- ✅ MT5 demo account created
- ✅ Python 3.8+
- ✅ `MetaTrader5` Python package

### Option 2: MetaAPI (Cross-Platform)
- ✅ Any operating system (macOS, Linux, Windows)
- ✅ MetaAPI account ($49/month or free tier)
- ✅ MT5 demo account linked to MetaAPI
- ✅ Python 3.8+
- ✅ `metaapi-cloud-sdk` Python package

---

## 🔧 Setup Instructions

### Step 1: Create MT5 Demo Account

1. **Download MT5**
   - Visit your preferred broker's website
   - Download MetaTrader 5 platform
   - Install on your computer (Windows for direct connection)

2. **Create Demo Account**
   - Open MT5 terminal
   - File → Open an Account → Demo Account
   - Fill in registration details
   - Choose account type: Standard
   - Choose leverage: 1:100 or higher
   - Initial deposit: $10,000 (recommended)
   - Save your login credentials:
     - Login: `XXXXXXX`
     - Password: `XXXXXXXX`
     - Server: `BrokerName-Demo`

### Step 2: Choose Connection Method

#### Option A: Direct MT5 Connection (Windows)

1. **Install MetaTrader5 Python Package**
   ```bash
   cd packages/engine
   pip install MetaTrader5
   ```

2. **Set Environment Variables**
   ```bash
   # Create .env file in packages/engine/
   export MT5_CONNECTION_TYPE=direct
   export MT5_LOGIN=12345678        # Your demo account login
   export MT5_PASSWORD=YourPassword  # Your demo account password
   export MT5_SERVER=BrokerName-Demo # Your broker's demo server
   export MT5_SYMBOL=XAUUSD         # Trading symbol
   ```

3. **Ensure MT5 Terminal is Running**
   - Keep MT5 terminal open while running the service
   - Log in to your demo account
   - The Python script will connect to the running terminal

#### Option B: MetaAPI Cloud Connection (Cross-Platform)

1. **Create MetaAPI Account**
   - Visit https://metaapi.cloud
   - Sign up for an account
   - Get free trial or subscribe ($49/month)

2. **Link Your MT5 Account**
   - Dashboard → Add Account
   - Enter your MT5 demo account credentials
   - Wait for account deployment (~5 minutes)
   - Copy your Account ID and API Token

3. **Install MetaAPI SDK**
   ```bash
   cd packages/engine
   pip install metaapi-cloud-sdk
   ```

4. **Set Environment Variables**
   ```bash
   # Create .env file in packages/engine/
   export MT5_CONNECTION_TYPE=metaapi
   export METAAPI_TOKEN=your_api_token_here
   export METAAPI_ACCOUNT_ID=your_account_id_here
   export MT5_SYMBOL=XAUUSD
   ```

### Step 3: Configure Risk Management

Edit your `.env` file to set risk parameters:

```bash
# Risk Management
export MAX_RISK_PER_TRADE=0.02      # 2% risk per trade
export MAX_POSITIONS=3              # Maximum 3 concurrent positions
export MAX_DAILY_LOSS=0.05         # Stop trading if 5% daily loss
export POSITION_SIZE_MODE=risk_based # or 'fixed_lots'
export FIXED_LOT_SIZE=0.01         # Used if position_size_mode=fixed_lots

# Execution Settings
export MAX_SLIPPAGE_PIPS=5         # Maximum acceptable slippage
export MAGIC_NUMBER=123456         # Unique identifier for your EA
```

### Step 4: Configure Data Feed

The service needs market data to generate signals:

```bash
# Data Feed (choose one)
export DATAFEED_TYPE=yahoo         # Free, 15-min delay (for testing)
# OR
export DATAFEED_TYPE=mt5           # Real-time from MT5 (Windows only)
# OR
export DATAFEED_TYPE=metaapi       # Real-time from MetaAPI cloud
```

**Recommendation:**
- **Testing/Development:** Use `yahoo` (free, works on all platforms)
- **Live Demo Trading:** Use `mt5` (Windows) or `metaapi` (any platform)

### Step 5: Complete Environment Configuration

Example `.env` file:

```bash
# MT5 Connection (choose direct OR metaapi)
MT5_CONNECTION_TYPE=direct
MT5_LOGIN=12345678
MT5_PASSWORD=YourPassword
MT5_SERVER=BrokerName-Demo
MT5_SYMBOL=XAUUSD

# OR for MetaAPI:
# MT5_CONNECTION_TYPE=metaapi
# METAAPI_TOKEN=your_token
# METAAPI_ACCOUNT_ID=your_account_id
# MT5_SYMBOL=XAUUSD

# Risk Management
MAX_RISK_PER_TRADE=0.02
MAX_POSITIONS=3
MAX_DAILY_LOSS=0.05
POSITION_SIZE_MODE=risk_based

# Data Feed
DATAFEED_TYPE=yahoo
TIMEFRAME=4H

# Database
DATABASE_URL=sqlite:///signals.db
```

---

## 🚀 Running the Service

### Test Configuration

First, verify your configuration:

```bash
cd packages/engine
python run_demo_trading.py --config
```

This will display your settings without connecting.

### Dry Run Mode (Testing)

Test the system without executing real trades:

```bash
python run_demo_trading.py --dry-run
```

In dry run mode:
- ✅ Signals are generated
- ✅ Risk checks are performed
- ✅ Position sizes are calculated
- ✅ Signals are logged
- ❌ NO actual trades are executed on MT5

### Live Demo Trading

Once you've tested with dry run, start live demo trading:

```bash
python run_demo_trading.py
```

The service will:
1. Connect to MT5
2. Start monitoring market data (4H candles)
3. Generate signals when conditions are met
4. Execute trades automatically
5. Monitor open positions
6. Close positions at SL or TP

### Monitor the Service

Watch the logs in real-time:

```bash
# In another terminal
tail -f demo_trading.log
```

Or check signal logs:

```bash
tail -f signals.log
```

---

## 📊 Understanding the Output

### When a Signal is Generated:

```
======================================================================
📊 TRADING SIGNAL RECEIVED (#1)
======================================================================
LONG XAUUSD (4H)
Entry: $2,127.80
Stop Loss: $2,055.74
Take Profit: $2,271.92
R:R Ratio: 1:2.00
Confidence: 70.0%
======================================================================

✅ RISK CHECK PASSED
  Current positions: 0/3
  Proposed risk: $200.00 (2.00%)
  Daily P&L: $0.00
  Account balance: $10,000.00

🚀 EXECUTING TRADE
======================================================================
  Ticket: 123456789
  Entry Price: $2,127.85
  Lot Size: 0.10
  Risk: $200.00
======================================================================
```

### Risk Management in Action:

```
❌ RISK CHECK FAILED: Maximum positions reached (3)
```

```
❌ RISK CHECK FAILED: Daily loss limit reached (5.02% >= 5.00%)
```

---

## 🛡️ Safety Features

### Automatic Protections:

1. **Position Limits**
   - Maximum 3 concurrent positions (configurable)
   - Prevents over-trading

2. **Daily Loss Limit**
   - Stops trading if daily loss reaches 5% (configurable)
   - Protects account from catastrophic losses

3. **Risk Per Trade**
   - Each trade risks only 2% of account (configurable)
   - Ensures sustainable risk management

4. **Account Balance Check**
   - Stops trading if balance drops below 50% of initial
   - Emergency circuit breaker

5. **Position Validation**
   - Validates lot size, margin, and slippage
   - Rejects trades that don't meet criteria

### Emergency Stop:

To stop the service immediately:
- Press `Ctrl+C` in the terminal
- Service will gracefully shut down
- All positions remain open on MT5 (they have SL/TP)

To close all positions manually:
- Open MT5 terminal
- Right-click on positions → Close

---

## 📈 Monitoring Your Trades

### 1. Web Dashboard

Visit http://localhost:3000 to see:
- Real-time signal status
- Open positions
- Performance metrics
- Trade history

### 2. Database

Query the SQLite database:

```bash
sqlite3 signals.db

# View all signals
SELECT * FROM signals ORDER BY timestamp DESC LIMIT 10;

# View open positions
SELECT * FROM signals WHERE status = 'active';

# View performance
SELECT COUNT(*), AVG(pnl), SUM(pnl) FROM signals WHERE status LIKE 'closed%';
```

### 3. MT5 Terminal

- Open MT5 → Toolbox → Trade
- View all open positions and their P&L
- Check trade history in Account History tab

---

## 🔍 Troubleshooting

### Connection Issues

**Problem:** `Failed to connect to MT5`

**Solutions:**
- Ensure MT5 terminal is running (for direct connection)
- Check login credentials in `.env` file
- Verify server name is correct
- Try logging in manually to MT5 first
- For MetaAPI: Check account deployment status

### Position Not Executing

**Problem:** Signals generated but no trades executed

**Check:**
1. Risk limits reached?
   - Check logs for "RISK CHECK FAILED"
   - View `risk_manager.get_risk_summary()`

2. Insufficient margin?
   - Check account free margin in MT5
   - Reduce `MAX_RISK_PER_TRADE` or use smaller lot sizes

3. Symbol not available?
   - Ensure XAUUSD is available on your broker
   - Check symbol name (might be GOLD, XAUUSD, or XAU/USD)

### Data Feed Issues

**Problem:** No candles being processed

**Solutions:**
- For Yahoo: Check internet connection
- For MT5: Ensure terminal is connected to broker
- For MetaAPI: Check API quota and connection status
- Verify symbol name matches broker's symbol

---

## 📝 Best Practices

### For Testing (First Week):

1. **Start with Dry Run**
   ```bash
   python run_demo_trading.py --dry-run
   ```
   Run for 24 hours to verify signals are generated

2. **Then Small Position Sizes**
   ```bash
   # In .env
   POSITION_SIZE_MODE=fixed_lots
   FIXED_LOT_SIZE=0.01  # Minimum lot size
   ```

3. **Monitor Closely**
   - Check logs every few hours
   - Verify trades match signals
   - Compare execution price vs signal price (slippage)

### For 30-Day Validation:

1. **Use Risk-Based Sizing**
   ```bash
   POSITION_SIZE_MODE=risk_based
   MAX_RISK_PER_TRADE=0.02  # 2%
   ```

2. **Let It Run Continuously**
   - Use a VPS or always-on computer
   - Set up auto-restart on crash (systemd, supervisor, etc.)

3. **Daily Review**
   - Check daily P&L
   - Review closed trades
   - Analyze execution quality vs backtest

4. **Weekly Analysis**
   - Compare live results to backtest
   - Calculate slippage average
   - Review risk management effectiveness

---

## 🎯 Success Metrics (30-Day Period)

Track these metrics:

- ✅ **Execution Rate:** % of signals successfully executed (target: >95%)
- ✅ **Win Rate:** Compare to backtest (target: ±5% of backtest)
- ✅ **Average R:R:** Should be ~2:1 as designed
- ✅ **Slippage:** Average difference between signal and execution (target: <2 pips)
- ✅ **System Uptime:** % of time service was running (target: >99%)
- ✅ **Risk Limit Triggers:** How often daily loss limit hit (target: <10%)

---

## 🎓 Next Steps After 30 Days

If demo trading is successful:

1. ✅ Analyze complete performance report
2. ✅ Compare demo results to backtest
3. ✅ Calculate actual Sharpe ratio
4. ✅ Review slippage and execution quality
5. ⬜ **Phase 3:** Consider live trading with minimum account size
6. ⬜ Add Telegram notifications
7. ⬜ Implement advanced analytics dashboard

---

## ⚠️ Important Disclaimers

- 🔴 **This is DEMO trading only** - No real money at risk
- 🔴 **Demo results may differ from live** - Slippage and execution can vary
- 🔴 **Always validate for 30+ days** before considering live trading
- 🔴 **Past performance doesn't guarantee future results**
- 🔴 **Never risk more than you can afford to lose**

---

*Last Updated: December 22, 2025*
*Phase 2 - Demo Trading Integration*

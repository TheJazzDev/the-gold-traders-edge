# Railway Auto-Trading Setup Guide

## Overview
Your MetaAPI integration is now fully implemented but **not yet enabled** in Railway. This guide shows you how to enable auto-trading on your demo account.

## What Was Fixed

### 1. NumPy Type Conversion Issue ✅
**Problem:** Signals were failing to save to database due to NumPy float64 types
**Solution:** Added automatic conversion to Python floats in DatabaseSubscriber
**Status:** Fixed and deployed

### 2. Duplicate Signal Detection Issue ✅
**Problem:** Historical candles were blocking all real-time signals
**Solution:** Only check duplicates for recent signals (< 1 hour old)
**Status:** Fixed and deployed

### 3. MT5Subscriber Not Enabled ❌
**Problem:** Auto-trading code exists but wasn't being used
**Solution:** Added `--enable-trading` flag and `ENABLE_AUTO_TRADING` env var
**Status:** Code ready, waiting for Railway configuration

---

## How to Enable Auto-Trading in Railway

### Step 1: Get Your MetaAPI Credentials

You mentioned you bought MetaAPI. You need:

1. **METAAPI_TOKEN** - Your MetaAPI API token
2. **METAAPI_ACCOUNT_ID** - Your MetaAPI demo account ID

Get these from your MetaAPI dashboard:
- Go to https://app.metaapi.cloud/
- Navigate to your account settings
- Copy the API Token
- Copy your Demo Account ID

### Step 2: Add Environment Variables to Railway

1. Go to your Railway project dashboard
2. Click on your service
3. Go to the **Variables** tab
4. Add these new environment variables:

```
ENABLE_AUTO_TRADING=true
METAAPI_TOKEN=<your_metaapi_token_here>
METAAPI_ACCOUNT_ID=<your_metaapi_account_id_here>
```

### Step 3: Deploy

Once you add these environment variables, Railway will automatically restart your service with auto-trading enabled.

---

## How It Works

### Signals-Only Mode (Current State)
```
Signal Generated → Database → Done
                → Logger
                → Console
```

### Auto-Trading Mode (After Configuration)
```
Signal Generated → Database
                → Logger
                → Console
                → MT5Subscriber → Risk Check → Execute Trade on Demo Account
```

---

## What Happens When Auto-Trading is Enabled

When a signal is generated:

1. **Signal Validation** - Strategy generates signal, validator checks R:R ratio
2. **Database Save** - Signal saved to PostgreSQL with status="PENDING"
3. **MT5 Subscriber Receives Signal** - Auto-trading activated
4. **Risk Management Check**:
   - Account balance check
   - Position size calculation
   - Max risk per trade validation (default: 1%)
   - Max positions check (default: 5)
   - Daily loss limit check (default: 3%)
5. **Trade Execution** (if all checks pass):
   - Market order placed on MetaAPI demo account
   - Stop Loss and Take Profit set
   - Database updated with `mt5_ticket`, `actual_entry`, status="EXECUTED"
6. **Position Monitoring** - Trade tracked until TP/SL hit

---

## Safety Features

### Risk Management
- **Max Risk Per Trade:** 1% of account balance (configurable)
- **Max Positions:** 5 simultaneous trades (configurable)
- **Max Daily Loss:** 3% of account balance (configurable)
- **Position Sizing:** Automatically calculated based on stop loss distance

### Fail-Safes
- Connection loss handling
- Invalid signal rejection
- Account balance verification before each trade
- Detailed error logging

---

## Monitoring Your Trades

### Via API
```bash
# View all signals
curl https://the-gold-traders-edge-production.up.railway.app/v1/signals/history?limit=50

# Filter by status
curl https://the-gold-traders-edge-production.up.railway.app/v1/signals/history?status=EXECUTED
```

### Via Database
```python
# Run this from Railway's terminal or locally with public URL
python check_signals.py
```

### Via Logs
Railway logs will show:
```
🎯 Signal triggered: Momentum Equilibrium
✅ Signal validated: LONG @ $2650.00
📢 Publishing signal to 4 subscriber(s)
🚀 EXECUTING TRADE
✅ TRADE EXECUTED SUCCESSFULLY
   Ticket: 123456789
   Entry Price: 2650.15
   Lot Size: 0.01
   Risk: $100.00
```

---

## Testing Before Going Live

### Recommended Testing Flow

1. **Enable Auto-Trading on Demo** (what this guide does)
   - Set `ENABLE_AUTO_TRADING=true` in Railway
   - Monitor for 1-2 weeks
   - Verify trades match signals
   - Check risk management is working

2. **Analyze Demo Results**
   - Win rate vs. backtest expectations
   - Slippage analysis
   - Risk metrics validation
   - Strategy performance by timeframe

3. **Go Live** (future step, when ready)
   - Switch `METAAPI_ACCOUNT_ID` to live account
   - Start with minimum lot sizes
   - Gradually increase position sizing

---

## Configuration Options

You can customize the MT5 behavior with these environment variables:

```bash
# Connection
METAAPI_TOKEN=your_token_here
METAAPI_ACCOUNT_ID=your_account_id_here

# Risk Management
MAX_RISK_PER_TRADE=0.01          # 1% per trade
MAX_POSITIONS=5                   # Max 5 concurrent trades
MAX_DAILY_LOSS=0.03              # Max 3% daily loss

# Trading Symbol
MT5_SYMBOL=XAUUSD                # Gold (default)
```

---

## Troubleshooting

### "MT5 configuration error" in logs
**Cause:** Missing or invalid MetaAPI credentials
**Fix:** Verify METAAPI_TOKEN and METAAPI_ACCOUNT_ID in Railway variables

### "Failed to connect to MT5"
**Cause:** MetaAPI connection issue or invalid account ID
**Fix:** Check MetaAPI dashboard, ensure account is active and deployed

### "Risk check failed" in logs
**Cause:** Risk management prevented trade (good thing!)
**Fix:** Review account balance, existing positions, and risk limits

### Signals saved but not executed
**Cause:** Auto-trading not enabled
**Fix:** Verify `ENABLE_AUTO_TRADING=true` is set in Railway

---

## Current Status Summary

✅ **Database saving fixed** - NumPy type conversion complete
✅ **Duplicate detection fixed** - Historical signals no longer block new ones
✅ **MT5Subscriber integration complete** - Code ready for auto-trading
❌ **MetaAPI credentials not configured** - Need to add to Railway
❌ **Auto-trading not enabled** - Need to set ENABLE_AUTO_TRADING=true

---

## Next Steps

1. ✅ Push NumPy fix to Railway (done)
2. ✅ Push MT5Subscriber integration to Railway (done)
3. ⏳ **YOU: Add MetaAPI credentials to Railway** (waiting for your MetaAPI account details)
4. ⏳ **YOU: Set ENABLE_AUTO_TRADING=true in Railway**
5. ⏳ Monitor logs and database for executed trades
6. ⏳ Analyze demo performance for 1-2 weeks
7. ⏳ Make decision to go live or adjust strategies

---

## Questions?

- Check Railway logs for detailed execution info
- Review `/v1/signals/history` API endpoint for signal/trade history
- All trade executions logged with ticket numbers and entry prices

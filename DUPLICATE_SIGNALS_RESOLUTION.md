# Duplicate Signals Issue - Resolution 🔧

## 📊 Issue Summary

You reported seeing duplicate signals in the database and the frontend not displaying data.

### Database Analysis

```
Signal Timestamp: 2025-12-24 14:30:00 (Dec 24)
Created Times: 2025-12-25 19:31:34 - 19:40:58 (Dec 25)
Signal Age: ~29 hours old when saved
Duplicates: 10 records (6 timeframes × 2 deployment cycles)
```

## 🔍 Root Cause

1. **Fix Timing**: The database-backed deduplicator fix was deployed at **20:48 on Dec 25**
2. **Duplicates Created**: The duplicate signals were saved at **19:31 and 19:40** - **BEFORE the fix was deployed**
3. **Old Signal**: The signal from Dec 24 was 29+ hours old and should have been rejected

## ✅ What's Fixed

### 1. Database-Backed Deduplicator (Deployed ✅)

**Commit**: `6661f88` - "Fix: CORS, deduplication, Telegram bot, database schema"
**Deployed**: 2025-12-25 20:48:34

**Files Modified**:
- `packages/engine/src/signals/signal_deduplicator.py` - Loads recent signals from DB on startup
- `packages/engine/src/signals/subscribers/dedup_subscriber.py` - Passes database_url
- `packages/engine/run_multi_timeframe_service.py` - Provides database_url to deduplicator

**What It Does**:
- On service startup, loads all signals from last 4 hours from database
- Pre-populates in-memory cache with existing signals
- Prevents duplicates even after Railway deployments/restarts
- Falls back gracefully if database unavailable

### 2. Old Signal Rejection (Should Be Active)

**File**: `packages/engine/src/signals/realtime_generator.py:186-197`

**What It Does**:
- Rejects signals older than 1 hour
- Prevents historical/old signals from being saved/sent
- **Note**: The Dec 24 signal should have been rejected by this

## ❓ Remaining Questions

### Why Was the Old Signal Not Rejected?

The signal from Dec 24 (14:30:00) was saved on Dec 25 (19:31-19:40), meaning it was ~29 hours old.
This should have been rejected by the 1-hour age check.

**Possible causes**:
1. **Timezone issue** - Signal timestamp vs current time timezone mismatch
2. **Fix not deployed yet** - The age check fix might not have been in the deployment
3. **Data feed issue** - Yahoo Finance returning old/cached data

### Why Is Frontend Not Showing Data?

**Need to check**:
1. `NEXT_PUBLIC_API_URL` environment variable in frontend
2. API endpoint responding correctly (`/v1/signals/history`)
3. CORS configuration
4. Browser console for errors

## 🛠️ Action Plan

### 1. Clean Up Duplicate Signals

Run the cleanup script:

```bash
cd packages/engine
python3 cleanup_duplicates.py
```

This will:
- Find all duplicate signals (same timestamp, symbol, strategy, levels)
- Keep only the first occurrence of each
- Prompt for confirmation before deleting

### 2. Verify Frontend API Connection

Check environment variables:

```bash
# Frontend should have:
NEXT_PUBLIC_API_URL=https://your-railway-api-url.railway.app
```

Test API endpoint:

```bash
curl https://your-railway-api-url.railway.app/v1/signals/history?limit=10
```

### 3. Monitor Next Signal

Wait for the next real signal to verify:
- ✅ Only ONE signal saved (not duplicated across timeframes)
- ✅ Signal appears in frontend
- ✅ Telegram notification sent once

### 4. Check Railway Logs

Look for these messages on next deployment:

```
✅ SignalDeduplicator initialized (window: 4h, db-backed: True)
✅ Loaded X recent signal(s) from database (prevents duplicate notifications on restart)
✅ Shared deduplication subscriber created (prevents duplicate signals across all timeframes and restarts)
```

If you see:
```
⚠️  No database URL provided - deduplicator will NOT persist across restarts!
```

Then the `DATABASE_URL` environment variable is not set in Railway.

## 📝 Expected Behavior After Fix

### On Deployment/Restart:

```
Service Starts
    ↓
Deduplicator loads recent signals from DB (last 4 hours)
    ↓
In-memory cache: [Signal from Dec 29 @2650.50, Signal from Dec 28 @2655.00, ...]
    ↓
1h worker: Detects setup @ $2650.50
    ↓
Deduplicator: "Already seen this signal!" → BLOCKED ✅
    ↓
4h worker: Detects same setup @ $2650.50
    ↓
Deduplicator: "Already seen this signal!" → BLOCKED ✅
    ↓
Result: NO duplicate Telegram messages ✅
```

### On New Signal:

```
Market forms new setup
    ↓
1h candle closes with new Order Block
    ↓
Signal validator: Age = 0.1 hours → VALID ✅
    ↓
Deduplicator: Not in cache → UNIQUE ✅
    ↓
Save to DB ✅
Send to Telegram ✅
    ↓
4h worker sees same setup 10 mins later
    ↓
Deduplicator: Already in cache! → BLOCKED ✅
    ↓
Result: ONE signal saved, ONE Telegram message ✅
```

## 🔬 Debug Commands

### Check Database Signals:

```sql
-- Count signals by timestamp
SELECT timestamp, COUNT(*) as count
FROM signals
GROUP BY timestamp
HAVING COUNT(*) > 1
ORDER BY timestamp DESC;

-- View recent signals
SELECT id, timestamp, timeframe, strategy_name, direction, entry_price, created_at
FROM signals
ORDER BY created_at DESC
LIMIT 20;
```

### Test Deduplicator:

```python
from signals.signal_deduplicator import get_deduplicator

dedup = get_deduplicator(dedup_window_hours=4, database_url='postgresql://...')
stats = dedup.get_stats()
print(f"Recent signals in cache: {stats['recent_signals_count']}")
print(f"Oldest signal: {stats['oldest_signal']}")
print(f"Newest signal: {stats['newest_signal']}")
```

### Test API Endpoint:

```bash
# Get signals
curl https://your-api.railway.app/v1/signals/history | jq

# Get market status
curl https://your-api.railway.app/v1/market/status | jq

# Health check
curl https://your-api.railway.app/health
```

## 📋 Checklist

- [x] Database-backed deduplicator deployed
- [x] Old signal rejection logic in place
- [ ] Clean up duplicate signals from database
- [ ] Verify frontend API connection
- [ ] Test with next real signal
- [ ] Confirm no duplicates in Telegram
- [ ] Confirm signals appear in frontend

## 📞 Next Steps

1. **Run cleanup script** to remove the 10 duplicate signals
2. **Check frontend environment variables** for API_URL
3. **Wait for next signal** to verify the fix is working
4. **Monitor Railway logs** for deduplicator initialization messages

If you still see duplicates after the next signal, we need to investigate:
- Railway environment variables (DATABASE_URL)
- Timezone handling in age calculation
- Data feed timestamp accuracy

---

**Status**: Fix deployed ✅ | Cleanup pending ⏳ | Frontend investigation needed 🔍

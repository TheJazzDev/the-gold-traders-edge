# Startup Signal Replay Bug - Fixed ✅

## Problem

Every time you deploy or restart the service on Railway, you receive **duplicate signals** in Telegram:

```
🟢 NEW LONG SIGNAL - 1h timeframe
Time: 2025-12-24 09:30 UTC

🟢 NEW LONG SIGNAL - 4h timeframe  ← DUPLICATE!
Time: 2025-12-24 09:30 UTC

🟢 NEW LONG SIGNAL - 1d timeframe  ← DUPLICATE!
Time: 2025-12-24 09:30 UTC
```

This happens **3-6 times** (once per timeframe) because:
1. Each timeframe processes the last candle on startup
2. The deduplicator's in-memory cache is wiped on restart
3. All signals appear "unique" to the empty deduplicator

## Root Cause

When the service restarts on Railway deployment:

**Issue #1: In-Memory Deduplicator Lost on Restart** ❌

1. **Service restarts** (Railway deployment)
2. **Deduplicator's in-memory cache is wiped** (RAM cleared)
3. **All 3-6 timeframe workers start simultaneously**
4. **Each fetches the latest candle** (same candle across all timeframes)
5. **Each detects the same setup** (e.g., Order Block on 1h, 4h, 1d)
6. **Deduplicator's cache is empty** - all signals appear "unique"
7. **All 3-6 duplicate signals sent to Telegram** ❌

**Issue #2: Old Signals on Startup** ❌ (Already Fixed)

The signal validator was checking if signals are recent (within 1 hour) but **still returning them** even if they were old.

This was already fixed in a previous update (see below).

## The Fix

### Fix #1: Database-Backed Deduplicator ✅ (NEW)

**Files:**
- `packages/engine/src/signals/signal_deduplicator.py`
- `packages/engine/src/signals/subscribers/dedup_subscriber.py`
- `packages/engine/run_multi_timeframe_service.py`

**Changed:** Deduplicator now **loads recent signals from database on startup**:

```python
# ✅ NEW CODE - Database-backed deduplication
class SignalDeduplicator:
    def __init__(self, dedup_window_hours: int = 4, database_url: Optional[str] = None):
        self.recent_signals: Dict[str, SignalFingerprint] = {}
        self.database_url = database_url or os.getenv('DATABASE_URL')

        # Load recent signals from database on startup
        self._load_recent_signals_from_db()  # ← PREVENTS DUPLICATES ON RESTART!

    def _load_recent_signals_from_db(self):
        """Load recent signals from database to prevent duplicate notifications on restart."""
        # Fetch signals from last 4 hours from database
        # Add to in-memory cache
        # Now duplicates will be detected even after restart! ✅
```

**Result:**
- On startup, deduplicator loads recent signals from database
- In-memory cache is pre-populated with signals from last 4 hours
- Duplicate signals from multiple timeframes are detected and suppressed
- NO duplicate Telegram notifications on restart! ✅

### Fix #2: Reject Old Signals ✅ (Previous Fix)

**File:** `packages/engine/src/signals/realtime_generator.py`

**Changed:** Signal validator **rejects old signals** completely:

```python
# ✅ EXISTING CODE - Rejects old signals
signal_age_hours = (pd.Timestamp.now(tz='UTC') - pd.Timestamp(signal.time)).total_seconds() / 3600
is_recent_signal = signal_age_hours < 1.0  # Signal must be from last hour

# REJECT old signals completely
if not is_recent_signal:
    logger.debug(
        f"Skipping old signal: {direction_str} @ ${signal.entry_price:.2f} "
        f"(age: {signal_age_hours:.1f}h, max: 1h)"
    )
    return None  # ← REJECT! No validation, no notification
```

### What Changed

**Before (Duplicates on Restart):**
1. Service restarts
2. Deduplicator's in-memory cache is EMPTY (RAM wiped)
3. 1h worker detects Order Block → Appears "unique" → Sent to Telegram ❌
4. 4h worker detects same Order Block → Appears "unique" (cache still empty) → Sent to Telegram ❌
5. 1d worker detects same Order Block → Appears "unique" (cache still empty) → Sent to Telegram ❌
6. **Result: 3 duplicate Telegram notifications** ❌

**After (Database-Backed Deduplication):**
1. Service restarts
2. Deduplicator loads recent signals from database (last 4 hours) ✅
3. In-memory cache is PRE-POPULATED with existing signals
4. 1h worker detects Order Block → Not in cache → Sent to Telegram ✅
5. 4h worker detects same Order Block → FOUND IN CACHE → Suppressed ✅
6. 1d worker detects same Order Block → FOUND IN CACHE → Suppressed ✅
7. **Result: 1 Telegram notification (duplicates suppressed)** ✅

## How It Works

### On Startup (First Run)

```
Service Starts
    └─ 1h worker fetches latest candle (Dec 24, 9:30am)
         └─ Strategy detects Order Block
              └─ Validator checks age: 26.9 hours old
                   └─ REJECTS signal (too old) ✅
                        └─ Nothing sent to Telegram ✅

    └─ 4h worker fetches latest candle (Dec 24, 9:30am)
         └─ Strategy detects Order Block
              └─ Validator checks age: 26.9 hours old
                   └─ REJECTS signal (too old) ✅
                        └─ Nothing sent to Telegram ✅
```

### During Normal Operation (New Candle Closes)

```
New 1h Candle Closes (just now)
    └─ Strategy detects new Order Block
         └─ Validator checks age: 0.1 hours old
              └─ ACCEPTS signal (recent!) ✅
                   └─ Sends to Telegram ✅
                   └─ Saves to database ✅
```

## Signal Age Threshold

**Current setting:** Signals must be **within 1 hour** of current time

```python
is_recent_signal = signal_age_hours < 1.0  # 1 hour threshold
```

This ensures:
- ✅ New signals (just generated) → Accepted
- ❌ Old signals (from startup candle processing) → Rejected
- ❌ Historical signals (from backtesting) → Rejected

### Why 1 Hour?

- Candle close to notification should be near-instant
- Even 4H candle closes should trigger within minutes
- 1 hour gives generous buffer for:
  - Network delays
  - Processing time
  - Server clock drift

### Adjust If Needed

If you need a different threshold:

```python
# More strict (15 minutes)
is_recent_signal = signal_age_hours < 0.25

# More lenient (2 hours)
is_recent_signal = signal_age_hours < 2.0
```

## Expected Behavior

### Scenario 1: Fresh Deployment (Startup)

```
Railway deploys new version
    ↓
Service starts at 10:00 UTC
    ↓
Fetches latest candles:
  - 1h candle closed at 09:00 UTC (1 hour old)
  - 4h candle closed at 08:00 UTC (2 hours old)
  - 1d candle closed at 00:00 UTC (10 hours old)
    ↓
Strategy detects signals on all candles
    ↓
Validator checks ages:
  - 1h: 1.0h old → REJECTED (barely too old)
  - 4h: 2.0h old → REJECTED
  - 1d: 10h old → REJECTED
    ↓
Result: NO old signals sent to Telegram ✅
```

### Scenario 2: Normal Operation (New Candle)

```
Service running normally
    ↓
New 1h candle closes at 11:00 UTC
    ↓
Data feed detects new candle
    ↓
Strategy analyzes (takes ~1 second)
    ↓
Signal generated at 11:00:01 UTC
    ↓
Validator checks age: 0.0003h (1 second) old
    ↓
ACCEPTS signal (very recent!) ✅
    ↓
Sends to Telegram ✅
Saves to database ✅
```

## Testing

### Test 1: Deploy and Check for Old Signals

```bash
# Deploy
git push

# Watch Railway logs
railway logs --tail | grep -E "(Skipping old|Signal validated)"

# Expected on startup:
# [DEBUG] Skipping old signal: LONG @ $4505.60 (age: 26.9h, max: 1h)
# [DEBUG] Skipping old signal: LONG @ $4505.60 (age: 26.9h, max: 1h)
# [DEBUG] Skipping old signal: LONG @ $4505.60 (age: 26.9h, max: 1h)

# NO "Signal validated" messages on startup ✅
```

### Test 2: Wait for New Candle

```bash
# Wait for next candle close (within 1 hour)
# New signal should be accepted and sent

# Expected:
# [INFO] ✅ Signal validated: LONG @ $2650.50 (age: 0.0h)
# [INFO] 📱 Signal sent to Telegram
```

### Test 3: Check Telegram

After deployment:
- ❌ Should NOT receive any old signals
- ✅ Should only receive NEW signals (when candles close)

## Deployment

### Push Changes

```bash
git add packages/engine/src/signals/realtime_generator.py
git commit -m "Fix: Reject old signals on startup to prevent Telegram spam"
git push
```

### Railway Auto-Deploys

Railway will deploy the fix automatically.

### Verify

1. **Watch Railway logs** during deployment
2. **Check for "Skipping old signal"** messages (good!)
3. **Check Telegram** - should NOT receive old signals
4. **Wait for next candle** - should receive NEW signal

## Logs

### Before Fix (Startup)

```
[INFO] 🎯 Signal triggered: Order Block Retest
[INFO] ✅ Signal validated: LONG @ $4505.60 (age: 26.9h)  ← Old signal!
[INFO] 📱 Signal sent to Telegram  ← Sent to Telegram ❌
```

### After Fix (Startup)

```
[INFO] 🎯 Signal triggered: Order Block Retest
[DEBUG] Skipping old signal: LONG @ $4505.60 (age: 26.9h, max: 1h)  ← Rejected!
# Nothing sent to Telegram ✅
```

### After Fix (New Candle)

```
[INFO] 🎯 Signal triggered: Order Block Retest
[INFO] ✅ Signal validated: LONG @ $2650.50 (age: 0.0h)  ← New signal!
[INFO] 📱 Signal sent to Telegram  ← Sent to Telegram ✅
```

## Summary

**Problem:** Service sends duplicate signals (3-6x) on every Railway deployment ❌

**Root Causes:**
1. Deduplicator's in-memory cache wiped on restart ❌
2. All timeframes process same candle simultaneously ❌
3. All signals appear "unique" to empty deduplicator ❌

**Fixes:**
1. Database-backed deduplicator (loads recent signals on startup) ✅
2. Signal validator rejects signals older than 1 hour ✅

**Result:**
- No duplicate signals on restart ✅
- Only unique signals sent to Telegram ✅
- Deduplication persists across deployments ✅
- Clean deployment experience ✅

## Related Issues

This fix also prevents:
- Duplicate notifications when service restarts ✅
- Duplicate signals across multiple timeframes ✅
- Historical backtest signals from being sent ✅
- Old signals from being saved to database on startup ✅

## Expected Logs on Startup

When the service starts with the fix, you should see:

```
[INFO] ✅ SignalDeduplicator initialized (window: 4h, db-backed: True)
[INFO] ✅ Loaded 3 recent signal(s) from database (prevents duplicate notifications on restart)
[INFO] ✅ Shared deduplication subscriber created (prevents duplicate signals across all timeframes and restarts)
```

If a duplicate signal is detected:

```
[DEBUG] Skipping old signal: LONG @ $4505.60 (age: 26.9h, max: 1h)
```

OR

```
[INFO] 🚫 Duplicate signal detected:
   Original: Order Block Retest LONG @ $4505.60 from 1h at 2025-12-24 09:30
   Suppressed: Same signal from 4h
[INFO] 🚫 Suppressing duplicate signal: Order Block Retest LONG @ $4505.60 from 4h
```

## Future Improvements

If needed, we could add:

1. **Configurable age threshold** via environment variable:
   ```python
   max_age_hours = float(os.getenv('MAX_SIGNAL_AGE_HOURS', '1.0'))
   is_recent_signal = signal_age_hours < max_age_hours
   ```

2. **Startup flag** to skip signal processing on first run:
   ```python
   if self.is_first_run:
       logger.info("Skipping first candle (startup)")
       self.is_first_run = False
       return None
   ```

3. **Database persistence** of last processed candle time:
   ```python
   last_processed = db.get_last_candle_time(timeframe)
   if signal.time <= last_processed:
       return None  # Already processed
   ```

For now, the 1-hour age check is simple and effective! ✅

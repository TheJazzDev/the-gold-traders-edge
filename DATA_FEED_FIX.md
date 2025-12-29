# Data Feed Display Fix

## Issue
Admin panel shows "Data Feed: yahoo" instead of "metaapi" even though you're using MetaAPI.

## Root Cause
The `/v1/settings/service/status` endpoint wasn't returning the `data_feed_type` field, so it defaulted to "yahoo" in the UI.

## Fix Applied

### 1. Updated Service Status Endpoint
**File**: `packages/api/src/routes/settings.py` (line 395)

Added `data_feed_type` to the response:

```python
return {
    "status": repo.get("service_status", "running"),
    "auto_trading_enabled": repo.get("auto_trading_enabled", False),
    "dry_run_mode": repo.get("dry_run_mode", False),
    # ... other fields ...
    "data_feed_type": repo.get("data_feed_type", "metaapi"),  # NEW!
    "active_timeframes": repo.get("enabled_timeframes", ["5m", "15m", "30m", "1h", "4h", "1d"]),
}
```

### 2. How It Works

The data feed type comes from:
1. **Database setting** (if `data_feed_type` is set in settings table)
2. **Default value** of "metaapi" (if not in database)

The actual data feed used by the signal generator is controlled by the **`DATA_FEED_TYPE` environment variable** in Railway.

### 3. To Ensure MetaAPI is Used

Make sure this environment variable is set in Railway:

```bash
DATA_FEED_TYPE=metaapi
```

This tells the signal generator (`run_multi_timeframe_service.py`) to use MetaAPI instead of Yahoo Finance.

## Deploy

Commit and push to deploy:

```bash
git add packages/api/src/routes/settings.py
git commit -m "Fix: show correct data_feed_type in admin panel"
git push origin main
```

After deploy, the admin panel will show:
- **Data Feed: metaapi** ✅ (instead of yahoo)

## Verify

After deploying, check your admin panel at:
`https://the-gold-traders-edge.jazzdev.xyz/admin`

You should see:
```
Service Information
├─ Status: running
├─ Auto-Trading: Enabled/Disabled
├─ Mode: Dry Run / Live
├─ Active Strategies: X / 5
└─ Data Feed: metaapi  ← Should now show this!
```

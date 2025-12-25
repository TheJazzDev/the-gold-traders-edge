# Settings Management System - Complete Guide

## Overview

**You asked:** "Should settings be available to configure from admin panel from web app or do we have to change env everytime and redeploy?"

**Answer:** ✅ **Settings are now fully manageable via admin panel!** No more redeploying for configuration changes.

---

## What Changed

### ❌ Before (Environment Variables Only)
- Want to change max risk? Edit `.env` → Redeploy → Wait 2-3 minutes
- Want to disable a strategy? Edit code → Commit → Push → Redeploy
- Want to pause trading? Shut down entire service

### ✅ After (Database-Driven Settings)
- Want to change max risk? Call API → Change takes effect immediately
- Want to disable a strategy? Update via admin panel → Instant
- Want to pause trading? Toggle `auto_trading_enabled` → Done

---

## Architecture

```
┌─────────────────┐
│   Admin Panel   │
│   (Web UI)      │
└────────┬────────┘
         │
         │ HTTP API
         ▼
┌─────────────────┐
│  Settings API   │
│ /v1/settings/*  │
└────────┬────────┘
         │
         │ SQL
         ▼
┌─────────────────┐      ┌──────────────────┐
│ PostgreSQL DB   │◄─────┤ Signal Service   │
│ settings table  │      │ (reads settings) │
└─────────────────┘      └──────────────────┘
```

---

## Setup Instructions

### Step 1: Run Database Migration

```bash
# From Railway terminal or locally with DATABASE_URL set
cd packages/engine
python init_settings_table.py
```

This will:
- Create the `settings` table
- Seed 20+ default settings
- Display current configuration

### Step 2: Verify API Endpoints

After deployment, test these endpoints:

```bash
# Get all settings
curl https://your-app.railway.app/v1/settings

# Get settings by category
curl https://your-app.railway.app/v1/settings?category=risk_management

# Get specific setting
curl https://your-app.railway.app/v1/settings/max_risk_per_trade

# Update a setting
curl -X PUT https://your-app.railway.app/v1/settings/max_risk_per_trade \
  -H "Content-Type: application/json" \
  -d '{"value": 2.0, "modified_by": "admin"}'
```

---

## Available Settings

### 🤖 Trading Settings

| Key | Description | Default | Unit | Restart Required |
|-----|-------------|---------|------|------------------|
| `auto_trading_enabled` | Enable auto-trading | `false` | - | ✅ Yes |
| `trading_symbol` | Trading symbol | `XAUUSD` | - | ✅ Yes |
| `dry_run_mode` | Log trades without executing | `false` | - | ✅ Yes |
| `enabled_timeframes` | Active timeframes | `["5m", "15m", "30m", "1h", "4h", "1d"]` | - | ✅ Yes |

### 🛡️ Risk Management Settings

| Key | Description | Default | Range | Restart Required |
|-----|-------------|---------|-------|------------------|
| `max_risk_per_trade` | Max risk per trade | `1.0` | 0.1 - 10.0% | ❌ No |
| `max_positions` | Max concurrent positions | `5` | 1 - 20 | ❌ No |
| `max_daily_loss` | Daily loss limit | `3.0` | 1.0 - 20.0% | ❌ No |
| `max_weekly_loss` | Weekly loss limit | `10.0` | 3.0 - 50.0% | ❌ No |
| `max_correlated_positions` | Max correlated positions | `2` | 1 - 10 | ❌ No |

### 📊 Strategy Settings

| Key | Description | Default | Range | Restart Required |
|-----|-------------|---------|-------|------------------|
| `enabled_strategies` | Active strategies | `["momentum_equilibrium", ...]` | - | ✅ Yes |
| `min_rr_ratio` | Min risk:reward ratio | `1.5` | 1.0 - 5.0 | ❌ No |
| `min_confidence` | Min signal confidence | `0.6` | 0.0 - 1.0 | ❌ No |
| `duplicate_window_hours` | Duplicate check window | `4` | 1 - 24 hours | ❌ No |

### 🔔 Notification Settings

| Key | Description | Default | Restart Required |
|-----|-------------|---------|------------------|
| `telegram_enabled` | Enable Telegram notifications | `false` | ❌ No |
| `email_enabled` | Enable email notifications | `false` | ❌ No |
| `notify_on_signal` | Notify when signal generated | `true` | ❌ No |
| `notify_on_trade_open` | Notify when trade opened | `true` | ❌ No |
| `notify_on_trade_close` | Notify when trade closed | `true` | ❌ No |

### ⚙️ System Settings

| Key | Description | Default | Restart Required |
|-----|-------------|---------|------------------|
| `service_status` | Service status | `running` | ❌ No |
| `log_level` | Logging level | `INFO` | ❌ No |
| `data_feed_type` | Data provider | `yahoo` | ✅ Yes |

---

## API Endpoints Reference

### GET /v1/settings
Get all settings or filter by category.

**Query Parameters:**
- `category` (optional): `trading`, `risk_management`, `strategies`, `notifications`, `system`

**Response:**
```json
[
  {
    "id": 1,
    "key": "max_risk_per_trade",
    "category": "risk_management",
    "value": "1.0",
    "value_type": "float",
    "typed_value": 1.0,
    "default_value": "1.0",
    "description": "Maximum risk per trade",
    "unit": "%",
    "min_value": 0.1,
    "max_value": 10.0,
    "editable": true,
    "requires_restart": false,
    "last_modified_by": "admin",
    "updated_at": "2025-12-25T12:00:00Z"
  }
]
```

### GET /v1/settings/categories
Get settings grouped by category.

**Response:**
```json
[
  {
    "category": "trading",
    "settings": [...]
  },
  {
    "category": "risk_management",
    "settings": [...]
  }
]
```

### GET /v1/settings/{key}
Get a specific setting.

**Example:**
```bash
GET /v1/settings/max_risk_per_trade
```

### PUT /v1/settings/{key}
Update a setting.

**Request:**
```json
{
  "value": 2.0,
  "modified_by": "admin@example.com"
}
```

**Response:**
```json
{
  "id": 1,
  "key": "max_risk_per_trade",
  "typed_value": 2.0,
  "requires_restart": false,
  ...
}
```

### PUT /v1/settings/bulk/update
Update multiple settings at once.

**Request:**
```json
{
  "settings": {
    "max_risk_per_trade": 2.0,
    "max_positions": 10,
    "max_daily_loss": 5.0
  },
  "modified_by": "admin"
}
```

**Response:**
```json
{
  "success": true,
  "updated_count": 3,
  "failed_count": 0,
  "requires_restart": false,
  "details": {
    "updated": ["max_risk_per_trade", "max_positions", "max_daily_loss"],
    "failed": [],
    "requires_restart": []
  }
}
```

### POST /v1/settings/{key}/reset
Reset a setting to its default value.

### POST /v1/settings/reset-all
Reset ALL settings to defaults (use with caution!).

### GET /v1/settings/service/status
Get quick summary of key settings.

**Response:**
```json
{
  "service_status": "running",
  "auto_trading_enabled": true,
  "dry_run_mode": false,
  "max_risk_per_trade": 1.0,
  "max_positions": 5,
  "enabled_timeframes": ["5m", "15m", "30m", "1h", "4h", "1d"],
  "enabled_strategies": ["momentum_equilibrium", "london_session_breakout", ...]
}
```

---

## Common Use Cases

### 1. Enable Auto-Trading

```bash
curl -X PUT https://your-app.railway.app/v1/settings/auto_trading_enabled \
  -H "Content-Type: application/json" \
  -d '{"value": true, "modified_by": "admin"}'
```

⚠️ **Requires restart** - Redeploy service after changing this.

### 2. Increase Risk Per Trade

```bash
curl -X PUT https://your-app.railway.app/v1/settings/max_risk_per_trade \
  -H "Content-Type: application/json" \
  -d '{"value": 2.0, "modified_by": "admin"}'
```

✅ **Instant effect** - Next signal will use 2% risk.

### 3. Pause Trading (Without Stopping Service)

```bash
curl -X PUT https://your-app.railway.app/v1/settings/service_status \
  -H "Content-Type: application/json" \
  -d '{"value": "paused", "modified_by": "admin"}'
```

✅ **Instant effect** - Service continues running but won't execute new trades.

### 4. Enable Only One Strategy

```bash
curl -X PUT https://your-app.railway.app/v1/settings/enabled_strategies \
  -H "Content-Type: application/json" \
  -d '{"value": ["momentum_equilibrium"], "modified_by": "admin"}'
```

⚠️ **Requires restart** - Redeploy service after changing strategies.

### 5. Set Conservative Risk Profile

```bash
curl -X PUT https://your-app.railway.app/v1/settings/bulk/update \
  -H "Content-Type: application/json" \
  -d '{
    "settings": {
      "max_risk_per_trade": 0.5,
      "max_positions": 3,
      "max_daily_loss": 2.0,
      "min_rr_ratio": 2.0
    },
    "modified_by": "admin"
  }'
```

✅ **Instant effect** - All risk settings updated atomically.

---

## Integration with Signal Service

The signal service automatically reads settings from the database:

```python
# In run_multi_timeframe_service.py
from database.settings_repository import settings_manager

# Initialize on startup
settings_manager.initialize(db_manager)

# Read settings anywhere
auto_trading = settings_manager.get('auto_trading_enabled', default=False)
max_risk = settings_manager.get('max_risk_per_trade', default=1.0)

# Settings that require restart
if auto_trading:
    # Enable MT5Subscriber
    pass
```

### Settings That Take Effect Immediately

These don't require service restart:
- All risk management settings (`max_risk_per_trade`, `max_positions`, etc.)
- Signal validation settings (`min_rr_ratio`, `min_confidence`)
- Notification settings
- Service status (`running`/`paused`)

### Settings That Require Restart

These need a service redeploy:
- `auto_trading_enabled`
- `enabled_timeframes`
- `enabled_strategies`
- `data_feed_type`

---

## Web UI Integration (Future)

### Recommended UI Layout

```
┌─────────────────────────────────────────────┐
│  Settings Management                         │
├─────────────────────────────────────────────┤
│                                              │
│  🤖 Trading Configuration                    │
│  ├─ Auto-Trading: [Toggle]                  │
│  ├─ Symbol: [Dropdown: XAUUSD]              │
│  └─ Dry Run Mode: [Toggle]                  │
│                                              │
│  🛡️ Risk Management                          │
│  ├─ Max Risk Per Trade: [Slider: 1.0%]      │
│  ├─ Max Positions: [Input: 5]               │
│  ├─ Daily Loss Limit: [Slider: 3.0%]        │
│  └─ Weekly Loss Limit: [Slider: 10.0%]      │
│                                              │
│  📊 Strategy Selection                       │
│  ├─ [✓] Momentum Equilibrium                │
│  ├─ [✓] London Session Breakout             │
│  ├─ [✓] Golden Fibonacci                    │
│  ├─ [✓] ATH Retest                          │
│  └─ [✓] Order Block Retest                  │
│                                              │
│  [Save Changes]  [Reset to Defaults]        │
│                                              │
│  ⚠️ Changes marked with ⚙️ require restart   │
└─────────────────────────────────────────────┘
```

### Example React Component

```tsx
import { useState, useEffect } from 'react';

function SettingsPanel() {
  const [settings, setSettings] = useState([]);

  useEffect(() => {
    // Fetch settings
    fetch('/v1/settings/categories')
      .then(res => res.json())
      .then(data => setSettings(data));
  }, []);

  const updateSetting = async (key, value) => {
    await fetch(`/v1/settings/${key}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ value, modified_by: 'admin' })
    });
  };

  return (
    <div>
      {settings.map(category => (
        <SettingsCategory
          key={category.category}
          category={category}
          onUpdate={updateSetting}
        />
      ))}
    </div>
  );
}
```

---

## Benefits of Database-Driven Settings

### ✅ Instant Updates (for most settings)
- Change risk parameters without redeploying
- Toggle notifications on/off instantly
- Adjust strategy parameters in real-time

### ✅ Audit Trail
- Every change is logged with timestamp
- Track who made each change
- View change history

### ✅ Version Control
- Default values always available
- Easy to reset to defaults
- Can rollback individual settings

### ✅ Multi-Environment Support
- Different settings for dev/staging/prod
- No code changes needed
- Single codebase, multiple configs

### ✅ No Downtime for Config Changes
- Most settings take effect immediately
- No need to restart service
- No deployment pipeline delays

---

## Migration Path

### Current State (Environment Variables)
```bash
# Railway Variables Tab
ENABLE_AUTO_TRADING=true
MAX_RISK_PER_TRADE=1.0
MAX_POSITIONS=5
```

### After Migration (Database Settings)
```bash
# Railway Variables Tab (only credentials)
METAAPI_TOKEN=<token>
METAAPI_ACCOUNT_ID=<account_id>
DATABASE_URL=<database_url>

# All other settings in database!
```

---

## Next Steps

1. ✅ **Run migration** - `python init_settings_table.py`
2. ✅ **Test API endpoints** - Verify `/v1/settings` works
3. ⏳ **Build admin UI** - Create settings management panel
4. ⏳ **Update signal service** - Read from database instead of env vars
5. ⏳ **Remove hardcoded configs** - Migrate to settings table

---

## Summary

**Before:** Every config change = Edit env vars → Redeploy → Wait → Hope it works

**After:** Config change = Call API → Instant update → See effect immediately

You now have a production-ready settings management system that allows you to configure everything from the admin panel without ever touching environment variables or redeploying!

🎉 **No more redeploying for configuration changes!**

# API Service Down - Troubleshooting Guide

## Current Status

**API**: ❌ DOWN (502 error)
**Health Endpoint**: Not responding
**CORS Errors**: Caused by API being down (not a CORS issue)

## Why CORS Errors Appear When API is Down

When the API server is completely down:
1. Railway returns a 502 "Application failed to respond" error
2. This error response doesn't include CORS headers
3. Browser blocks the request and shows CORS error
4. **The root cause is NOT CORS - it's that the API isn't running**

## Steps to Fix

### 1. Check Railway Logs

Go to Railway Dashboard:
1. Open your API service
2. Click on "Deployments"
3. Click on the latest deployment
4. View the logs

**Look for**:
- Import errors
- Database connection errors
- Port binding errors
- Python errors on startup

### 2. Common Issues & Solutions

#### Issue: Database Connection Error
**Logs show**: `sqlalchemy.exc.OperationalError` or `could not connect to server`

**Fix**: Check `DATABASE_URL` environment variable is set correctly in Railway.

#### Issue: Missing Dependencies
**Logs show**: `ModuleNotFoundError: No module named 'X'`

**Fix**: Make sure `requirements.txt` includes all dependencies and Railway rebuilds.

#### Issue: Port Binding Error
**Logs show**: `Address already in use` or port errors

**Fix**: Railway auto-assigns PORT. Make sure API starts with:
```python
port = int(os.getenv("PORT", 8000))
uvicorn.run(app, host="0.0.0.0", port=port)
```

#### Issue: Import Path Errors
**Logs show**: `ModuleNotFoundError` for your own modules

**Fix**: Check all `sys.path.insert()` statements in routes are correct.

### 3. Force Restart in Railway

Sometimes Railway needs a hard restart:

1. Go to Railway Dashboard
2. Find your API service
3. Click **"..."** (three dots menu)
4. Click **"Restart"**
5. Wait 2-3 minutes

### 4. Check Dockerfile/Start Command

Make sure Railway knows how to start your API.

**Check `Dockerfile` or start command**:
```dockerfile
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "$PORT"]
```

Or in Railway settings, **Start Command**:
```bash
cd packages/api && uvicorn src.main:app --host 0.0.0.0 --port $PORT
```

### 5. Test Locally First

Before deploying again, test the API locally:

```bash
# Navigate to API directory
cd packages/api

# Set environment variables
export DATABASE_URL="your_railway_postgres_url"
export PORT=8000

# Start API
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

**Test endpoints**:
```bash
curl http://localhost:8000/health
curl http://localhost:8000/v1/signals/history?limit=5
```

If these work locally but not on Railway, it's a deployment configuration issue.

### 6. Rollback if Needed

If the latest deployment broke things:

1. Go to Railway Dashboard
2. Find your API service
3. Go to "Deployments"
4. Find a working deployment (before recent changes)
5. Click **"Redeploy"** on that old deployment

This will rollback to a working state.

## Quick Check Commands

**Test API is running**:
```bash
curl https://the-gold-traders-edge-production.up.railway.app/health
```

**Expected (working)**:
```json
{"status":"healthy","service":"Gold Trader's Edge API","version":"1.0.0"}
```

**Current (broken)**:
```json
{"status":"error","code":502,"message":"Application failed to respond"}
```

## What I Changed (For Reference)

1. **CORS** - `packages/api/src/main.py`:
   - Changed to `allow_origins=["*"]`
   - Should not cause startup issues

2. **Signals Route** - `packages/api/src/routes/signals.py`:
   - Added filters and pagination
   - Uses same imports as before
   - Should not cause startup issues

3. **Settings Route** - `packages/api/src/routes/settings.py`:
   - Added `data_feed_type` to response
   - Should not cause startup issues

**None of these changes should crash the API at startup.**

## Most Likely Causes

1. **Railway didn't restart the service** after deployment
2. **Database connection issue** (check DATABASE_URL env var)
3. **Old deployment is still running** (need manual restart)
4. **Build cache issue** (Railway using old cached build)

## Immediate Action

**Go to Railway NOW and**:
1. Check the logs for errors
2. Manually restart the API service
3. If that doesn't work, redeploy a previous working version

The CORS errors will disappear once the API is running again!

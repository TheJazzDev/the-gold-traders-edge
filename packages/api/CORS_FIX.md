# CORS Policy Fix

## Problem

Frontend at `https://the-gold-traders-edge.jazzdev.xyz` was blocked from accessing the API at `https://the-gold-traders-edge-production.up.railway.app` due to CORS policy:

```
Access to fetch at 'https://the-gold-traders-edge-production.up.railway.app/v1/signals/history?limit=10'
from origin 'https://the-gold-traders-edge.jazzdev.xyz' has been blocked by CORS policy:
No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

## Root Cause

The API's CORS middleware had `allow_origins=["*"]` which doesn't work properly with `allow_credentials=True`.

## Solution

**File:** `packages/api/src/main.py`

### Updated CORS Configuration

```python
# CORS configuration - allow production and local domains
allowed_origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8000",
    "https://the-gold-traders-edge.jazzdev.xyz",  # Production frontend
    "https://the-gold-traders-edge-production.up.railway.app",  # Railway API
]

# Add custom origins from environment variable
cors_origins_env = os.getenv("CORS_ORIGINS", "")
if cors_origins_env:
    additional_origins = [origin.strip() for origin in cors_origins_env.split(",")]
    allowed_origins.extend(additional_origins)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # ← Now uses specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## What Changed

1. **Replaced `["*"]` with explicit origin list**
   - Added production frontend domain
   - Added Railway API domain
   - Added localhost domains for development

2. **Added environment variable support**
   - Can add more origins via `CORS_ORIGINS` env var
   - Format: Comma-separated list

## Deployment

### Push Changes

```bash
git add packages/api/src/main.py
git commit -m "Fix: Add production domain to CORS allowed origins"
git push
```

### Railway Auto-Deploys

Railway will automatically deploy the fix to your API service.

### Optional: Add More Origins via Environment Variable

In Railway dashboard, you can add:

```
CORS_ORIGINS=https://www.your-domain.com,https://app.your-domain.com
```

## Testing

### Before Fix

```bash
# This would fail with CORS error
curl -H "Origin: https://the-gold-traders-edge.jazzdev.xyz" \
     -I https://the-gold-traders-edge-production.up.railway.app/v1/signals/history?limit=10
```

Response: No `Access-Control-Allow-Origin` header

### After Fix

```bash
# This should work
curl -H "Origin: https://the-gold-traders-edge.jazzdev.xyz" \
     -I https://the-gold-traders-edge-production.up.railway.app/v1/signals/history?limit=10
```

Response should include:
```
Access-Control-Allow-Origin: https://the-gold-traders-edge.jazzdev.xyz
Access-Control-Allow-Credentials: true
```

## Verification

After Railway deploys the fix:

1. **Open your frontend:** `https://the-gold-traders-edge.jazzdev.xyz`
2. **Check browser console** - CORS errors should be gone
3. **Verify API calls work** - Signals should load properly

## Additional Domains

If you need to add more domains in the future:

### Option 1: Update Code

Edit `packages/api/src/main.py` and add to the `allowed_origins` list:

```python
allowed_origins = [
    # ... existing origins ...
    "https://your-new-domain.com",
]
```

### Option 2: Use Environment Variable

Add to Railway environment variables:

```
CORS_ORIGINS=https://new-domain.com,https://another-domain.com
```

This is useful for:
- Preview deployments
- Staging environments
- Additional custom domains

## Security Notes

✅ **Good practices used:**
- Explicit origin list (not wildcard)
- Environment variable support for flexibility
- Works with credentials
- Includes only trusted domains

❌ **Avoid:**
- `allow_origins=["*"]` with credentials
- Adding untrusted domains
- Removing `allow_credentials` if your app needs it

## Summary

**Problem:** CORS blocking frontend from accessing API ❌
**Solution:** Added production domain to allowed origins ✅
**Deploy:** Push to GitHub → Railway auto-deploys → Done! ✅

The frontend should now be able to access the API without CORS errors.

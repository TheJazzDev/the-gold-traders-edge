# 🚀 Deployment Guide - The Gold Trader's Edge

**Complete step-by-step guide to deploy and start generating real-time gold trading signals**

---

## 🎯 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    USERS (Traders)                          │
└────────────────┬────────────────────────────────────────────┘
                 │
    ┌────────────┴────────────┐
    │                         │
    ▼                         ▼
┌─────────────┐          ┌──────────────────┐
│   VERCEL    │          │     RAILWAY      │
│ (Frontend)  │◄─────────┤   (Backend)      │
│  ✅ DEPLOYED│   API    │   🔶 TO DEPLOY   │
└─────────────┘          └─────────┬────────┘
                                   │
              Supervisor (runs both services together)
                                   │
                    ┌──────────────┴──────────────┐
                    │                             │
                    ▼                             ▼
            ┌──────────────┐            ┌──────────────────┐
            │  FastAPI     │            │ Signal Generator │
            │  (Port 8000) │            │ (Background)     │
            └──────┬───────┘            └──────┬───────────┘
                   │                           │
                   │   ┌───────────────────────┘
                   │   │
                   ▼   ▼
            ┌──────────────────┐
            │ SQLite Database  │
            │ (/data/signals.db)│
            └──────────────────┘
```

**Key Points:**
✅ **Frontend** (Vercel) - Already deployed
🔶 **Backend** (Railway) - Need to deploy (API + Signal Generator run together via Supervisor)
📊 **Database** - SQLite with persistent volume (automatically handled)

---

## 📦 STEP 1: Deploy Backend to Railway

### What You'll Deploy:
One Railway service running **both** API and Signal Generator together using Supervisor (already configured ✅)

### 1A. Prepare Repository

```bash
# Navigate to project
cd /Users/jazzdev/Documents/Programming/the-gold-traders-edge

# Commit pending changes
git add .
git commit -m "Ready for production deployment"
git push origin phase-2/demo-trading  # or merge to main first
```

### 1B. Deploy via Railway Dashboard

**Option A: Railway Dashboard (Easiest)**

1. Go to https://railway.app
2. Sign up/Login with GitHub
3. Click **"New Project"**
4. Select **"Deploy from GitHub repo"**
5. Choose: `the-gold-traders-edge`
6. Railway auto-detects:
   - ✅ Dockerfile
   - ✅ railway.json
   - ✅ Supervisor configuration
7. Click **"Deploy"**

**Option B: Railway CLI (For advanced users)**

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Initialize & deploy
railway init
railway up
```

### 1C. Add Persistent Volume for Database

**IMPORTANT:** Add this before first deployment!

1. In Railway dashboard → Your project
2. Go to **Settings** → **Volumes**
3. Click **"New Volume"**
   - **Mount Path:** `/data`
   - This ensures signals persist across deployments

### 1D. Configure Environment Variables

In Railway dashboard → **Variables** → Add these:

```bash
# ============================================================================
# CORE SETTINGS
# ============================================================================
ENVIRONMENT=production
DATABASE_URL=sqlite:////data/signals.db

# ============================================================================
# API CONFIGURATION
# ============================================================================
API_V1_STR=/v1
PROJECT_NAME=Gold Trader's Edge API
API_HOST=0.0.0.0
PORT=8000

# CORS - Update with YOUR Vercel URL
CORS_ORIGINS=https://your-app-name.vercel.app,http://localhost:3000

# ============================================================================
# DATA FEED (Yahoo Finance - Free, 15min delay)
# ============================================================================
DATAFEED_TYPE=yahoo
SYMBOL=XAUUSD
TIMEFRAME=4H

# ============================================================================
# SIGNAL GENERATION
# ============================================================================
ENABLE_DATABASE=true
ENABLE_LOGGER=true
ENABLE_CONSOLE=true
MIN_RR_RATIO=1.5
HEARTBEAT_INTERVAL=5

# ============================================================================
# SECURITY (Generate new secret!)
# ============================================================================
SECRET_KEY=generate-this-with-openssl-rand-hex-32
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

**Generate SECRET_KEY:**
```bash
openssl rand -hex 32
```
Copy the output and paste it as `SECRET_KEY` value.

### 1E. Get Your Railway URL

After deployment completes:

1. Railway assigns a domain like: `https://the-gold-traders-edge-production.up.railway.app`
2. Copy this URL - you'll need it for Step 2
3. Test it works:
   ```bash
   curl https://your-railway-url.up.railway.app/health
   ```

   Expected response:
   ```json
   {
     "status": "healthy",
     "service": "Gold Trader's Edge API",
     "version": "1.0.0"
   }
   ```

### 1F. Verify Both Services Are Running

Check Railway logs (Deployments → View Logs):

You should see:
```
[program:api] Started
[program:signal-generator] Started
📊 GOLD TRADER'S EDGE - REAL-TIME SIGNAL SERVICE
⚙️  Configuration loaded
📡 Data feed connected: Yahoo Finance
```

**✅ Backend deployed successfully!**

---

## 🌐 STEP 2: Update Frontend with Production API

Since your frontend is **already deployed on Vercel** ✅, you just need to update the API URL.

### 2A. Update Vercel Environment Variables

1. Go to https://vercel.com → Your project
2. Navigate to **Settings** → **Environment Variables**
3. Find or add: `NEXT_PUBLIC_API_URL`
4. Set value to: `https://your-railway-url.up.railway.app` (from Step 1E)
5. Click **Save**

### 2B. Redeploy Frontend

**Option A: Via Vercel Dashboard**
1. Go to **Deployments** tab
2. Click the **⋯** menu on latest deployment
3. Select **"Redeploy"**
4. Check **"Use existing Build Cache"** (faster)
5. Click **"Redeploy"**

**Option B: Via Git Push**
```bash
# Make a small change to trigger deployment
git commit --allow-empty -m "Update production API URL"
git push
```

### 2C. Update CORS on Railway

Now that you have your Vercel URL, update Railway:

1. Go to Railway dashboard → Your project → **Variables**
2. Update `CORS_ORIGINS` to:
   ```
   https://your-vercel-app.vercel.app,http://localhost:3000
   ```
3. Railway will auto-redeploy

**✅ Frontend connected to production API!**

---

## 🎯 STEP 3: Verify Real-Time Signal Flow

### 3A. Test API Endpoints

```bash
# Replace with your Railway URL
API_URL="https://your-railway-url.up.railway.app"

# Health check
curl $API_URL/health

# Get signals (might be empty initially)
curl $API_URL/v1/signals?limit=10

# Get signal stats
curl $API_URL/v1/signals/stats
```

### 3B. Monitor Signal Generation

**Check Railway Logs:**

Go to Railway dashboard → Deployments → **View Logs**

Look for these messages:

```
✅ Good signs:
[program:signal-generator] 📊 Service started, monitoring XAUUSD on 4H
[program:signal-generator] ⏰ Heartbeat: Service running, checking for candle close...
[program:signal-generator] 📊 Candle close detected at 2025-12-23 12:00:00
[program:signal-generator] ✅ New signal generated: BUY XAUUSD @ 2650.00
[program:signal-generator] 💾 Signal saved to database

❌ Warning signs:
ERROR: Failed to connect to data feed
ERROR: Database connection failed
WARNING: No candle close detected yet (this is normal between candle closes)
```

### 3C. Test Frontend Connection

1. Open your Vercel app: `https://your-app.vercel.app`
2. Check dashboard status indicator (should show "API Connected")
3. Verify signals list loads (might be empty if no signals generated yet)
4. Open browser console (F12) - should see no CORS errors

### 3D. Wait for First Signal

**Important:** Signals are generated on **4H candle closes**

XAUUSD 4H candles close at:
- 00:00 UTC
- 04:00 UTC
- 08:00 UTC
- 12:00 UTC
- 16:00 UTC
- 20:00 UTC

**Timeline:**
```
Deploy backend → Wait for next 4H close → Signal generated → Appears on dashboard
                 (up to 4 hours)         (instant)          (within 30s)
```

**✅ System fully operational!**

---

## 📊 STEP 4: How Real-Time Signals Work

### Complete Data Flow Diagram

```
┌───────────────────────────────────────────────────────────────┐
│                    YAHOO FINANCE                              │
│          (Free market data, 15min delay)                      │
└────────────────────────┬──────────────────────────────────────┘
                         │
                         │ Every 4H candle close
                         │ (00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC)
                         │
                         ▼
┌───────────────────────────────────────────────────────────────┐
│               SIGNAL GENERATOR (Railway)                      │
│  1. Detect candle close                                       │
│  2. Analyze with Momentum Equilibrium (Rule 5)                │
│  3. Check: momentum reversal + trend alignment                │
│  4. Calculate: Entry, SL, TP, R:R                             │
│  5. Validate: R:R >= 1.5                                      │
└────────────────────────┬──────────────────────────────────────┘
                         │
                         │ Save signal
                         │
                         ▼
┌───────────────────────────────────────────────────────────────┐
│              SQLITE DATABASE (/data/signals.db)               │
│  Table: signals                                               │
│  - signal_id, timestamp, direction, symbol                    │
│  - entry_price, stop_loss, take_profit                        │
│  - risk_reward_ratio, strategy                                │
│  - status (generated/executed/closed)                         │
└────────────┬──────────────────────────────────────────────────┘
             │                              │
             │ Read signals                 │ (Future: Demo trading)
             ▼                              ▼
┌─────────────────────────┐    ┌───────────────────────────────┐
│   FASTAPI (Railway)     │    │ TRADE SUBSCRIBER (Future)     │
│   GET /v1/signals       │    │ - Auto-execute on MetaAPI     │
│   - Query database      │    │ - Track positions             │
│   - Return JSON         │    │ - Update signal status        │
│   - CORS enabled        │    └───────────────────────────────┘
└────────────┬────────────┘
             │
             │ HTTPS REST API
             │
             ▼
┌───────────────────────────────────────────────────────────────┐
│            NEXT.JS DASHBOARD (Vercel)                         │
│  1. Auto-refresh every 30 seconds                             │
│  2. Fetch: /v1/signals?limit=20                               │
│  3. Display: Latest signals in table                          │
│  4. Show: Entry, SL, TP, R:R, Status                          │
│  5. Calculate: Performance stats                              │
└───────────────────────────────────────────────────────────────┘
             │
             ▼
┌───────────────────────────────────────────────────────────────┐
│                    USER (Trader)                              │
│  - Sees signals in real-time (max 30s delay)                  │
│  - Can manually execute on MT5                                │
│  - Tracks performance                                         │
└───────────────────────────────────────────────────────────────┘
```

### Signal Generation Process

**Every 4 hours, the system:**

1. **Fetches latest candle data** from Yahoo Finance
2. **Detects candle close** (4H timeframe)
3. **Runs strategy analysis:**
   - Calculate momentum indicators
   - Detect trend direction
   - Find entry points
   - Calculate stop loss (based on swing low/high)
   - Calculate take profit (based on R:R ratio)
4. **Validates signal:**
   - R:R ratio >= 1.5
   - No duplicate signals for same setup
   - Entry price within reasonable range
5. **Saves to database** with all details
6. **Logs to console** and file

**API serves signals:**

1. **Runs 24/7** alongside signal generator
2. **Reads from same database** (SQLite file)
3. **Exposes REST endpoints:**
   - `/v1/signals` - Get all signals
   - `/v1/signals/{id}` - Get specific signal
   - `/v1/signals/stats` - Get performance stats
4. **CORS enabled** for Vercel domain

**Dashboard displays signals:**

1. **Auto-refresh every 30s** (configurable)
2. **Fetches latest signals** via API
3. **Updates UI** with new signals
4. **Shows real-time** performance metrics

### Why Signals Appear in Real-Time

```
Time: 12:00:00 UTC → 4H candle closes
Time: 12:00:05 UTC → Signal generator detects close
Time: 12:00:10 UTC → Strategy analysis completes
Time: 12:00:11 UTC → Signal saved to database
Time: 12:00:15 UTC → User's dashboard auto-refreshes
Time: 12:00:16 UTC → API returns new signal
Time: 12:00:16 UTC → Signal appears on dashboard

Total delay: ~16 seconds
```

**Maximum delay:** 30 seconds (dashboard refresh interval)

---

## ✅ STEP 5: Post-Deployment Checklist

### Immediate Verification (Do this now):

- [ ] Railway deployment succeeded
- [ ] API health check passes: `curl https://your-railway-url.up.railway.app/health`
- [ ] Vercel environment variable updated with Railway URL
- [ ] Frontend redeployed successfully
- [ ] CORS configured with Vercel URL
- [ ] Both services running in Railway logs

### Within First 4 Hours (Wait for candle close):

- [ ] Signal generator heartbeat in logs (every 5 min)
- [ ] No errors in Railway logs
- [ ] Dashboard loads and shows "API Connected"
- [ ] Next 4H candle close occurs
- [ ] Signal generated and appears in logs
- [ ] Signal appears on dashboard (within 30s)

### Optional - Enable Demo Trading (When ready):

- [ ] Deposit $10 to MetaAPI account
- [ ] Get MetaAPI token and account ID
- [ ] Add to Railway environment variables:
  - `METAAPI_TOKEN`
  - `METAAPI_ACCOUNT_ID`
  - `MT5_CONNECTION_TYPE=metaapi`
- [ ] Redeploy Railway service
- [ ] Verify MT5 connection in logs
- [ ] Monitor automatic trade execution

---

## 💰 Monthly Cost Breakdown

### Current Setup (Signal Generation Only):
- **Vercel:** $0 (Free tier - perfect for this)
- **Railway:** $20/month (Developer plan for 24/7 uptime)
- **Yahoo Finance:** $0 (Free API)
- **Total:** **$20/month**

### With Demo Trading (Future):
- **Vercel:** $0
- **Railway:** $20/month
- **MetaAPI:** $4/month + $10 one-time deposit
- **Total:** **$24/month** (+ $10 initial)

**Note:** Railway Hobby plan ($5/mo) only includes 500 hours. Running 24/7 = 720 hours, so Developer plan is required.

---

## 🔍 Troubleshooting Guide

### Problem: API Returns 404

**Symptoms:**
```bash
curl https://your-app.railway.app/health
# 404 Not Found
```

**Fix:**
1. Check Railway logs for startup errors
2. Verify Dockerfile builds successfully
3. Ensure `railway.json` has correct start command
4. Check `PORT` environment variable is set

### Problem: Signal Generator Not Running

**Symptoms:**
- No heartbeat logs every 5 minutes
- No `[program:signal-generator]` in logs

**Fix:**
1. Check Railway logs for errors:
   ```
   [program:signal-generator] FATAL: Exited too quickly
   ```
2. Verify environment variables:
   - `DATAFEED_TYPE=yahoo`
   - `DATABASE_URL=sqlite:////data/signals.db`
3. Ensure `/data` volume is mounted
4. Check supervisor config in logs

### Problem: CORS Errors on Dashboard

**Symptoms:**
```
Access to fetch has been blocked by CORS policy
```

**Fix:**
1. Verify `CORS_ORIGINS` in Railway includes exact Vercel URL
2. Must include `https://` (not `http://`)
3. No trailing slash
4. Example: `CORS_ORIGINS=https://gold-edge.vercel.app,http://localhost:3000`
5. Redeploy Railway after changing

### Problem: No Signals Generated

**Symptoms:**
- API returns empty array: `{"signals": []}`
- Dashboard shows "No signals yet"

**Possible Causes:**
1. **Too early** - Need to wait for 4H candle close
2. **No valid signals** - Strategy didn't find entry (normal)
3. **Database error** - Check logs for write errors

**Fix:**
1. Check time - signals only generate at: 00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC
2. Wait for next candle close
3. Check logs for "Signal generated" message
4. Verify `/data` volume has write permissions

### Problem: Database Connection Failed

**Symptoms:**
```
ERROR: Could not connect to database
sqlite3.OperationalError: unable to open database file
```

**Fix:**
1. Check `/data` volume is created and mounted
2. Verify `DATABASE_URL=sqlite:////data/signals.db` (4 slashes!)
3. Railway volume mount path must be exactly `/data`

### Problem: Yahoo Finance Connection Failed

**Symptoms:**
```
ERROR: Failed to fetch data from Yahoo Finance
ConnectionError: Unable to connect
```

**Fix:**
1. Yahoo Finance might be rate-limiting
2. Increase `HEARTBEAT_INTERVAL` to 10 minutes
3. Check Railway outbound network connectivity
4. Try different data feed: `DATAFEED_TYPE=metaapi` (requires account)

---

## 📊 Monitoring & Maintenance

### Daily Checks (First Week):

1. **Railway Dashboard** → View Logs
   - Look for errors or crashes
   - Verify heartbeat every 5 minutes
   - Check signal generation at candle closes

2. **Vercel Dashboard** → Deployments
   - Check for build failures
   - Monitor error rates in Analytics

3. **Test API Health:**
   ```bash
   curl https://your-railway-url.up.railway.app/health
   ```

### Weekly Checks (Ongoing):

1. **Review generated signals:**
   ```bash
   curl https://your-railway-url.up.railway.app/v1/signals?limit=50
   ```

2. **Check database size:**
   - Railway dashboard → Volumes
   - Should grow slowly (few KB per signal)

3. **Monitor Railway usage:**
   - Ensure within plan limits
   - Check monthly cost forecast

### Database Backup (Monthly):

```bash
# Using Railway CLI
railway link  # Link to your project
railway volumes  # List volumes
railway run bash  # Open shell in container

# Inside container:
cp /data/signals.db /tmp/backup-$(date +%Y%m%d).db
# Download via Railway dashboard
```

---

## 🚀 Next Steps After Deployment

### Immediate (Today):
1. ✅ Complete deployment (Steps 1-3 above)
2. ✅ Verify system is running
3. ✅ Wait for first signal (up to 4 hours)

### This Week:
1. Monitor signal generation for 7 days
2. Verify all signals appear on dashboard
3. Check signal quality and frequency
4. Review Railway logs for any issues

### This Month:
1. Analyze 30 days of signal performance
2. Decide if strategy needs tuning
3. Consider enabling demo trading
4. Evaluate switching to MetaAPI for real-time data

### Future Enhancements:
1. **Demo Trading** - Auto-execute signals on MT5 demo account
2. **Mobile App** - React Native app with push notifications
3. **Advanced Analytics** - Performance reports, win rate tracking
4. **Telegram Bot** - Receive signals via Telegram
5. **Multi-Strategy** - Add Rules 1-4 for more signals
6. **Live Trading** - After 30-day validation, switch to real account

---

## 🆘 Getting Help

**Check Logs First:**
- Railway: Dashboard → Deployments → View Logs
- Vercel: Dashboard → Deployments → Function Logs

**Common Issues:**
- 90% are environment variable problems
- Check spelling and format carefully
- Ensure URLs have no trailing slashes

**Still Stuck?**
1. Copy exact error message from logs
2. Check environment variables match guide
3. Verify volume mount path is `/data`
4. Test locally with Docker first

---

## 🎉 Success Criteria

**You know deployment worked when:**

✅ Railway logs show:
```
[program:api] Started
[program:signal-generator] Started
⚙️  Configuration loaded
📡 Data feed connected: Yahoo Finance
⏰ Heartbeat: Service running...
```

✅ API health check returns:
```json
{"status": "healthy"}
```

✅ Dashboard shows:
- "API Connected" status
- Service status: "Running"
- Signals list loads (empty is OK initially)

✅ After 4H candle close:
```
[program:signal-generator] ✅ New signal generated
[program:signal-generator] 💾 Signal saved to database
```

✅ Dashboard auto-refreshes and shows new signal

---

**Deployment Date:** _________
**Railway URL:** _________
**Vercel URL:** _________
**First Signal Generated:** _________

---

*Guide Version: 2.0*
*Last Updated: December 23, 2025*
*Deployment Stack: Railway (Backend) + Vercel (Frontend) + SQLite (Database)*

# Deployment Guide - The Gold Trader's Edge

Complete guide for deploying the full stack application.

---

## 🎯 Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Users                               │
└────────────────┬────────────────────────────────────────────┘
                 │
    ┌────────────┴────────────┐
    │                         │
    ▼                         ▼
┌─────────┐              ┌──────────┐
│  Vercel │              │ Railway  │
│ (Web UI)│              │ (Backend)│
└─────────┘              └─────┬────┘
                               │
                    ┌──────────┴──────────┐
                    │                     │
                    ▼                     ▼
            ┌──────────────┐      ┌──────────────┐
            │   API Server │      │    Signal    │
            │   (FastAPI)  │      │   Generator  │
            └──────┬───────┘      └──────┬───────┘
                   │                     │
                   │   ┌─────────────────┘
                   │   │
                   ▼   ▼
            ┌──────────────┐
            │   SQLite DB  │
            │   (Signals)  │
            └──────────────┘
```

---

## 📦 Part 1: Deploy Backend (Railway)

### Step 1: Prepare Your Repository

1. **Ensure all files are committed:**
```bash
cd /path/to/the-gold-traders-edge
git add .
git commit -m "Prepare for deployment"
git push origin main
```

2. **Verify Docker files exist:**
- ✅ `Dockerfile`
- ✅ `docker-compose.prod.yml`
- ✅ `.dockerignore`
- ✅ `railway.json`

### Step 2: Deploy to Railway

1. **Go to Railway:** https://railway.app
2. **Sign up/Login** with GitHub
3. **New Project** → **Deploy from GitHub repo**
4. **Select:** `the-gold-traders-edge` repository
5. **Railway will auto-detect** the Dockerfile

### Step 3: Configure Environment Variables

In Railway dashboard, add these environment variables:

```bash
# API Configuration
API_V1_STR=/v1
PROJECT_NAME=Gold Trader's Edge API
CORS_ORIGINS=https://your-vercel-app.vercel.app

# Database
DATABASE_URL=sqlite:////data/signals.db

# Data Feed
DATAFEED_TYPE=yahoo
SYMBOL=XAUUSD
TIMEFRAME=4H

# API Server
PORT=8000
API_HOST=0.0.0.0
```

### Step 4: Add MetaAPI Credentials (After $10 deposit)

```bash
# MetaAPI (Add these after you deposit $10)
MT5_CONNECTION_TYPE=metaapi
METAAPI_TOKEN=your_token_here
METAAPI_ACCOUNT_ID=your_account_id_here
MT5_SYMBOL=XAUUSD

# Risk Management
MAX_RISK_PER_TRADE=0.01
MAX_POSITIONS=2
MAX_DAILY_LOSS=0.03
POSITION_SIZE_MODE=risk_based
```

### Step 5: Deploy Signal Generator Service

Railway doesn't support multiple services in one deployment easily. **Options:**

**Option A: Run Both in One Container (Recommended for Railway)**
- Modify start command to run both API + Signal Generator
- Uses process manager (like supervisord)

**Option B: Create Separate Railway Services**
- Deploy API as one service
- Deploy Signal Generator as another service
- Both connect to same database volume

**Option C: Use Different Platform for Services**
- Railway: API only
- Render/Fly.io: Signal Generator

**I recommend Option A for simplicity. Want me to set that up?**

### Step 6: Get Your API URL

After deployment:
1. Railway will give you a URL: `https://your-app.railway.app`
2. Test it: `https://your-app.railway.app/health`
3. Save this URL for Vercel configuration

---

## 🌐 Part 2: Deploy Frontend (Vercel)

### Step 1: Prepare Web App

1. **Update API URL in web app:**

```bash
cd apps/web
```

Create `.env.production`:
```bash
NEXT_PUBLIC_API_URL=https://your-app.railway.app
```

2. **Commit changes:**
```bash
git add .
git commit -m "Add production API URL"
git push
```

### Step 2: Deploy to Vercel

1. **Go to Vercel:** https://vercel.com
2. **Import Project** → Select your GitHub repo
3. **Root Directory:** `apps/web`
4. **Framework Preset:** Next.js (auto-detected)
5. **Environment Variables:**
```bash
NEXT_PUBLIC_API_URL=https://your-app.railway.app
```

6. **Deploy!**

### Step 3: Update CORS

After Vercel deployment:
1. Get your Vercel URL: `https://your-app.vercel.app`
2. Update Railway environment variable:
```bash
CORS_ORIGINS=https://your-app.vercel.app,http://localhost:3000
```

3. Redeploy Railway service

---

## 🔧 Part 3: Running Multiple Services (Advanced)

### Option 1: Modify Dockerfile to Run Both Services

Update `Dockerfile` CMD:

```dockerfile
# Install supervisor
RUN pip install supervisor

# Copy supervisor config
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Run supervisor
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
```

Create `supervisord.conf`:
```ini
[supervisord]
nodaemon=true

[program:api]
command=python -m uvicorn api.src.main:app --host 0.0.0.0 --port 8000
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stderr_logfile=/dev/stderr

[program:signals]
command=python /app/engine/run_signal_service.py
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stderr_logfile=/dev/stderr
```

### Option 2: Use Railway's Multiple Services

1. Create `railway.json` for each service
2. Deploy API service
3. Deploy Signal service separately
4. Both share database via Railway volumes

---

## 📊 Part 4: Monitoring & Maintenance

### Health Checks

**API Health:**
```bash
curl https://your-app.railway.app/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "service": "Gold Trader's Edge API",
  "version": "1.0.0"
}
```

### View Logs

**Railway:**
- Dashboard → Your Project → Deployments → View Logs

**Check Signal Generation:**
```bash
# In Railway logs, look for:
"Signal generated"
"Candle processed"
"Signal saved to database"
```

### Database Backup

Railway provides automatic backups, but you can also:

1. **Download database:**
```bash
# From Railway CLI
railway run python -c "import shutil; shutil.copy('/data/signals.db', '/tmp/backup.db')"
```

2. **Schedule backups** (add to your service):
```python
# cron job to backup database daily
```

---

## 🚀 Part 5: Post-Deployment Checklist

### Immediately After Deployment:

- [ ] API health check passes
- [ ] Vercel site loads
- [ ] Web app can fetch data from API
- [ ] CORS configured correctly
- [ ] Environment variables set

### Within 24 Hours:

- [ ] Signal generator running (check logs)
- [ ] First signal generated (check database)
- [ ] Web dashboard shows signal
- [ ] No errors in logs

### After MetaAPI Deposit:

- [ ] Add METAAPI credentials to Railway
- [ ] Deploy demo trading service
- [ ] Verify MT5 connection
- [ ] Monitor first trade execution

---

## 💰 Cost Breakdown

### Free Tier (Testing):
- **Vercel:** Free (hobby plan)
- **Railway:** $5/month (500 hours free)
- **Total:** $5/month

### With MetaAPI (Live Trading):
- **Vercel:** Free
- **Railway:** $5-10/month
- **MetaAPI:** $2.10/month
- **Total:** ~$7-12/month

---

## 🔍 Troubleshooting

### API Not Responding

**Check:**
1. Railway logs for errors
2. Environment variables set correctly
3. Database path accessible
4. Port configuration

**Fix:**
```bash
# Redeploy
railway up --detach
```

### Signal Generator Not Running

**Check:**
1. Process is running in logs
2. Yahoo Finance connection working
3. Database writable

**Fix:**
- Check DATAFEED_TYPE is set to 'yahoo'
- Verify database path has write permissions

### CORS Errors

**Check:**
1. CORS_ORIGINS includes your Vercel URL
2. URL includes https:// (not http://)

**Fix:**
```bash
# Update Railway env var
CORS_ORIGINS=https://exact-vercel-url.vercel.app
```

---

## 📝 Next Steps

1. **Deploy API to Railway** ← Start here
2. **Deploy Web to Vercel**
3. **Test end-to-end**
4. **Add MetaAPI credentials** (after $10 deposit)
5. **Enable demo trading service**
6. **Monitor for 30 days**

---

## 🆘 Support

**Issues?**
- Check Railway/Vercel logs first
- Review environment variables
- Test locally with Docker first
- Check GitHub issues

**Ready to deploy?**
Let me know which option you want for running multiple services!

---

*Last Updated: December 22, 2025*
*Deployment Strategy: Railway + Vercel*

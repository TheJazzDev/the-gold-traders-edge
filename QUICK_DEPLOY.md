# ⚡ Quick Deploy - 15 Minutes to Live

**Your frontend is already on Vercel ✅ - Just deploy the backend!**

---

## 🚀 Deploy Backend to Railway (10 min)

### Step 1: Push Code to GitHub (2 min)
```bash
cd /Users/jazzdev/Documents/Programming/the-gold-traders-edge
git add .
git commit -m "Ready for production deployment"
git push origin phase-2/demo-trading  # or merge to main first
```

### Step 2: Deploy to Railway (3 min)
1. Go to https://railway.app
2. Login with GitHub
3. **New Project** → **Deploy from GitHub repo**
4. Select: `the-gold-traders-edge`
5. Wait for build (~3 min)

### Step 3: Add Database Volume (1 min)
1. Railway dashboard → **Settings** → **Volumes**
2. **New Volume**
3. Mount path: `/data`
4. Save

### Step 4: Set Environment Variables (3 min)
Copy from `RAILWAY_ENV_TEMPLATE.txt` and paste into Railway → **Variables**

**Must update these:**
- `CORS_ORIGINS` → Your Vercel URL (e.g., `https://gold-edge.vercel.app`)
- `SECRET_KEY` → Run `openssl rand -hex 32` in terminal, paste output

### Step 5: Get Railway URL (1 min)
- Copy your Railway URL: `https://xyz.up.railway.app`
- Test it: `curl https://your-url.up.railway.app/health`
- Should return: `{"status": "healthy"}`

---

## 🌐 Update Frontend (5 min)

### Step 1: Update Vercel Environment Variable
1. Go to https://vercel.com → Your project
2. **Settings** → **Environment Variables**
3. Update `NEXT_PUBLIC_API_URL` to your Railway URL
4. Save

### Step 2: Redeploy
1. **Deployments** tab → Latest deployment → **⋯** menu
2. Click **"Redeploy"**
3. Wait ~1 minute

### Step 3: Update CORS on Railway
1. Go back to Railway → **Variables**
2. Update `CORS_ORIGINS` to your Vercel URL (from browser address bar)
   - Example: `https://gold-traders-edge.vercel.app,http://localhost:3000`
3. Save (auto-redeploys)

---

## ✅ Verify It's Working

```bash
# Test API health
curl https://your-railway-url.up.railway.app/health
# Expected: {"status": "healthy"}
```

**Check Railway Logs:**
1. Railway dashboard → Deployments → **View Logs**
2. Look for:
   ```
   [program:api] Started
   [program:signal-generator] Started
   📊 Service started, monitoring XAUUSD on 4H
   ⏰ Heartbeat: Service running...
   ```

**Open Dashboard:**
1. Visit your Vercel URL
2. Should show "API Connected" status
3. Signals list loads (empty initially is OK)

**Wait for First Signal:**
- Signals generate at: 00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC
- Dashboard auto-refreshes every 30 seconds
- Max wait: 4 hours for next candle close

---

## 📊 System is Now Live!

**What's happening now:**
1. ✅ Signal generator monitoring XAUUSD 24/7
2. ✅ API serving data to dashboard
3. ✅ Dashboard auto-refreshing every 30s
4. ⏳ Waiting for next 4H candle close to generate signal

**Cost:** $20/month (Railway Developer plan)

---

## 🔮 Next Steps (Optional)

### Enable Demo Trading (When Ready)
1. Deposit $10 to MetaAPI account
2. Add to Railway variables:
   ```
   MT5_CONNECTION_TYPE=metaapi
   METAAPI_TOKEN=your_token
   METAAPI_ACCOUNT_ID=your_account_id
   MT5_SYMBOL=XAUUSD
   MAX_RISK_PER_TRADE=0.01
   MAX_POSITIONS=2
   MAX_DAILY_LOSS=0.03
   ```
3. Signals will auto-execute on MT5 demo account

---

## 🆘 Troubleshooting

### API Returns 404
- Check Railway logs for build errors
- Verify Dockerfile built successfully
- Ensure environment variables are set

### CORS Errors
- CORS_ORIGINS must exactly match Vercel URL
- Include `https://` (not `http://`)
- No trailing slash

### No Signals After 24 Hours
1. Check Railway logs for errors
2. Verify signal generator is running
3. Look for "Signal generated" in logs
4. Strategy might not find valid entries (normal)

### Database Errors
- Ensure `/data` volume is created and mounted
- DATABASE_URL needs 4 slashes: `sqlite:////data/signals.db`
- Check write permissions in logs

---

## 📚 More Info

- **Full Guide:** See `DEPLOYMENT_GUIDE.md`
- **Environment Variables:** See `RAILWAY_ENV_TEMPLATE.txt`
- **Architecture:** See `DEPLOYMENT_GUIDE.md` Step 4

---

**That's it! 🎉**

Your gold trading signal system is now live and monitoring the market!

**Deployment Checklist:**
- [x] Backend deployed to Railway
- [x] Frontend updated with API URL
- [x] Environment variables configured
- [x] CORS set up correctly
- [x] System verified working
- [ ] Wait for first signal (up to 4 hours)
- [ ] Monitor for 7 days
- [ ] Optional: Enable demo trading

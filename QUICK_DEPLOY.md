# Quick Deploy Guide

**Get your app running in 15 minutes!**

---

## 🚀 Backend (Railway) - 5 minutes

### 1. Push to GitHub
```bash
git add .
git commit -m "Ready for deployment"
git push origin main
```

### 2. Deploy to Railway
1. Go to https://railway.app
2. **New Project** → **Deploy from GitHub repo**
3. Select: `the-gold-traders-edge`
4. Railway auto-deploys!

### 3. Add Environment Variables

Click **Variables** in Railway dashboard and add:

```bash
# Required
DATAFEED_TYPE=yahoo
SYMBOL=XAUUSD
TIMEFRAME=4H
DATABASE_URL=sqlite:////data/signals.db

# CORS - Update after Vercel deployment
CORS_ORIGINS=http://localhost:3000
```

### 4. Get Your API URL
- Railway gives you: `https://your-app.railway.app`
- Test: Visit `https://your-app.railway.app/health`
- ✅ Should return: `{"status":"healthy",...}`

---

## 🌐 Frontend (Vercel) - 5 minutes

### 1. Deploy to Vercel
1. Go to https://vercel.com
2. **New Project** → Import from GitHub
3. **Root Directory:** `apps/web`
4. Framework: Next.js (auto-detected)

### 2. Add Environment Variable

```bash
NEXT_PUBLIC_API_URL=https://your-app.railway.app
```

### 3. Deploy!
- Vercel gives you: `https://your-app.vercel.app`
- Visit your URL - dashboard should load!

---

## 🔗 Final Step - Connect Them (2 minutes)

### Update CORS in Railway

Go back to Railway → Variables:
```bash
CORS_ORIGINS=https://your-app.vercel.app
```

Redeploy Railway (automatic on save).

---

## ✅ Verify Everything Works

1. **Visit your Vercel app:** `https://your-app.vercel.app`
2. **Check Service Status card** - Should show "Active"
3. **Wait ~4 hours** - First signal will be generated
4. **Check Signals List** - Should show signals

---

## 🎯 After MetaAPI Deposit ($10)

Add to Railway variables:
```bash
MT5_CONNECTION_TYPE=metaapi
METAAPI_TOKEN=your_token
METAAPI_ACCOUNT_ID=your_account_id
MAX_RISK_PER_TRADE=0.01
MAX_POSITIONS=2
MAX_DAILY_LOSS=0.03
```

---

## 🆘 Troubleshooting

**Dashboard shows "Service Offline":**
- Check Railway logs for errors
- Verify environment variables are set
- Restart Railway service

**CORS errors:**
- Double-check CORS_ORIGINS matches exact Vercel URL
- Include `https://` (not `http://`)

**No signals appearing:**
- Normal! Signals only generate every 4 hours
- Check Railway logs for "Candle processed"
- Give it 24 hours

---

**That's it! 🎉**

Your app is now live and generating signals automatically!

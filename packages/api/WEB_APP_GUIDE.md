# Gold Trader's Edge - Web App & API Guide

## ✅ What's Been Built

The web app is now **fully integrated** with the real-time signal system! You can view signals, live prices, and service status through a beautiful web dashboard.

### Features Implemented:
- ✅ **REST API** with FastAPI
- ✅ **Signal Endpoints** (list, get by ID, performance stats)
- ✅ **Real-Time Price Endpoint** (current gold price from Yahoo Finance)
- ✅ **Service Status Endpoint** (monitor signal service health)
- ✅ **Web Dashboard** (Beautiful UI with live updates)
- ✅ **Auto-Refresh** (Price updates every 30s, signals every 2 min)

---

## 🚀 Quick Start

### 1. Start the Signal Service (Engine)
First, make sure the signal service is running to generate signals:

```bash
cd /Users/jazzdev/Documents/Programming/the-gold-traders-edge/packages/engine
source venv/bin/activate
python run_signal_service.py
```

This will:
- Connect to Yahoo Finance for live gold prices
- Monitor price every 30 seconds
- Generate signals when 4H candles close
- Save signals to `signals.db`

### 2. Start the API/Web Server
In a new terminal:

```bash
cd /Users/jazzdev/Documents/Programming/the-gold-traders-edge/packages/api
source venv/bin/activate
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000
```

### 3. Open the Dashboard
Open your browser and go to:
```
http://localhost:8000
```

You'll see the beautiful dashboard with:
- 📊 Current gold price (auto-updates every 30s)
- ✅ Service status
- 📈 Total signals generated
- 📋 Latest signals with all details

---

## 📖 API Endpoints

### Health Check
```bash
GET http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "Gold Trader's Edge API",
  "version": "1.0.0"
}
```

### Get Latest Signals
```bash
GET http://localhost:8000/api/signals/?page=1&page_size=20
```

**Query Parameters:**
- `page` - Page number (default: 1)
- `page_size` - Results per page (default: 50, max: 100)
- `status` - Filter by status (pending, active, closed_tp, closed_sl, etc.)
- `direction` - Filter by direction (LONG, SHORT)
- `days` - Get signals from last N days

**Response:**
```json
{
  "total": 10,
  "signals": [
    {
      "id": 1,
      "timestamp": "2025-12-20T16:00:00",
      "symbol": "XAUUSD",
      "timeframe": "4H",
      "strategy_name": "Momentum Equilibrium",
      "direction": "LONG",
      "entry_price": 4387.30,
      "stop_loss": 4310.20,
      "take_profit": 4548.10,
      "confidence": 0.65,
      "status": "pending",
      "risk_reward_ratio": 2.0,
      "risk_pips": 771.0,
      "reward_pips": 1542.0
    }
  ],
  "page": 1,
  "page_size": 20
}
```

### Get Single Signal
```bash
GET http://localhost:8000/api/signals/1
```

**Response:** Same as signal object above

### Get Performance Statistics
```bash
GET http://localhost:8000/api/signals/stats/performance?days=30
```

**Response:**
```json
{
  "total_signals": 10,
  "total_closed": 5,
  "win_count": 4,
  "loss_count": 1,
  "win_rate": 80.0,
  "total_pnl": 1250.50,
  "total_pnl_pct": 12.5,
  "avg_win": 400.0,
  "avg_loss": -150.0,
  "profit_factor": 2.67,
  "largest_win": 550.0,
  "largest_loss": -150.0
}
```

### Get Current Gold Price
```bash
GET http://localhost:8000/api/signals/price/current
```

**Response:**
```json
{
  "symbol": "XAUUSD",
  "price": 4387.30,
  "timestamp": "2025-12-21T00:25:00",
  "change": 2.50,
  "change_pct": 0.057
}
```

### Get Service Status
```bash
GET http://localhost:8000/api/signals/service/status
```

**Response:**
```json
{
  "status": "running",
  "uptime_hours": null,
  "candles_processed": 10,
  "signals_generated": 10,
  "signal_rate": 3.5,
  "last_candle_time": "2025-12-20T16:00:00",
  "next_candle_time": "2025-12-21T04:00:00",
  "current_price": 4387.30,
  "datafeed_type": "yahoo",
  "symbol": "XAUUSD",
  "timeframe": "4H"
}
```

---

## 📊 Dashboard Features

### Live Price Card
- Shows current gold price in real-time
- Updates every 30 seconds
- Displays price change from last update
- Beautiful golden gradient design

### Service Status Card
- Shows if signal service is running
- Displays countdown to next candle close
- Green gradient when running

### Statistics Cards
- Total signals generated
- Signal rate (% of candles)
- Auto-updates every minute

### Signal List
- Shows latest 20 signals
- Color-coded: GREEN for LONG, RED for SHORT
- Displays all important info:
  - Entry price, Stop Loss, Take Profit
  - R:R Ratio
  - Confidence score
  - Signal status
- Click refresh to manually update
- Auto-refreshes every 2 minutes

---

## 🔧 API Structure

```
packages/api/
├── src/
│   ├── main.py                     # FastAPI app + dashboard
│   ├── models/
│   │   ├── __init__.py
│   │   └── signal.py               # Pydantic models
│   ├── routes/
│   │   ├── __init__.py
│   │   └── signals.py              # Signal endpoints
│   └── database/
│       ├── __init__.py
│       └── connection.py           # DB connection
├── static/
│   └── index.html                  # Beautiful dashboard
├── requirements.txt                # Dependencies
└── WEB_APP_GUIDE.md               # This file
```

---

## 🎨 Dashboard Design

The dashboard features:
- **Modern gradient design** (Purple/blue background)
- **Clean white cards** with subtle shadows
- **Responsive grid layout** (works on mobile)
- **Auto-refreshing data** (no manual refresh needed)
- **Color-coded signals** (green = LONG, red = SHORT)
- **Professional typography** (System fonts)
- **Smooth animations** on hover

---

## 🔗 Integration with Engine

The API connects directly to the engine's `signals.db` database:

```
packages/
├── engine/
│   ├── signals.db              ← Engine writes signals here
│   ├── run_signal_service.py   ← Generates signals
│   └── src/...
└── api/
    └── src/database/
        └── connection.py        ← API reads from same DB
```

This means:
1. ✅ No need for separate databases
2. ✅ Real-time sync (signals appear immediately)
3. ✅ Single source of truth
4. ✅ Simple deployment

---

## 🧪 Testing the API

### Test Health
```bash
curl http://localhost:8000/health
```

### Test Signals Endpoint
```bash
curl http://localhost:8000/api/signals/?page_size=5
```

### Test Price Endpoint
```bash
curl http://localhost:8000/api/signals/price/current
```

### Test Service Status
```bash
curl http://localhost:8000/api/signals/service/status
```

### View API Docs
FastAPI provides automatic interactive documentation:
```
http://localhost:8000/docs         # Swagger UI
http://localhost:8000/redoc        # ReDoc
```

---

## 📱 Mobile Support

The dashboard is fully responsive:
- Cards stack vertically on mobile
- Touch-friendly buttons
- Optimized font sizes
- Swipe-friendly scrolling

---

## 🚨 Troubleshooting

### "No signals showing"
**Solution:** Make sure the signal service is running:
```bash
cd packages/engine
python run_signal_service.py
```

### "Price not updating"
**Solution:** Check your internet connection. The API fetches prices from Yahoo Finance.

### "Port 8000 already in use"
**Solution:** Either kill the existing process or use a different port:
```bash
# Use port 8001 instead
python -m uvicorn src.main:app --host 0.0.0.0 --port 8001
```

### "Database not found"
**Solution:** Run the signal service at least once to create the database:
```bash
cd packages/engine
python run_signal_service.py --test 1
```

---

## 🎯 Next Steps

### Phase 2 Enhancements (Optional):
1. **WebSocket Support** - Real-time push notifications
2. **User Authentication** - JWT-based login
3. **Trade Execution** - MT5 integration via API
4. **Performance Charts** - Visualize win rate, P&L
5. **Telegram Integration** - Push signals to Telegram

---

## 📊 Production Deployment

For production deployment:

1. **Use Production Server:**
```bash
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
```

2. **Enable HTTPS** (use reverse proxy like Nginx)

3. **Update CORS Settings** in `src/main.py`:
```python
allow_origins=["https://yourdomain.com"]  # Replace wildcard
```

4. **Use Environment Variables** for configuration

5. **Set up Process Manager** (PM2, systemd, or supervisor)

---

## ✅ Summary

You now have a complete web application that:
- ✅ Displays real-time signals from the engine
- ✅ Shows live gold prices (updates every 30s)
- ✅ Monitors service health
- ✅ Provides REST API for external integrations
- ✅ Works on desktop and mobile
- ✅ Auto-refreshes data
- ✅ Beautiful, professional design

**To use it:**
1. Start signal service: `python run_signal_service.py`
2. Start web server: `python -m uvicorn src.main:app`
3. Open browser: `http://localhost:8000`

That's it! You're running a professional gold trading signal platform! 🎉

---

*Last Updated: December 21, 2025*
*Status: ✅ COMPLETE & WORKING*

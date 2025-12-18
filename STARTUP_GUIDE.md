# 🚀 The Gold Trader's Edge - Complete Startup Guide

## Quick Start (2 Steps)

### 1. Start the API Server (Backend)

```bash
cd packages/engine
./start_api.sh
```

The API will start on **http://localhost:8000**
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### 2. Start the Web Dashboard (Frontend)

```bash
cd apps/web
npm install  # First time only
npm run dev
```

The web app will start on **http://localhost:3000**

---

## What You'll See

### Web Dashboard (http://localhost:3000)

Your browser will show:

1. **Performance Stats Cards**
   - Total Return: +203.66%
   - Win Rate: 55.26%
   - Profit Factor: 1.80
   - Sharpe Ratio: 4.23
   - And more metrics!

2. **Rule Performance Chart**
   - Visual bar chart showing P&L by rule
   - Interactive tooltips with details
   - Color-coded (green = profit, red = loss)

3. **System Info**
   - Active trading rules
   - API status indicator
   - Last update time
   - Timeframe selector (4H/Daily)

---

## System Architecture

```
┌─────────────────────────────────────────┐
│   Web Dashboard (Next.js)               │
│   http://localhost:3000                 │
│   - Performance visualizations          │
│   - Interactive charts                  │
│   - Real-time updates                   │
└────────────┬────────────────────────────┘
             │
             │ HTTP Requests
             ▼
┌─────────────────────────────────────────┐
│   FastAPI Backend                       │
│   http://localhost:8000                 │
│   - Trading signals generation          │
│   - Performance analytics               │
│   - Market data endpoints               │
└────────────┬────────────────────────────┘
             │
             │ Loads data from
             ▼
┌─────────────────────────────────────────┐
│   Real XAUUSD Data                      │
│   packages/engine/data/processed/       │
│   - 4H data: 3,100 candles             │
│   - Daily data: 1,255 candles          │
└─────────────────────────────────────────┘
```

---

## Project Structure

```
the-gold-traders-edge/
├── packages/
│   └── engine/                 # Python backend & strategy
│       ├── api/               # FastAPI application
│       ├── src/               # Trading strategy engine
│       ├── data/              # Real market data
│       ├── analysis/          # Performance charts
│       ├── start_api.sh       # API startup script ⭐
│       ├── fetch_real_data.py # Data fetcher
│       └── run_backtest.py    # Backtest runner
│
└── apps/
    └── web/                   # Next.js web dashboard
        ├── app/               # Next.js pages
        ├── components/        # React components
        ├── lib/               # API client & utils
        └── package.json
```

---

## Available Commands

### Backend (API)

```bash
cd packages/engine

# Start API (recommended)
./start_api.sh

# Or start manually
source venv/bin/activate
python3 -m uvicorn api.main:app --reload

# Fetch latest data
python3 fetch_real_data.py --timeframe 4h --years 2

# Run backtest
python3 run_backtest.py --rules 1,2,5,6

# Generate analysis
python3 analyze_performance.py --timeframe 4h --rules 1,2,5,6
```

### Frontend (Web Dashboard)

```bash
cd apps/web

# Development
npm run dev          # Start dev server
npm run build        # Build for production
npm start            # Start production server

# Utilities
npm run lint         # Run linter
```

---

## API Endpoints Reference

All endpoints are available at: http://localhost:8000/docs

### Analytics
- `GET /v1/analytics/summary` - Performance summary
  ```bash
  curl "http://localhost:8000/v1/analytics/summary?timeframe=4h&rules=1,2,5,6"
  ```

- `GET /v1/analytics/by-rule` - Rule breakdown
  ```bash
  curl "http://localhost:8000/v1/analytics/by-rule?timeframe=4h&rules=1,2,5,6"
  ```

### Market Data
- `GET /v1/market/ohlcv` - Price data
  ```bash
  curl "http://localhost:8000/v1/market/ohlcv?timeframe=4h&limit=100"
  ```

- `GET /v1/market/indicators` - Technical indicators
  ```bash
  curl "http://localhost:8000/v1/market/indicators?timeframe=4h"
  ```

### Signals
- `GET /v1/signals/latest` - Current signals
  ```bash
  curl "http://localhost:8000/v1/signals/latest?timeframe=4h&rules=1,2,5,6"
  ```

---

## Troubleshooting

### API Won't Start

**Error**: `ModuleNotFoundError: No module named 'fastapi'`

**Solution**:
```bash
cd packages/engine
source venv/bin/activate
pip install -r requirements.txt
```

---

### Web App Shows "API Connection Error"

**Cause**: Backend API is not running

**Solution**:
```bash
# In one terminal
cd packages/engine
./start_api.sh

# Verify API is running
curl http://localhost:8000/health
```

---

### Port Already in Use

**Error**: `Address already in use: 8000` or `3000`

**Solution**:
```bash
# Find and kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Find and kill process on port 3000
lsof -ti:3000 | xargs kill -9
```

---

### No Data Available

**Error**: "No data available for timeframe 4h"

**Solution**:
```bash
cd packages/engine
python3 fetch_real_data.py --timeframe 4h --years 2 --clean
```

---

## Performance Metrics Explained

### Total Return
**What it is**: Overall profit/loss percentage
**Current**: +203.66% (4H) | +67.62% (Daily)
**Good**: >50% | **Excellent**: >100%

### Win Rate
**What it is**: Percentage of profitable trades
**Current**: 55.26% (4H) | 57.63% (Daily)
**Good**: >50% | **Excellent**: >60%

### Profit Factor
**What it is**: Gross profit ÷ Gross loss
**Current**: 1.80 (4H) | 1.98 (Daily)
**Good**: >1.5 | **Excellent**: >2.0

### Sharpe Ratio
**What it is**: Risk-adjusted returns
**Current**: 4.23 (4H) | 5.13 (Daily)
**Good**: >2.0 | **Excellent**: >3.0

### Max Drawdown
**What it is**: Largest peak-to-trough decline
**Current**: 12.22% (4H) | 11.72% (Daily)
**Good**: <20% | **Excellent**: <15%

---

## Next Steps

### Option A: Deploy to Production
- Containerize with Docker
- Deploy to cloud (AWS/GCP/Azure)
- Add authentication
- Setup monitoring

### Option B: Enhance Features
- Add real-time WebSocket updates
- Implement user authentication
- Add email/SMS alerts
- Create mobile app

### Option C: Paper Trading
- Connect to live data feed
- Test with real-time data
- Track performance before going live

---

## Support & Documentation

- **API Docs**: http://localhost:8000/docs
- **Project README**: See `README.md` in root
- **Engine Docs**: `packages/engine/PROJECT_SUMMARY.md`
- **Web Docs**: `apps/web/README.md`

---

## Tech Stack Summary

| Component | Technology |
|-----------|-----------|
| Backend Framework | FastAPI (Python) |
| Frontend Framework | Next.js 15 |
| Language (Backend) | Python 3.11+ |
| Language (Frontend) | TypeScript |
| Styling | Tailwind CSS V4 |
| Charts | Recharts |
| Data Analysis | Pandas, NumPy |
| API Client | Axios |
| Server | Uvicorn (ASGI) |

---

**Built with ❤️ using Claude Code**

For questions or issues, check the documentation or create an issue on GitHub.

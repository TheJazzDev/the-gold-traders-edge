# The Gold Trader's Edge

A professional forex signal application focused on gold (XAUUSD) trading with real-time signals, backtesting, and automated trade execution.

## 🎯 Vision

Provide retail traders with institutional-grade gold trading signals based on proven technical patterns, delivered instantly to their mobile devices with one-tap trade execution.

## 📦 Project Structure

```
the-gold-traders-edge/
│
├── apps/
│   └── mobile/              # React Native mobile app
│       └── src/             # Push notifications, signal display, MT5 connection
│
├── packages/
│   ├── engine/              # 🧠 Core trading engine (Python)
│   │   ├── src/
│   │   │   ├── data/        # XAUUSD data fetching & processing
│   │   │   ├── analysis/    # Technical analysis (Fib, swings, trends)
│   │   │   ├── backtesting/ # Strategy backtesting framework
│   │   │   └── signals/     # Signal generation (5 gold rules)
│   │   └── tests/
│   │
│   ├── api/                 # 🌐 Backend API (FastAPI)
│   │   └── src/             # REST endpoints, WebSocket, auth
│   │
│   └── mt5-bridge/          # 🔌 MetaTrader 5 integration
│       └── src/             # Trade execution, account sync
│
├── docs/                    # Documentation
├── .github/workflows/       # CI/CD pipelines
└── docker-compose.yml       # Local development setup
```

## 🚀 Features

### Phase 1: Backtesting Engine ✅
- [x] Historical data loading (Yahoo Finance, HistData, CSV)
- [x] Technical analysis (Fibonacci, swing detection, trend analysis)
- [x] Backtesting framework with performance metrics
- [ ] 5 gold trading rules implementation

### Phase 2: Backend API 🔄
- [ ] FastAPI REST endpoints
- [ ] WebSocket for real-time signals
- [ ] User authentication (JWT)
- [ ] Subscription management

### Phase 3: Mobile App 📱
- [ ] React Native app
- [ ] Push notifications for signals
- [ ] Signal history & performance
- [ ] MT5 account linking

### Phase 4: MT5 Integration 🤖
- [ ] MetaAPI/MT5 bridge
- [ ] One-tap trade execution
- [ ] Auto SL/TP placement
- [ ] Position management

## 🏗️ Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- Docker (optional)

### Engine Development

```bash
cd packages/engine
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run backtest
python -m src.signals.gold_strategy
```

### Mobile Development

```bash
cd apps/mobile
npm install
npx react-native run-android  # or run-ios
```

## 📊 Trading Strategy

This system implements **5 core gold trading rules** based on proven XAUUSD patterns:

| Rule | Description | Status |
|------|-------------|--------|
| Rule 1 | Fib 78.6% retracement buy in uptrend | ✅ Templated |
| Rule 2 | TBD | ⏳ Pending |
| Rule 3 | TBD | ⏳ Pending |
| Rule 4 | TBD | ⏳ Pending |
| Rule 5 | TBD | ⏳ Pending |

## 💰 Monetization

- **Free Tier**: Delayed signals, limited history
- **Pro Tier** ($29/mo): Real-time signals, full history
- **Premium Tier** ($79/mo): Auto-execution, priority support

## 📄 License

Proprietary - All rights reserved

## ⚠️ Disclaimer

Trading forex involves significant risk of loss. Past performance does not guarantee future results. This software is for educational purposes only.

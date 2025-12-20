# Real-Time Signal System - Implementation Plan

**Goal:** Generate live trading signals from Momentum Equilibrium strategy, paper trade on demo account for 30 days, and deliver signals via Telegram bot.

**Strategy:** Momentum Equilibrium ONLY (74% win rate, 3.31 PF, $21K profit on backtest)

**Timeline:** 4-6 weeks to production

---

## 📋 Phase 1: Real-Time Signal Generation (Week 1-2)

### 1.1 Market Data Pipeline
- [ ] Set up real-time XAUUSD 4H data feed
  - [ ] Option A: Yahoo Finance (free, 15min delay acceptable for 4H)
  - [ ] Option B: Alpha Vantage API (free tier)
  - [ ] Option C: MetaTrader 5 Python integration (real-time)
  - **Decision:** Use MT5 Python for real-time data
- [ ] Create data fetcher that runs every candle close (4H intervals)
- [ ] Store last 200 candles in memory for indicator calculation
- [ ] Add error handling and retry logic
- [ ] Test data pipeline for 24 hours continuously

**File:** `packages/engine/src/data/realtime_feed.py`

```python
class RealtimeDataFeed:
    def __init__(self, symbol="XAUUSD", timeframe="4H"):
        # Initialize MT5 connection
        pass

    def get_latest_candles(self, count=200):
        # Fetch latest candles
        pass

    def wait_for_new_candle(self):
        # Wait until next 4H candle closes
        pass
```

### 1.2 Signal Generator Service
- [ ] Create signal generation service that runs continuously
- [ ] Load Momentum Equilibrium strategy ONLY
- [ ] Check for new signals every 4 hours (on candle close)
- [ ] Generate signal with all required fields:
  - Entry price (market execution or limit order)
  - Stop loss (ATR-based)
  - Take profit (2:1 R:R default)
  - Direction (LONG/SHORT)
  - Confidence score
  - Timestamp
- [ ] Validate signal before publishing (sanity checks)
- [ ] Add logging for all signal generation events

**File:** `packages/engine/src/signals/realtime_generator.py`

```python
class SignalGenerator:
    def __init__(self):
        self.strategy = GoldStrategy()
        # Enable ONLY momentum_equilibrium
        self.strategy.rules_enabled = {
            'momentum_equilibrium': True,
            # All others disabled
        }

    def generate_signal(self, df):
        # Run strategy on latest data
        # Return signal or None
        pass

    def validate_signal(self, signal):
        # Sanity checks: SL not too wide, TP reasonable, etc.
        pass
```

### 1.3 Signal Storage (Database)
- [ ] Set up PostgreSQL database (or SQLite for MVP)
- [ ] Create signals table schema:
  ```sql
  CREATE TABLE signals (
      id UUID PRIMARY KEY,
      timestamp TIMESTAMP NOT NULL,
      symbol VARCHAR(10) DEFAULT 'XAUUSD',
      strategy VARCHAR(50) DEFAULT 'Momentum Equilibrium',
      direction VARCHAR(5) NOT NULL, -- LONG or SHORT
      entry_price DECIMAL(10,2) NOT NULL,
      stop_loss DECIMAL(10,2) NOT NULL,
      take_profit DECIMAL(10,2) NOT NULL,
      confidence DECIMAL(3,2),
      status VARCHAR(20) DEFAULT 'pending', -- pending, active, closed
      actual_entry DECIMAL(10,2),
      actual_exit DECIMAL(10,2),
      actual_pnl DECIMAL(10,2),
      closed_at TIMESTAMP,
      notes TEXT,
      created_at TIMESTAMP DEFAULT NOW()
  );
  ```
- [ ] Create signal repository class for CRUD operations
- [ ] Add indices on timestamp and status

**File:** `packages/engine/src/database/signal_repository.py`

### 1.4 Signal Publishing System
- [ ] Create event bus for signal publishing (simple pub/sub)
- [ ] Publishers:
  - [ ] Database (save signal)
  - [ ] Telegram bot (send notification)
  - [ ] Demo trading system (execute trade)
  - [ ] Web API (update UI)
- [ ] Add error handling per publisher (one failure shouldn't break others)

**File:** `packages/engine/src/signals/signal_publisher.py`

```python
class SignalPublisher:
    def __init__(self):
        self.subscribers = []

    def subscribe(self, callback):
        self.subscribers.append(callback)

    def publish(self, signal):
        for subscriber in self.subscribers:
            try:
                subscriber(signal)
            except Exception as e:
                log.error(f"Publisher failed: {e}")
```

### 1.5 Main Service Runner
- [ ] Create main service that orchestrates everything
- [ ] Runs as daemon/background process
- [ ] Health checks every 5 minutes
- [ ] Graceful shutdown handling
- [ ] Restart on failure with exponential backoff

**File:** `packages/engine/src/services/signal_service.py`

```python
class SignalService:
    def run(self):
        while True:
            # Wait for new candle
            # Fetch latest data
            # Generate signal
            # Publish if signal found
            # Sleep until next candle
            pass
```

---

## 📋 Phase 2: Demo Account Paper Trading (Week 2-3)

### 2.1 MetaTrader 5 Integration
- [ ] Install MetaTrader5 Python package
- [ ] Set up demo account (XM, FTMO, or similar)
- [ ] Test connection and authentication
- [ ] Implement trade execution functions:
  - [ ] Place market order
  - [ ] Place limit order
  - [ ] Set stop loss
  - [ ] Set take profit
  - [ ] Close position
- [ ] Add error handling for failed orders

**File:** `packages/engine/src/trading/mt5_client.py`

```python
class MT5Client:
    def __init__(self, account, password, server):
        # Initialize MT5
        pass

    def place_order(self, signal):
        # Execute trade based on signal
        # Return order ticket number
        pass

    def get_position_status(self, ticket):
        # Check if position still open
        pass

    def close_position(self, ticket):
        # Close the position
        pass
```

### 2.2 Trade Manager
- [ ] Create trade manager that listens to signals
- [ ] Execute trades on demo account when signal published
- [ ] Track open positions
- [ ] Monitor for SL/TP hits
- [ ] Update database when trade closes
- [ ] Calculate actual P&L
- [ ] Handle partial fills, slippage

**File:** `packages/engine/src/trading/trade_manager.py`

### 2.3 Performance Tracker
- [ ] Real-time performance dashboard data
- [ ] Track live vs backtest performance:
  - [ ] Win rate (live vs 74% backtest)
  - [ ] Profit factor (live vs 3.31 backtest)
  - [ ] Average win/loss
  - [ ] Max drawdown
  - [ ] Sharpe ratio
- [ ] Alert if live performance degrades significantly
- [ ] Daily performance report

**File:** `packages/engine/src/analytics/performance_tracker.py`

### 2.4 30-Day Validation Period
- [ ] Start paper trading on demo account
- [ ] Track all signals and outcomes
- [ ] Compare to backtest expectations
- [ ] Decision criteria after 30 days:
  - ✅ **GO LIVE:** If win rate > 60% and PF > 2.0
  - ⚠️  **CONTINUE TESTING:** If win rate 50-60% and PF 1.5-2.0
  - ❌ **STOP:** If win rate < 50% or PF < 1.5

---

## 📋 Phase 3: Telegram Bot Integration (Week 3-4)

### 3.1 Telegram Bot Setup
- [ ] Create Telegram bot via @BotFather
- [ ] Get bot token
- [ ] Install python-telegram-bot library
- [ ] Test basic message sending

**File:** `packages/engine/src/notifications/telegram_bot.py`

### 3.2 Signal Notifications
- [ ] Format signal message template:
  ```
  🥇 NEW GOLD SIGNAL - Momentum Equilibrium

  📊 XAUUSD | 4H Timeframe
  🎯 Direction: LONG
  💰 Entry: 2,650.50 (Market Execution)
  🛑 Stop Loss: 2,635.20 (-15.30 pips)
  ✅ Take Profit: 2,681.10 (+30.60 pips)
  📈 Risk/Reward: 2.0
  💪 Confidence: 82%

  ⏰ Generated: 2025-12-20 16:00 UTC

  ⚠️ This is a demo signal - paper trading only
  ```
- [ ] Send notification when new signal generated
- [ ] Include chart image (optional but nice)
- [ ] Add buttons for:
  - [ ] "Details" - Full signal info
  - [ ] "Performance" - Current stats

### 3.3 Trade Updates
- [ ] Send updates when trade closes:
  ```
  ✅ SIGNAL CLOSED - Profit

  📊 XAUUSD Momentum Equilibrium
  Entry: 2,650.50
  Exit: 2,681.10
  P&L: +$306.00 (+1.15%)
  Duration: 16 hours

  📈 Current Stats (Last 30 days):
  Win Rate: 71% (17W / 7L)
  Profit Factor: 2.89
  Total P&L: +$4,230
  ```
- [ ] Different message for losing trades
- [ ] Weekly summary report

### 3.4 Bot Commands
- [ ] `/start` - Subscribe to signals
- [ ] `/stop` - Unsubscribe from signals
- [ ] `/stats` - View current performance
- [ ] `/signals` - View recent signals (last 10)
- [ ] `/help` - Show available commands

---

## 📋 Phase 4: Web Dashboard (Week 4-5) - Optional

### 4.1 Real-Time Signals Page
- [ ] Create new page: `/signals/live`
- [ ] Show current open signals
- [ ] Show signal history (last 30 days)
- [ ] Real-time updates via WebSocket
- [ ] Signal performance chart

### 4.2 Performance Dashboard
- [ ] Live vs backtest comparison chart
- [ ] Win rate trending over time
- [ ] P&L curve
- [ ] Current drawdown
- [ ] Best/worst trades

### 4.3 Subscription Management
- [ ] Users can subscribe to Telegram notifications
- [ ] Email notifications (optional)
- [ ] Webhook integration for third-party apps

---

## 📋 Phase 5: Monitoring & Reliability (Week 5-6)

### 5.1 Health Monitoring
- [ ] Service uptime monitoring
- [ ] Alert if service down > 5 minutes
- [ ] Database health checks
- [ ] MT5 connection health
- [ ] Disk space monitoring

### 5.2 Logging & Debugging
- [ ] Structured logging (JSON format)
- [ ] Log levels: DEBUG, INFO, WARNING, ERROR
- [ ] Log rotation (max 100MB per file)
- [ ] Centralized logging (optional: ELK stack)

### 5.3 Error Alerting
- [ ] Critical errors send alert to Telegram
- [ ] Email alerts for system failures
- [ ] Automatic restart on crash

### 5.4 Backup & Recovery
- [ ] Daily database backups
- [ ] Signal data export to CSV
- [ ] Configuration backup
- [ ] Recovery plan documentation

---

## 🎯 Success Criteria

### Minimum Viable Product (MVP)
- ✅ Generate signals every 4 hours automatically
- ✅ Execute trades on demo MT5 account
- ✅ Send Telegram notifications instantly
- ✅ Track performance in database
- ✅ Run continuously for 30 days without manual intervention

### 30-Day Validation Metrics
- **Target:** Win rate > 60%, Profit factor > 2.0
- **Acceptable:** Win rate 55-60%, Profit factor 1.8-2.0
- **Failed:** Win rate < 55%, Profit factor < 1.8

### Go-Live Decision Criteria
After 30 days of paper trading:

✅ **APPROVED FOR LIVE TRADING:**
- Win rate within 10% of backtest (>66%)
- Profit factor within 20% of backtest (>2.6)
- Max drawdown < 15%
- No critical bugs or failures
- At least 20 signals executed

⚠️ **NEEDS MORE TIME:**
- Win rate 55-66%
- Profit factor 2.0-2.6
- Continue for another 30 days

❌ **STRATEGY FAILED:**
- Win rate < 55%
- Profit factor < 2.0
- Back to backtesting and strategy review

---

## 📊 Tech Stack

### Core Services
- **Language:** Python 3.10+
- **Framework:** FastAPI (REST API)
- **Database:** PostgreSQL (or SQLite for MVP)
- **Real-time Data:** MetaTrader 5 Python
- **Trading:** MetaTrader 5 Demo Account

### Integrations
- **Telegram:** python-telegram-bot
- **Notifications:** Telegram Bot API
- **Monitoring:** Basic health checks (expand later)

### Deployment
- **Development:** Local machine / Docker
- **Production:** VPS (DigitalOcean, AWS, etc.)
- **Uptime:** Target 99.5% (acceptable for beta)

---

## 📁 Project Structure

```
packages/engine/
├── src/
│   ├── data/
│   │   ├── realtime_feed.py          # Real-time data fetcher
│   │   └── data_validator.py         # Data quality checks
│   ├── signals/
│   │   ├── realtime_generator.py     # Signal generation
│   │   ├── signal_publisher.py       # Event pub/sub
│   │   └── signal_validator.py       # Signal sanity checks
│   ├── trading/
│   │   ├── mt5_client.py             # MT5 integration
│   │   ├── trade_manager.py          # Trade execution
│   │   └── position_tracker.py       # Open position monitoring
│   ├── database/
│   │   ├── models.py                 # SQLAlchemy models
│   │   ├── signal_repository.py      # Signal CRUD
│   │   └── migrations/               # Database migrations
│   ├── notifications/
│   │   ├── telegram_bot.py           # Telegram integration
│   │   └── message_formatter.py      # Message templates
│   ├── analytics/
│   │   └── performance_tracker.py    # Live performance
│   └── services/
│       ├── signal_service.py         # Main orchestrator
│       └── health_monitor.py         # Health checks
├── config/
│   ├── production.yaml               # Production config
│   └── demo.yaml                     # Demo trading config
├── scripts/
│   ├── start_signal_service.sh       # Service starter
│   └── setup_database.py             # DB initialization
├── tests/
│   └── test_realtime_signals.py      # Unit tests
└── REAL_TIME_SIGNALS_PLAN.md         # This file
```

---

## ⚠️ Critical Warnings

### 1. Data Feed Reliability
- 4H candles must be reliable
- Missing data = missed signals
- Solution: Backfill missing candles from multiple sources

### 2. Signal Validation
- Don't send signals with impossible SL/TP
- Validate entry price vs current market
- Alert if signal logic seems broken

### 3. Demo vs Live
- Demo account slippage != live slippage
- Demo fills may be optimistic
- Expect 10-20% performance degradation in live

### 4. Overfitting Risk
- 74% win rate is suspiciously high
- Could be curve-fitted to historical data
- Paper trading will reveal truth
- BE PREPARED for win rate to drop to 55-65% live

### 5. Market Changes
- Strategy works on 2023-2025 data
- Markets change, strategies degrade
- Monitor performance weekly
- Kill switch if 3 consecutive weeks of losses

---

## 🚀 Next Steps

1. **Create Development Environment**
   - Set up Python virtual environment
   - Install MetaTrader 5
   - Open demo account

2. **Build Phase 1 (Week 1)**
   - Real-time data feed
   - Signal generator
   - Basic database

3. **Test Locally (Week 2)**
   - Run service for 1 week
   - Monitor for bugs
   - Validate signals manually

4. **Deploy & Paper Trade (Week 3-8)**
   - Deploy to VPS
   - Connect to demo account
   - Send Telegram notifications
   - Track for 30 days

5. **Go/No-Go Decision (Week 9)**
   - Review 30-day results
   - Decide: Live trading or more testing

---

## 📝 Current Status

- [x] Strategy validated (Momentum Equilibrium)
- [x] Backtest completed (74% win rate, 3.31 PF)
- [x] Codebase cleaned up
- [ ] Real-time signal system (NOT STARTED)
- [ ] Demo trading (NOT STARTED)
- [ ] Telegram bot (NOT STARTED)
- [ ] 30-day validation (NOT STARTED)

**Start Date:** TBD
**Target Go-Live:** TBD + 9 weeks (if validation passes)

---

*Last Updated: 2025-12-20*
*Strategy: Momentum Equilibrium ONLY*
*Next Milestone: Phase 1 - Real-Time Signal Generation*

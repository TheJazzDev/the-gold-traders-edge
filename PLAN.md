# The Gold Trader's Edge — Project Plan

> **Mission**: Build a professional-grade XAUUSD trading signal system that delivers high-probability setups with real-time monitoring and smart notifications.

---

## Vision

A focused, Gold-only trading assistant that:
- Monitors XAUUSD 24/5 in real-time
- Detects high-probability trade setups automatically
- Alerts you before opportunities slip away
- Tracks signal performance to continuously improve
- Incorporates your personal trading insights over time

**Target**: 70%+ win rate with minimum 1:2 risk-reward ratio

---

## Phase Breakdown

### Phase 1: Foundation ✅ COMPLETE
> Core app with chart, basic analysis, and browser notifications

**Delivered:**
- [x] Next.js 14 project setup with TypeScript
- [x] TradingView Lightweight Charts integration
- [x] Multi-timeframe support (1m to 1W)
- [x] Technical indicators (RSI, MACD, EMA, ATR, Bollinger Bands)
- [x] Support/Resistance detection
- [x] Pattern recognition (triangles, engulfing)
- [x] Signal generation with confidence scoring
- [x] Browser push notifications
- [x] Zustand state management with persistence
- [x] Responsive dashboard UI
- [x] Simulated data fallback (works without API)

---

### Phase 2: Real Market Data 🔄 NEXT
> Connect to live XAUUSD price feeds

**Goals:**
- [ ] Finnhub API integration for real-time quotes
- [ ] WebSocket connection for live price streaming
- [ ] Historical data fetching for backtesting
- [ ] Price alert system (custom price levels)
- [ ] Connection status indicator with auto-reconnect
- [ ] Rate limiting and error handling

**API Options:**
| Provider | Free Tier | WebSocket | Notes |
|----------|-----------|-----------|-------|
| Finnhub | 60 calls/min | Yes | Good for forex |
| Twelve Data | 800/day | Paid only | Better candle data |
| OANDA | Unlimited* | Yes | Requires trading account |
| MetaAPI | 100 calls/day | Yes | MT4/MT5 bridge |

---

### Phase 3: Signal Tracking Engine
> Monitor active signals and update status automatically

**Goals:**
- [ ] Real-time signal status monitoring
- [ ] Auto-detect when price enters entry zone → "ACTIVE"
- [ ] Auto-detect TP1/TP2 hits → Update status + calculate P&L
- [ ] Auto-detect SL hit → Close signal + log loss
- [ ] Partial close tracking (50% at TP1, 50% at TP2)
- [ ] Signal expiration logic (cancel if not triggered in X hours)
- [ ] Trade journal with entry/exit screenshots

---

### Phase 4: Telegram Bot Integration
> Get alerts on your phone anywhere

**Goals:**
- [ ] Telegram bot setup (@GoldTradersEdgeBot)
- [ ] Commands: `/status`, `/signals`, `/stats`, `/settings`
- [ ] New signal alerts with formatted message
- [ ] Signal update notifications (TP hit, SL hit)
- [ ] Daily summary report
- [ ] User authentication (link Telegram to account)

**Message Format:**
```
🟢 NEW BUY SIGNAL — XAUUSD

Entry: $2,645 - $2,650
Stop Loss: $2,625 (-20 pips)
Take Profit 1: $2,680 (+30 pips)
Take Profit 2: $2,710 (+60 pips)

Risk:Reward: 1:2.5
Confidence: 78%
Pattern: Ascending Triangle

⏰ Valid for 4 hours
```

---

### Phase 5: Email Notifications
> Backup alerts via email

**Goals:**
- [ ] Resend API integration
- [ ] HTML email templates (branded, mobile-friendly)
- [ ] New signal emails
- [ ] Daily/weekly performance reports
- [ ] Configurable email frequency
- [ ] Unsubscribe handling

---

### Phase 6: Advanced Analytics Dashboard
> Track performance and identify strengths

**Goals:**
- [ ] Performance metrics dashboard
  - Win rate by timeframe
  - Win rate by pattern type
  - Win rate by session (London, NY, Asian)
  - Average R:R achieved
  - Profit factor
  - Maximum drawdown
- [ ] Equity curve visualization
- [ ] Monthly/weekly P&L breakdown
- [ ] Best/worst trade analysis
- [ ] Streak tracking (consecutive wins/losses)
- [ ] Export data to CSV/Excel

---

### Phase 7: Custom Strategy Builder
> Add your personal Gold trading insights

**Goals:**
- [ ] Custom indicator integration
- [ ] User-defined entry rules
- [ ] User-defined exit rules
- [ ] Combine multiple conditions (AND/OR logic)
- [ ] Strategy templates (save/load)
- [ ] A/B test strategies against each other

**Your Inputs to Add:**
- Key support/resistance levels you've identified
- Specific patterns you've found work well
- Time-of-day filters (e.g., only trade London session)
- News event filters
- Custom confluence requirements

---

### Phase 8: Backtesting Engine
> Test strategies against historical data

**Goals:**
- [ ] Historical data storage (1+ year of candles)
- [ ] Backtest runner with progress indicator
- [ ] Configurable date ranges
- [ ] Performance metrics calculation
- [ ] Trade-by-trade breakdown
- [ ] Optimization mode (test parameter ranges)
- [ ] Walk-forward analysis
- [ ] Monte Carlo simulation

---

### Phase 9: Risk Management Module
> Protect your capital

**Goals:**
- [ ] Position size calculator
- [ ] Account balance tracking
- [ ] Maximum daily loss limit
- [ ] Maximum open positions limit
- [ ] Correlation warnings (if adding other pairs later)
- [ ] Risk per trade enforcement
- [ ] Drawdown alerts

---

### Phase 10: Mobile PWA
> Full mobile experience

**Goals:**
- [ ] Progressive Web App setup
- [ ] Offline support (cached data)
- [ ] Add to home screen
- [ ] Native-like navigation
- [ ] Touch-optimized charts
- [ ] Quick actions (close signal, adjust TP/SL)

---

## Technical Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      FRONTEND (Next.js)                      │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────────┐ │
│  │Dashboard│  │ Signals │  │Analytics│  │ Strategy Builder│ │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────────┬────────┘ │
│       └────────────┴───────────┴─────────────────┘          │
│                            │                                 │
│                     ┌──────┴──────┐                         │
│                     │ Zustand Store│                         │
│                     └──────┬──────┘                         │
└────────────────────────────┼────────────────────────────────┘
                             │
┌────────────────────────────┼────────────────────────────────┐
│                      BACKEND (API Routes)                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────────┐  │
│  │ Market   │  │ Analysis │  │ Signals  │  │Notifications│  │
│  │ Data API │  │ Engine   │  │ Manager  │  │   Service   │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬──────┘  │
└───────┼─────────────┼─────────────┼───────────────┼─────────┘
        │             │             │               │
        ▼             │             ▼               ▼
┌───────────────┐     │     ┌─────────────┐  ┌───────────┐
│ Finnhub/OANDA │     │     │  Database   │  │ Telegram  │
│   WebSocket   │     │     │ (Supabase)  │  │   Bot     │
└───────────────┘     │     └─────────────┘  └───────────┘
                      │
              ┌───────┴───────┐
              │   Indicators  │
              │ RSI,MACD,EMA  │
              │ ATR,BB,S&R    │
              │ Patterns      │
              └───────────────┘
```

---

## Database Schema (Future)

```sql
-- Users
users (id, email, telegram_id, settings, created_at)

-- Signals
signals (
  id, user_id, direction, status,
  entry_low, entry_high, stop_loss,
  tp1, tp2, tp3,
  confidence, timeframe, patterns,
  triggered_at, closed_at, closed_price,
  pnl_pips, pnl_percent,
  created_at, updated_at
)

-- Price History
candles (symbol, timeframe, time, open, high, low, close, volume)

-- Notifications
notifications (id, user_id, type, title, message, read, created_at)

-- Strategies (future)
strategies (id, user_id, name, rules, is_active, created_at)
```

---

## Success Metrics

| Metric | Target | How We'll Measure |
|--------|--------|-------------------|
| Win Rate | 70%+ | Closed signals with TP hit / Total closed |
| Avg R:R | 1:2+ | Average reward achieved vs risk taken |
| Signal Frequency | 3-5/week | Quality over quantity |
| False Signals | <20% | Signals cancelled or expired |
| Notification Latency | <30s | Time from detection to alert |
| Uptime | 99.5% | Monitoring via Vercel |

---

## Timeline Estimate

| Phase | Duration | Priority |
|-------|----------|----------|
| Phase 1 | ✅ Done | — |
| Phase 2 | 1 week | 🔴 High |
| Phase 3 | 1 week | 🔴 High |
| Phase 4 | 3-4 days | 🔴 High |
| Phase 5 | 2-3 days | 🟡 Medium |
| Phase 6 | 1 week | 🟡 Medium |
| Phase 7 | 2 weeks | 🟡 Medium |
| Phase 8 | 2 weeks | 🟢 Low |
| Phase 9 | 1 week | 🟡 Medium |
| Phase 10 | 3-4 days | 🟢 Low |

**MVP Complete**: Phases 1-4 (~3 weeks)
**Full Product**: All phases (~10-12 weeks)

---

## Tech Stack Summary

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14, React 18, TypeScript |
| Styling | TailwindCSS, CSS Variables |
| Charts | TradingView Lightweight Charts |
| State | Zustand (client), React Query (server) |
| Database | Supabase (PostgreSQL) |
| Auth | Supabase Auth or NextAuth |
| Notifications | Web Push API, Telegram Bot API, Resend |
| Hosting | Vercel (frontend), Railway (WebSocket server) |
| Monitoring | Vercel Analytics, Sentry |

---

## Notes & Ideas

### Your Custom Findings to Integrate
*(Add your Gold trading insights here as we build)*

- [ ] Key levels:
- [ ] Best trading sessions:
- [ ] Patterns that work:
- [ ] Patterns to avoid:
- [ ] News events impact:
- [ ] Correlation with DXY:

### Future Enhancements
- Multi-pair support (XAGUSD, EURUSD)
- Social features (share signals)
- Copy trading integration
- AI-powered pattern recognition
- Voice alerts
- Apple Watch / WearOS app

---

## Getting Started

```bash
# Clone and install
git clone https://github.com/TheJazzDev/the-gold-traders-edge.git
cd the-gold-traders-edge
npm install

# Set up environment
cp .env.example .env.local
# Add your API keys to .env.local

# Run development server
npm run dev
```

---

*Last Updated: November 27, 2025*
*Version: 0.1.0 (Phase 1 Complete)*
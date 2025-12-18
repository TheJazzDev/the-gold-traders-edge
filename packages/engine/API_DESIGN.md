# Phase 2: Gold Trading Signals API

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     CLIENT APPLICATIONS                      │
│  (Web Dashboard, Mobile App, Trading Terminal, Webhooks)    │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │ HTTPS / WebSocket
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     API GATEWAY / NGINX                      │
│                  (Load Balancing, Rate Limiting)             │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   FASTAPI BACKEND SERVICE                    │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  REST API   │  │  WebSocket   │  │  Background      │  │
│  │  Endpoints  │  │  Real-time   │  │  Tasks (Celery)  │  │
│  └─────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                    ▲              ▲             ▲
                    │              │             │
      ┌─────────────┴──┐    ┌──────┴──────┐    ┌┴───────────┐
      │  Redis Cache   │    │  PostgreSQL │    │ Message    │
      │  (Sessions)    │    │  (Users,    │    │ Queue      │
      │                │    │  Signals)   │    │ (Redis)    │
      └────────────────┘    └─────────────┘    └────────────┘
                    ▲
                    │
      ┌─────────────┴────────────────┐
      │   Gold Strategy Engine       │
      │  (Your existing Python code) │
      │  - Signal Generation         │
      │  - Indicator Calculation     │
      │  - Backtesting               │
      └──────────────────────────────┘
                    ▲
                    │
      ┌─────────────┴────────────┐
      │  Data Sources           │
      │  - Yahoo Finance API    │
      │  - Custom Data Feeds    │
      └─────────────────────────┘
```

## API Specification

### Base URL
```
Production: https://api.goldtradersedge.com/v1
Development: http://localhost:8000/v1
```

### Authentication
- **Method**: JWT (JSON Web Tokens)
- **Header**: `Authorization: Bearer <token>`
- **Token Expiry**: 24 hours (configurable)

---

## REST API Endpoints

### 1. Authentication

#### `POST /auth/register`
Register a new user.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securePassword123",
  "name": "John Doe"
}
```

**Response:**
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "message": "User registered successfully"
}
```

#### `POST /auth/login`
Login and receive JWT token.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securePassword123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

---

### 2. Signals

#### `GET /signals/latest`
Get the latest trading signals for XAUUSD.

**Query Parameters:**
- `timeframe`: `4h` | `1d` (default: `4h`)
- `rules`: Comma-separated rule numbers (e.g., `1,2,5,6`) (default: all enabled)

**Response:**
```json
{
  "timestamp": "2025-12-17T08:00:00Z",
  "symbol": "XAUUSD",
  "timeframe": "4h",
  "current_price": 2034.50,
  "signals": [
    {
      "rule": "Rule6_50_Momentum",
      "signal": "LONG",
      "entry_price": 2034.50,
      "stop_loss": 2020.00,
      "take_profit": 2060.00,
      "confidence": 0.85,
      "risk_reward_ratio": 1.75,
      "generated_at": "2025-12-17T08:00:00Z"
    }
  ],
  "market_context": {
    "trend": "bullish",
    "volatility": "moderate",
    "atr": 15.32
  }
}
```

#### `GET /signals/history`
Get historical signals.

**Query Parameters:**
- `timeframe`: `4h` | `1d` (default: `4h`)
- `start_date`: ISO 8601 date (default: 30 days ago)
- `end_date`: ISO 8601 date (default: now)
- `limit`: Max number of signals (default: 100, max: 1000)

**Response:**
```json
{
  "signals": [
    {
      "id": "signal_uuid",
      "timestamp": "2025-12-16T04:00:00Z",
      "rule": "Rule1_618_Golden",
      "signal": "LONG",
      "entry_price": 2025.00,
      "stop_loss": 2010.00,
      "take_profit": 2055.00,
      "status": "closed",
      "pnl": 250.50,
      "pnl_pct": 1.5
    }
  ],
  "total": 45,
  "page": 1,
  "page_size": 100
}
```

---

### 3. Market Data

#### `GET /market/ohlcv`
Get OHLCV (candlestick) data for XAUUSD.

**Query Parameters:**
- `timeframe`: `1h` | `4h` | `1d`
- `start_date`: ISO 8601 date
- `end_date`: ISO 8601 date
- `limit`: Number of candles (max: 5000)

**Response:**
```json
{
  "symbol": "XAUUSD",
  "timeframe": "4h",
  "candles": [
    {
      "timestamp": "2025-12-17T08:00:00Z",
      "open": 2030.00,
      "high": 2035.50,
      "low": 2028.00,
      "close": 2034.50,
      "volume": 12500
    }
  ]
}
```

#### `GET /market/indicators`
Get technical indicators for current market state.

**Response:**
```json
{
  "timestamp": "2025-12-17T08:00:00Z",
  "price": 2034.50,
  "indicators": {
    "ema_20": 2025.30,
    "ema_50": 2010.50,
    "atr_14": 15.32,
    "rsi_14": 62.5,
    "fibonacci_levels": {
      "0.236": 2020.00,
      "0.382": 2015.00,
      "0.618": 2005.00,
      "0.786": 2000.00
    }
  }
}
```

---

### 4. Performance Analytics

#### `GET /analytics/summary`
Get overall strategy performance summary.

**Query Parameters:**
- `timeframe`: `4h` | `1d`
- `period`: `1w` | `1m` | `3m` | `1y` | `all`

**Response:**
```json
{
  "period": "3m",
  "timeframe": "4h",
  "total_signals": 152,
  "winning_signals": 84,
  "losing_signals": 68,
  "win_rate": 55.26,
  "profit_factor": 1.80,
  "total_return_pct": 203.66,
  "sharpe_ratio": 4.23,
  "max_drawdown_pct": 12.22,
  "avg_win": 544.92,
  "avg_loss": 373.63,
  "best_performing_rule": "Rule1_618_Golden"
}
```

#### `GET /analytics/by-rule`
Get performance breakdown by rule.

**Response:**
```json
{
  "rules": [
    {
      "name": "Rule1_618_Golden",
      "total_signals": 66,
      "win_rate": 59.1,
      "profit_factor": 1.72,
      "net_pnl": 7891.74,
      "avg_return": 119.57
    },
    {
      "name": "Rule6_50_Momentum",
      "total_signals": 26,
      "win_rate": 84.6,
      "profit_factor": 5.30,
      "net_pnl": 7138.45,
      "avg_return": 274.56
    }
  ]
}
```

---

### 5. User Management

#### `GET /user/profile`
Get user profile and subscription info.

**Response:**
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "name": "John Doe",
  "subscription": {
    "plan": "premium",
    "status": "active",
    "expires_at": "2026-01-17T00:00:00Z"
  },
  "preferences": {
    "default_timeframe": "4h",
    "enabled_rules": [1, 2, 5, 6],
    "notifications": {
      "email": true,
      "push": true,
      "webhook_url": "https://example.com/webhook"
    }
  }
}
```

#### `PATCH /user/preferences`
Update user preferences.

**Request:**
```json
{
  "default_timeframe": "1d",
  "enabled_rules": [1, 5, 6],
  "notifications": {
    "email": true,
    "webhook_url": "https://example.com/webhook"
  }
}
```

---

### 6. Backtesting

#### `POST /backtest/run`
Run a custom backtest with user-defined parameters.

**Request:**
```json
{
  "timeframe": "4h",
  "start_date": "2023-01-01",
  "end_date": "2025-12-17",
  "initial_balance": 10000,
  "risk_per_trade": 2.0,
  "rules": [1, 2, 5, 6]
}
```

**Response:**
```json
{
  "backtest_id": "uuid",
  "status": "completed",
  "results": {
    "initial_balance": 10000,
    "final_balance": 30366.19,
    "net_profit": 20366.19,
    "return_pct": 203.66,
    "total_trades": 152,
    "win_rate": 55.26,
    "profit_factor": 1.80,
    "sharpe_ratio": 4.23
  }
}
```

---

## WebSocket API

### Connection
```
wss://api.goldtradersedge.com/v1/ws
```

### Authentication
Send JWT token on connection:
```json
{
  "type": "auth",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### Subscribe to Signals
```json
{
  "type": "subscribe",
  "channel": "signals",
  "params": {
    "timeframe": "4h",
    "rules": [1, 2, 5, 6]
  }
}
```

### Real-time Signal Updates
```json
{
  "type": "signal",
  "timestamp": "2025-12-17T08:00:00Z",
  "data": {
    "rule": "Rule6_50_Momentum",
    "signal": "LONG",
    "entry_price": 2034.50,
    "stop_loss": 2020.00,
    "take_profit": 2060.00,
    "confidence": 0.85
  }
}
```

---

## Technology Stack

### Backend
- **Framework**: FastAPI (Python)
- **ASGI Server**: Uvicorn with Gunicorn
- **Database**: PostgreSQL (User data, signals history)
- **Cache**: Redis (Sessions, rate limiting, real-time data)
- **Task Queue**: Celery with Redis broker
- **WebSocket**: FastAPI WebSocket support

### Security
- JWT authentication (PyJWT)
- Password hashing (bcrypt)
- Rate limiting (slowapi)
- CORS configuration
- Input validation (Pydantic)

### Deployment
- **Containerization**: Docker + Docker Compose
- **Orchestration**: Kubernetes (production) or Docker Swarm
- **CI/CD**: GitHub Actions
- **Monitoring**: Prometheus + Grafana
- **Logging**: ELK Stack (Elasticsearch, Logstash, Kibana)

---

## Deployment Architecture

### Development
```bash
docker-compose up
# Runs: API, PostgreSQL, Redis, Celery worker
```

### Production
```
Kubernetes Cluster:
├── API Pods (3 replicas, auto-scaling)
├── PostgreSQL StatefulSet
├── Redis Deployment
├── Celery Worker Deployment
└── Nginx Ingress Controller
```

---

## API Rate Limits

| Plan | Requests/min | WebSocket Connections |
|------|--------------|----------------------|
| Free | 30 | 1 |
| Basic | 100 | 3 |
| Premium | 300 | 10 |
| Enterprise | Unlimited | Unlimited |

---

## Next Steps for Implementation

1. **Setup FastAPI project structure**
2. **Implement authentication system**
3. **Create signal generation endpoints**
4. **Integrate strategy engine**
5. **Setup database models**
6. **Implement WebSocket support**
7. **Add background tasks for data fetching**
8. **Create API documentation (auto-generated)**
9. **Setup Docker containerization**
10. **Deploy to staging environment**

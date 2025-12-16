# Gold Signal API

Backend API service for The Gold Trader's Edge platform.

## Tech Stack

- **Framework**: FastAPI (Python 3.10+)
- **Database**: PostgreSQL
- **Cache**: Redis
- **Auth**: JWT tokens
- **Real-time**: WebSocket

## Features (Planned)

- [ ] User authentication & registration
- [ ] Subscription management (Stripe integration)
- [ ] REST endpoints for signals
- [ ] WebSocket for real-time signal push
- [ ] Trade history & analytics
- [ ] MT5 account linking

## API Endpoints (Planned)

```
POST   /auth/register        # User registration
POST   /auth/login           # Login, returns JWT
POST   /auth/refresh         # Refresh token

GET    /signals              # List recent signals
GET    /signals/:id          # Get signal details
GET    /signals/live         # WebSocket connection

GET    /user/profile         # Get user profile
PUT    /user/profile         # Update profile
GET    /user/subscription    # Get subscription status

POST   /mt5/connect          # Link MT5 account
POST   /mt5/trade            # Execute trade
GET    /mt5/positions        # Get open positions
```

## Development

```bash
cd packages/api
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run development server
uvicorn src.main:app --reload --port 8000
```

## Environment Variables

```env
DATABASE_URL=postgresql://user:pass@localhost:5432/goldtrader
REDIS_URL=redis://localhost:6379
JWT_SECRET=your-secret-key
STRIPE_API_KEY=sk_test_xxx
```

## Status: 🚧 Not Started

This package will be developed in Phase 2.

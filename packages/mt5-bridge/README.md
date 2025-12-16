# MT5 Bridge

MetaTrader 5 integration service for automated trade execution.

## Overview

This service connects to MetaTrader 5 accounts and executes trades based on signals from the Gold Signal Engine.

## Integration Options

### Option 1: MetaAPI (Recommended)
Cloud-based MT5 API service that doesn't require running MT5 locally.

- Website: https://metaapi.cloud
- Supports: MT4 & MT5
- Features: REST API, WebSocket, copy trading

### Option 2: Direct MT5 Python API
Requires MT5 terminal running on Windows.

- Package: `MetaTrader5`
- Limitation: Windows only

### Option 3: Custom EA + Webhook
Expert Advisor that listens for webhook signals.

- Most reliable for VPS deployment
- Requires MQL5 development

## Features (Planned)

- [ ] Connect to MT5 accounts via MetaAPI
- [ ] Execute market orders
- [ ] Set stop loss and take profit
- [ ] Manage open positions
- [ ] Sync trade history
- [ ] Risk management (lot sizing)

## API (Planned)

```python
from mt5_bridge import MT5Client

# Initialize client
client = MT5Client(api_key="xxx", account_id="123456")

# Execute trade
trade = await client.execute_trade(
    symbol="XAUUSD",
    direction="buy",
    lot_size=0.1,
    stop_loss=1950.00,
    take_profit=1980.00
)

# Get positions
positions = await client.get_positions()

# Close position
await client.close_position(position_id="12345")
```

## Development

```bash
cd packages/mt5-bridge
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Environment Variables

```env
METAAPI_TOKEN=your-metaapi-token
MT5_ACCOUNT_ID=your-account-id
MT5_PASSWORD=your-password
MT5_SERVER=your-broker-server
```

## Status: 🚧 Not Started

This package will be developed in Phase 4.

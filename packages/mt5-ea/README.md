# Gold Trader's Edge order EA

An MT5 Expert Advisor that places the bot's signals as real orders. It replaces
MetaAPI: the terminal is logged in to the broker, and the EA talks to the bot's
API over HTTPS.

## How it works

1. Every few seconds the EA calls `POST /v1/ea/poll`.
2. The API answers with the trading mode and any new signal (`trading/ea_orders.py`
   in the engine holds the rules). A signal is offered only while trading is
   LIVE, it is under 15 minutes old, and nothing has been recorded against it.
3. The EA moves the signal's stop and target to the broker's price, sizes the
   position from the account balance, and sends a market order with the stop
   loss and take profit attached.
4. It reports the fill, and later the close, to `/v1/ea/orders/{id}/fill` and
   `/close`. These land in the `broker_fills` table, apart from the paper record.

The stop loss and take profit sit at the broker, so a trade closes whether or
not the terminal is running. The terminal only has to be online when a signal
arrives. A signal that arrives while it is offline is skipped, not placed late.

## Switches

No order goes out unless all of these hold:

| Where | Switch |
|---|---|
| Server | `EA_API_KEY` is set (without it every EA endpoint refuses) |
| Dashboard | `auto_trading_enabled` on and `dry_run_mode` off |
| Terminal | Algo Trading on, and the EA attached with the same key |
| EA input | `InpAllowLiveAccount` true, for any account that is not a demo |

Server settings: `MAX_RISK_PER_TRADE` (default 0.0025, refused above 0.02),
`EA_ORDER_SYMBOLS` (default XAUUSD, EURUSD, GBPUSD), `EA_MAX_SIGNAL_AGE_MINUTES`
(default 15). The EA's own `InpMaxRiskPercent` caps whatever the server sends.

## Install

1. Copy this folder's `.mq5` and `.mqh` files to `MQL5/Experts/GoldTradersEdge/`
   in the terminal's data folder and compile `GoldTradersEdge.mq5` in MetaEditor.
2. In MT5: Tools > Options > Expert Advisors, tick "Allow WebRequest for listed
   URL" and add the API address.
3. Drag the EA onto any one chart, paste the EA key into `InpApiKey`, and turn
   Algo Trading on. The chart shows the mode and the time of the last contact.

`GET /v1/ea/status` (with the `X-EA-Key` header) shows the last poll and the
latest fills.

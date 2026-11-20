# MT5 terminal on Railway

Runs the MT5 terminal under Wine in a Linux container, logged in to the broker
with the order EA (`packages/mt5-ea`) attached. It replaces a laptop or a
Windows VPS: the terminal is always on, so no signal is missed.

MT5 on Wine is not an official setup. Watch `GET /v1/ea/status` on the API:
`last_poll.terminal` should read `railway` and `last_poll.at` should be recent.

## What the image does

| Step | File |
|---|---|
| Installs Wine and MT5 at build time | `Dockerfile`, `install-mt5.sh` |
| Compiles the EA; the build fails if it does not compile | `build-ea.sh` |
| Writes the login, EA inputs and allowed web address at start | `write-config.sh` |
| Starts MT5 on a virtual screen with the EA on one chart | `entrypoint.sh` |
| Copies the terminal's and the EA's logs to the container output | `tail-logs.sh` |

When MT5 stops, the container exits and Railway starts a new one.

## Railway service settings

| Variable | Value |
|---|---|
| `RAILWAY_DOCKERFILE_PATH` | `packages/mt5-terminal/Dockerfile` |
| `MT5_LOGIN`, `MT5_PASSWORD`, `MT5_SERVER` | The broker account |
| `EA_API_KEY` | Same key as the API service |
| `MT5_ALGO_TRADING` | `1` to let the EA trade; `0` (default) only polls |
| `MT5_ALLOW_LIVE_ACCOUNT` | `true` for an account that is not a demo |
| `MT5_SYMBOL_SUFFIX` | Broker's symbol suffix, if any |
| `EA_API_URL` | Only if the API is not at the production address |

Attach a volume at `/data`. It keeps the EA's memory of which signals it
already placed.

## Two files copied from a desktop terminal

- `servers.dat` is the broker server list, so the terminal can find the
  broker's servers by name. Refresh it from `config/servers.dat` when moving
  to a broker the desktop terminal has since logged in to.
- `webrequest.blob` is the allowed-address list for `WebRequest`. MT5 stores it
  encrypted, so it cannot be written as text. To change it, add the address in
  a desktop terminal (Tools > Options > Expert Advisors) and copy the
  `WebRequestUrl=` value from `config/common.ini`.

## Never two terminals trading one account

The API gives each signal to the first terminal that asks, by its
`InpLabel`. Even so, keep Algo Trading off on any other terminal logged in to
the same account.

# MT5 terminal on Railway

Runs the MT5 terminal under Wine in a Linux container, logged in to the broker
with the order EA (`packages/mt5-ea`) attached. It replaces a laptop or a
Windows VPS: the terminal is always on, so no signal is missed.

MT5 on Wine is not an official setup. Watch `GET /v1/ea/status` on the API:
`last_poll.terminal` should read `railway` and `last_poll.at` should be recent.

## What the image does

| Step | File |
|---|---|
| Installs Wine and unpacks the MT5 program files | `Dockerfile`, `install-mt5.sh` |
| Compiles the EA; the build fails if it does not compile | `build-ea.sh` |
| Writes the login and EA inputs at start | `write-config.sh` |
| Starts MT5 on a virtual screen with the EA on one chart | `entrypoint.sh` |
| Sends the EA's requests to the API | `bridge.sh` |
| Copies the terminal's and the EA's logs to the container output | `tail-logs.sh` |

When MT5 stops, the container exits and Railway starts a new one.

## Build and deploy

```
sh packages/mt5-terminal/make-vendor.sh   # once, and again for a newer MT5 build
sh packages/mt5-terminal/deploy.sh
```

The service is not linked to GitHub. `make-vendor.sh` packs the MT5 program
files from a Mac install into `vendor/mt5.tar.gz` (not in the repository), and
`deploy.sh` uploads that with the EA sources. MetaQuotes' own installer hangs
in Railway's builder, which is why the files are packed from a desktop.

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

## Things that did not work, and what is used instead

- **WebRequest.** MT5 stores its allowed-address list encrypted per machine, so
  it cannot be copied in or written as text. The EA runs with
  `InpBridgeFolder` set: it writes each request to a file and `bridge.sh`
  sends it with curl. The real EA key stays with `bridge.sh`.
- **32-bit Wine.** Railway cannot run 32-bit Linux programs. `WINEARCH=wow64`
  makes Wine work without them.
- **Paths with spaces** in `/config:`. The start config lives at `C:\gte-start.ini`.
- **`Enabled=0`** under `[Experts]` stops EAs from running at all. Trading is
  switched with `AllowLiveTrading` instead.

`servers.dat` is the broker server list from a desktop terminal, so the
terminal can find the broker's servers by name. Refresh it from
`config/servers.dat` when moving to a broker the desktop has since logged in to.

## Never two terminals trading one account

The API gives each signal to the first terminal that asks, by its
`InpLabel`. Even so, keep Algo Trading off on any other terminal logged in to
the same account.

#!/bin/sh
# Write the terminal's settings from the service's variables:
# the login and the EA's inputs.
set -eu

: "${MT5_LOGIN:?set MT5_LOGIN}"
: "${MT5_PASSWORD:?set MT5_PASSWORD}"
: "${MT5_SERVER:?set MT5_SERVER}"
: "${EA_API_KEY:?set EA_API_KEY}"
API_URL="${EA_API_URL:-https://the-gold-traders-edge-production.up.railway.app}"
# Expert Advisors always run; MT5_ALGO_TRADING decides whether this one may trade.
ALGO="${MT5_ALGO_TRADING:-0}"

# MT5 reads its own files as UTF-16 with Windows line ends.
utf16() {
  { printf '\377\376'; sed 's/$/\r/' | iconv -f UTF-8 -t UTF-16LE; } > "$1"
}

mkdir -p "$MT5_DIR/config" "$MT5_DIR/MQL5/Presets"
cp /gte/servers.dat "$MT5_DIR/config/servers.dat"

utf16 "$MT5_DIR/config/common.ini" <<EOF
[Experts]
AllowDllImport=0
Enabled=1
Account=0
Profile=0
Chart=0
Api=0
EOF

# The EA's requests go through bridge.sh, which holds the real key.
utf16 "$MT5_DIR/MQL5/Presets/gte.set" <<EOF
InpApiUrl=$API_URL
InpApiKey=sent-by-the-bridge
InpSymbolSuffix=${MT5_SYMBOL_SUFFIX:-}
InpAllowLiveAccount=${MT5_ALLOW_LIVE_ACCOUNT:-false}
InpLabel=${MT5_LABEL:-railway}
InpBridgeFolder=gte-bridge
EOF

# No spaces in this path: MT5 cannot read a /config: path that has them.
cat > "$WINEPREFIX/drive_c/gte-start.ini" <<EOF
[Common]
Login=$MT5_LOGIN
Password=$MT5_PASSWORD
Server=$MT5_SERVER
KeepPrivate=1
NewsEnable=0
[Experts]
AllowLiveTrading=$ALGO
AllowDllImport=0
Enabled=1
Account=0
Profile=0
[StartUp]
Expert=GoldTradersEdge\\GoldTradersEdge
ExpertParameters=gte.set
Symbol=${MT5_CHART_SYMBOL:-EURUSD}
Period=H1
EOF

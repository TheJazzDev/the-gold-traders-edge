#!/bin/sh
# Write the terminal's settings from the service's variables:
# the login, the EA's inputs, and the web address the EA may call.
set -eu

: "${MT5_LOGIN:?set MT5_LOGIN}"
: "${MT5_PASSWORD:?set MT5_PASSWORD}"
: "${MT5_SERVER:?set MT5_SERVER}"
: "${EA_API_KEY:?set EA_API_KEY}"
API_URL="${EA_API_URL:-https://the-gold-traders-edge-production.up.railway.app}"
ALGO="${MT5_ALGO_TRADING:-0}"

# MT5 reads its own files as UTF-16 with Windows line ends.
utf16() {
  { printf '\377\376'; sed 's/$/\r/' | iconv -f UTF-8 -t UTF-16LE; } > "$1"
}

mkdir -p "$MT5_DIR/config" "$MT5_DIR/MQL5/Presets"
cp /gte/servers.dat "$MT5_DIR/config/servers.dat"

# WebRequestUrl is stored encrypted, so it is copied from a terminal where the
# address was added by hand (see the README for how to refresh it).
utf16 "$MT5_DIR/config/common.ini" <<EOF
[Experts]
AllowDllImport=0
Enabled=$ALGO
Account=0
Profile=0
Chart=0
Api=0
WebRequest=1
WebRequestUrl=$(cat /gte/webrequest.blob)
EOF

utf16 "$MT5_DIR/MQL5/Presets/gte.set" <<EOF
InpApiUrl=$API_URL
InpApiKey=$EA_API_KEY
InpSymbolSuffix=${MT5_SYMBOL_SUFFIX:-}
InpAllowLiveAccount=${MT5_ALLOW_LIVE_ACCOUNT:-false}
InpLabel=${MT5_LABEL:-railway}
EOF

cat > "$MT5_DIR/config/gte-start.ini" <<EOF
[Common]
Login=$MT5_LOGIN
Password=$MT5_PASSWORD
Server=$MT5_SERVER
KeepPrivate=1
NewsEnable=0
[Experts]
AllowLiveTrading=$ALGO
AllowDllImport=0
Enabled=$ALGO
Account=0
Profile=0
[StartUp]
Expert=GoldTradersEdge\\GoldTradersEdge
ExpertParameters=gte.set
Symbol=${MT5_CHART_SYMBOL:-EURUSD}
Period=H1
EOF

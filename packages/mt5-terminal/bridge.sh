#!/bin/sh
# Send the EA's requests to the API. The EA cannot make web requests itself
# on this terminal (see packages/mt5-ea/GteBridge.mqh), so it leaves each
# request as a file and reads the answer from another.
set -u

API_URL="${EA_API_URL:-https://the-gold-traders-edge-production.up.railway.app}"
DIR="$MT5_DIR/MQL5/Files/gte-bridge"
mkdir -p "$DIR"
rm -f "$DIR"/*

while :; do
  for request in "$DIR"/*.req; do
    [ -f "$request" ] || continue
    id="$(basename "$request" .req)"
    path="$(head -n 1 "$request")"
    case "$path" in
      /v1/ea/*) ;;
      *) rm -f "$request"; continue ;;
    esac
    tail -n +2 "$request" > /tmp/bridge-body
    : > /tmp/bridge-answer
    status="$(curl -s -m 7 -o /tmp/bridge-answer -w '%{http_code}' -X POST "$API_URL$path" \
      -H 'Content-Type: application/json' -H "X-EA-Key: $EA_API_KEY" \
      --data-binary @/tmp/bridge-body)" || status=-1
    { echo "$status"; cat /tmp/bridge-answer; } > "$DIR/$id.part"
    mv "$DIR/$id.part" "$DIR/$id.res"
    rm -f "$request"
  done
  find "$DIR" -type f -mmin +2 -delete 2>/dev/null
  sleep 0.2
done

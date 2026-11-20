#!/bin/sh
# Build step: compile the EA with MetaEditor. The build fails if it does not compile.
set -eu

EA_DIR="$MT5_DIR/MQL5/Experts/GoldTradersEdge"
mkdir -p "$EA_DIR"
cp /gte/ea/* "$EA_DIR/"

rm -f /tmp/.X99-lock /tmp/.X11-unix/X99
Xvfb :99 -screen 0 1024x768x24 -nolisten tcp &
sleep 2

cd "$MT5_DIR"
timeout 300 wine metaeditor64.exe /portable \
  '/compile:MQL5\Experts\GoldTradersEdge\GoldTradersEdge.mq5' /log || true
wineserver -w || true

iconv -f UTF-16LE -t UTF-8 -c "$EA_DIR/GoldTradersEdge.log" 2>/dev/null | tr -d '\r' | tail -20 || true
if [ ! -f "$EA_DIR/GoldTradersEdge.ex5" ]; then
  echo "the EA did not compile"
  exit 1
fi
echo "EA compiled"

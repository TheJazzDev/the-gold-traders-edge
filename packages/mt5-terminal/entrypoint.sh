#!/bin/sh
# Start the terminal with the EA attached. When the terminal stops, the
# container stops too, and the platform starts a fresh one.
set -eu

# What the EA remembers (which signals it already placed) lives in Bases.
# Keep it on the volume at /data so it survives a restart.
mkdir -p /data/Bases
if [ ! -L "$MT5_DIR/Bases" ]; then
  cp -an "$MT5_DIR/Bases/." /data/Bases/ 2>/dev/null || true
  rm -rf "$MT5_DIR/Bases"
  ln -s /data/Bases "$MT5_DIR/Bases"
fi

# Start from the terminal's default charts, so a restart never leaves a
# second copy of the EA on an old chart.
rm -rf "$MT5_DIR/MQL5/Profiles/Charts"

sh /gte/write-config.sh

rm -f /tmp/.X99-lock /tmp/.X11-unix/X99
Xvfb :99 -screen 0 1024x768x24 -nolisten tcp &
sleep 2
sh /gte/tail-logs.sh &
sh /gte/bridge.sh &

trap 'wineserver -k 15 || true; exit 0' TERM INT

echo "[gte] starting MT5 for account $MT5_LOGIN on $MT5_SERVER, algo trading ${MT5_ALGO_TRADING:-0}"
cd "$MT5_DIR"
wine terminal64.exe /portable '/config:C:\gte-start.ini' &
wait $! || true
wineserver -w || true
echo "[gte] MT5 stopped"
exit 1

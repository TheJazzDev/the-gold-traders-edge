#!/bin/sh
# Build step: install the MT5 terminal into the Wine prefix.
set -eu

rm -f /tmp/.X99-lock /tmp/.X11-unix/X99
Xvfb :99 -screen 0 1024x768x24 -nolisten tcp &
sleep 2

wineboot -i
wineserver -w
wine reg add 'HKCU\Software\Wine' /v Version /d win10 /f
wineserver -w

wget -qO /tmp/mt5setup.exe \
  https://download.mql5.com/cdn/web/metaquotes.software.corp/mt5/mt5setup.exe
wine /tmp/mt5setup.exe /auto &

# The installer downloads the terminal, then starts it. Wait for the files.
waited=0
until [ -f "$MT5_DIR/terminal64.exe" ] && [ -f "$MT5_DIR/metaeditor64.exe" ]; do
  sleep 10
  waited=$((waited + 10))
  if [ "$waited" -ge 900 ]; then
    echo "MT5 did not install within 15 minutes"
    ls -la "/opt/wine/drive_c/Program Files" || true
    exit 1
  fi
done
sleep 45
wineserver -k || true
sleep 3

# One run in portable mode, so the terminal unpacks its MQL5 folder (the
# standard library the EA compiles against) next to the program.
( cd "$MT5_DIR" && wine terminal64.exe /portable ) &
waited=0
until [ -f "$MT5_DIR/MQL5/Include/Trade/Trade.mqh" ]; do
  sleep 5
  waited=$((waited + 5))
  if [ "$waited" -ge 300 ]; then
    echo "the MQL5 standard library did not appear"
    ls -la "$MT5_DIR" "$MT5_DIR/MQL5" || true
    exit 1
  fi
done
sleep 20
wineserver -k || true
sleep 3

# A clean copy of the chart profiles, restored at every start so that a
# restart never leaves a second copy of the EA on an old chart.
tar -C "$MT5_DIR/MQL5/Profiles" -cf /gte/charts.tar Charts
rm -f /tmp/mt5setup.exe
echo "MT5 installed"

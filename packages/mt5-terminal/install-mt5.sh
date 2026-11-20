#!/bin/sh
# Build step: create the Wine prefix and unpack the MT5 program files into it.
set -eu

rm -f /tmp/.X99-lock /tmp/.X11-unix/X99
Xvfb :99 -screen 0 1024x768x24 -nolisten tcp &
sleep 2

wine wineboot -i
wineserver -w
wine reg add 'HKCU\Software\Wine' /v Version /d win10 /f
wineserver -w

mkdir -p "$MT5_DIR"
tar -C "$MT5_DIR" -xzf /tmp/mt5.tar.gz
rm -f /tmp/mt5.tar.gz
mkdir -p "$MT5_DIR/Bases" "$MT5_DIR/config" "$MT5_DIR/logs"

echo "MT5 unpacked"

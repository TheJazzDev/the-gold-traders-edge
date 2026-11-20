#!/bin/sh
# Run on a Mac with MT5 installed: pack the terminal's program files into
# vendor/mt5.tar.gz for the image. No account data and no price history go in.
# MetaQuotes' own installer hangs in Railway's builder, so the image uses
# these files instead. Run it again to move the image to a newer MT5 build.
set -eu

SOURCE="${1:-$HOME/Library/Application Support/net.metaquotes.wine.metatrader5/drive_c/Program Files/MetaTrader 5}"
HERE="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$HERE/vendor"
tar -C "$SOURCE" -czf "$HERE/vendor/mt5.tar.gz" \
  --exclude 'MQL5/Logs' --exclude 'MQL5/Files' --exclude 'MQL5/Experts/GoldTradersEdge' \
  --exclude 'MQL5/experts.dat' --exclude 'MQL5/Profiles/Charts' --exclude 'MQL5/Profiles/deleted' \
  terminal64.exe metaeditor64.exe MQL5 Sounds
ls -lh "$HERE/vendor/mt5.tar.gz"

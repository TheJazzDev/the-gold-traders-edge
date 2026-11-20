#!/bin/sh
# Copy new lines from the terminal's journal and the EA's log to the
# container's output, so they show up in `railway logs`.
set -u

while sleep 15; do
  for file in "$MT5_DIR"/logs/*.log "$MT5_DIR"/MQL5/[Ll]ogs/*.log; do
    [ -f "$file" ] || continue
    mark="/tmp/log-$(printf '%s' "$file" | md5sum | cut -c1-12)"
    seen=$(cat "$mark" 2>/dev/null || echo 0)
    size=$(stat -c %s "$file")
    size=$((size - size % 2))
    [ "$size" -gt "$seen" ] || continue
    case "$file" in
      */MQL5/[Ll]ogs/*) tag="ea" ;;
      *) tag="mt5" ;;
    esac
    tail -c "+$((seen + 1))" "$file" | head -c "$((size - seen))" \
      | iconv -f UTF-16LE -t UTF-8 -c | tr -d '\r' | sed "s/^\xef\xbb\xbf//; s/^/[$tag] /"
    echo "$size" > "$mark"
  done
done

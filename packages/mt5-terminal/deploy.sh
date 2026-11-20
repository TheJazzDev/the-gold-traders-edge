#!/bin/sh
# Build and deploy the terminal image to the Railway service `mt5-terminal`.
# The service is not linked to GitHub, because the image needs
# vendor/mt5.tar.gz (see make-vendor.sh), which is not in the repository.
set -eu

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
[ -f "$HERE/vendor/mt5.tar.gz" ] || { echo "run make-vendor.sh first"; exit 1; }

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$STAGE/packages"
cp -R "$ROOT/packages/mt5-ea" "$ROOT/packages/mt5-terminal" "$STAGE/packages/"

cd "$ROOT"
railway up "$STAGE" --path-as-root --service mt5-terminal --detach

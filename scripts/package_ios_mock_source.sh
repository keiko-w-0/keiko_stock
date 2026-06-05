#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="$ROOT_DIR/dist/iphone"
PACKAGE_DIR="$DIST_DIR/KeikoStockAI-iPhone-Mock"
WEB_DIR="$PACKAGE_DIR/Web"

mkdir -p "$WEB_DIR" "$PACKAGE_DIR/App"

ditto "$ROOT_DIR/ios/KeikoStockAI/README.md" "$PACKAGE_DIR/README.md"
ditto "$ROOT_DIR/ios/KeikoStockAI/App" "$PACKAGE_DIR/App"

for item in \
  index.html \
  styles.css \
  app.js \
  manifest.webmanifest \
  service-worker.js \
  assets
do
  ditto "$ROOT_DIR/$item" "$WEB_DIR/$item"
done

ditto -c -k --keepParent "$PACKAGE_DIR" "$DIST_DIR/KeikoStockAI-iPhone-Mock-Source.zip"

echo "$PACKAGE_DIR"
echo "$DIST_DIR/KeikoStockAI-iPhone-Mock-Source.zip"

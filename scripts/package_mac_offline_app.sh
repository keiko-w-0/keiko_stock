#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_NAME="Keiko Stock AI"
DIST_DIR="$ROOT_DIR/dist/macos-offline"
APP_DIR="$DIST_DIR/$APP_NAME.app"
CONTENTS_DIR="$APP_DIR/Contents"
MACOS_DIR="$CONTENTS_DIR/MacOS"
RESOURCES_DIR="$CONTENTS_DIR/Resources"
APP_RESOURCES_DIR="$RESOURCES_DIR/app"
MIN_MACOS="12.0"

mkdir -p "$MACOS_DIR" "$APP_RESOURCES_DIR"

cp "$ROOT_DIR/packaging/mac/Info.plist" "$CONTENTS_DIR/Info.plist"
MACOSX_DEPLOYMENT_TARGET="$MIN_MACOS" clang "$ROOT_DIR/packaging/mac/KeikoStockAIOffline.m" \
  -arch arm64 \
  -arch x86_64 \
  -mmacosx-version-min="$MIN_MACOS" \
  -fobjc-arc \
  -framework Cocoa \
  -framework WebKit \
  -o "$MACOS_DIR/KeikoStockAI"

for item in \
  assets \
  docs \
  index.html \
  styles.css \
  app.js \
  manifest.webmanifest \
  service-worker.js
do
  ditto "$ROOT_DIR/$item" "$APP_RESOURCES_DIR/$item"
done

if command -v codesign >/dev/null 2>&1; then
  codesign --force --deep --sign - "$APP_DIR" >/dev/null
fi

ditto -c -k --keepParent "$APP_DIR" "$DIST_DIR/KeikoStockAI-mac-mock-offline-universal.zip"

echo "$APP_DIR"
echo "$DIST_DIR/KeikoStockAI-mac-mock-offline-universal.zip"

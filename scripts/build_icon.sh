#!/bin/bash
# 從 assets/icon_source.png 重新產生 macOS .icns
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/assets/icon_source.png"
ICONSET="$ROOT/assets/icon.iconset"
ICNS="$ROOT/assets/FlutterDevTools.icns"

if [[ ! -f "$SRC" ]]; then
  echo "缺少 $SRC" >&2
  exit 1
fi

rm -rf "$ICONSET"
mkdir -p "$ICONSET"
cd "$ICONSET"

sips -z 16 16     "$SRC" --out icon_16x16.png >/dev/null
sips -z 32 32     "$SRC" --out icon_16x16@2x.png >/dev/null
sips -z 32 32     "$SRC" --out icon_32x32.png >/dev/null
sips -z 64 64     "$SRC" --out icon_32x32@2x.png >/dev/null
sips -z 128 128   "$SRC" --out icon_128x128.png >/dev/null
sips -z 256 256   "$SRC" --out icon_128x128@2x.png >/dev/null
sips -z 256 256   "$SRC" --out icon_256x256.png >/dev/null
sips -z 512 512   "$SRC" --out icon_256x256@2x.png >/dev/null
sips -z 512 512   "$SRC" --out icon_512x512.png >/dev/null
sips -z 1024 1024 "$SRC" --out icon_512x512@2x.png >/dev/null

iconutil -c icns "$ICONSET" -o "$ICNS"
echo "已產生: $ICNS"

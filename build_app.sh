#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

echo "==> 安裝建置依賴（若尚未安裝）"
python3 -m pip install --upgrade pip
python3 -m pip install py2app requests rumps pyobjc-framework-Cocoa

echo "==> 建置 Flutter DevTools.app"
rm -rf build dist
python3 setup_app.py py2app

APP_PATH="dist/Flutter DevTools.app"
if [[ -d "$APP_PATH" ]]; then
  echo ""
  echo "完成：$APP_PATH"
  echo "可將此 .app 拖到「應用程式」，之後從 Launchpad 或 Spotlight 開啟。"
  echo "首次開啟若被阻擋：系統設定 → 隱私權與安全性 → 仍要開啟"
else
  echo "建置失敗，請檢查上方錯誤訊息。" >&2
  exit 1
fi

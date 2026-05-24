# monitor

macOS 選單列工具 **Flutter DevTools**，提供 Performance 時間軸採樣與可選的桌面 **Performance** 面板。介面以 Flutter DevTools Performance 風格呈現 frame / build / raster 等指標。

> **平台**：僅支援 macOS（依賴選單列與 AppKit）。

---

## 目錄

- [環境需求](#環境需求)
- [快速開始](#快速開始)
- [方式一：雙擊 App 開啟（推薦）](#方式一雙擊-app-開啟推薦)
- [方式二：終端機執行](#方式二終端機執行)
- [首次開啟與權限](#首次開啟與權限)
- [設定檔說明](#設定檔說明)
- [選單功能對照](#選單功能對照)
- [開機自動啟動](#開機自動啟動)
- [自行打包 App](#自行打包-app)
- [常見問題](#常見問題)
- [專案結構](#專案結構)
- [從 GitHub 取得原始碼](#從-github-取得原始碼)

---

## 環境需求

| 項目 | 說明 |
|------|------|
| 系統 | macOS 11.0 或以上 |
| Python | 3.10+（自行用指令執行時需要） |
| 網路 | 需能連線至資料來源 API |

---

## 快速開始

```bash
# 1. 克隆專案
git clone https://github.com/TONYCHOU81905/monitor.git
cd monitor

# 2. 安裝依賴（指令列執行時）
python3 -m pip install requests rumps pyobjc-framework-Cocoa

# 3. 執行
python3 flutter_monitor.py
```

執行成功後，請看螢幕**右上角選單列**是否出現 **`Perf: …`**，點擊即可展開選單。

---

## 方式一：雙擊 App 開啟（推薦）

不必每次開終端機。專案已提供打包腳本，可產生獨立 `.app`。

### 建置 App（只需做一次，或程式更新後重做）

```bash
cd monitor
chmod +x build_app.sh
./build_app.sh
```

完成後會產生：

```text
dist/Flutter DevTools.app
```

### 安裝到本機

1. 在 Finder 開啟專案內的 `dist` 資料夾  
2. 將 **`Flutter DevTools.app`** 拖到 **「應用程式」** 資料夾  
3. 用以下任一方式啟動：  
   - Launchpad → 搜尋 **Flutter DevTools**  
   - Spotlight（`⌘ + 空白`）→ 輸入 **Flutter DevTools**  
   - Finder → 應用程式 → 雙擊 **Flutter DevTools**

### 結束程式

- 選單列圖示 → **Quit DevTools**  
- 或在「活動監視器」結束 `Flutter DevTools`

---

## 方式二：終端機執行

適合開發除錯。

```bash
cd monitor
python3 -m pip install requests rumps pyobjc-framework-Cocoa
python3 flutter_monitor.py
```

- 終端機**通常不會印出任何文字**，屬正常現象  
- 程序會持續執行，選單列出現 **`Perf: …`** 即代表已啟動  
- 結束：終端機按 `Ctrl + C`，或選單 **Quit DevTools**

---

## 首次開啟與權限

### 若出現「無法打開，因為來自身份不明的開發者」

1. 打開 **系統設定** → **隱私權與安全性**  
2. 找到被阻擋的 **Flutter DevTools**  
3. 點 **仍要開啟**

或：在 `.app` 上按右鍵 → **打開** → 再按 **打開**。

### 選單列找不到圖示

- 選單列空間不足時，圖示可能被收進 **`>>`**（控制中心左側）  
- 確認程式仍在執行（活動監視器）

### 資料一直顯示 Profiling / 無 traces

- 選單 → **Capture timeline** 手動更新  
- 檢查網路與設定檔中的 pinned traces（見下方）  
- 選單若顯示 **Trace error**，請看錯誤訊息（多為網路或 id 格式錯誤）

---

## 設定檔說明

設定檔路徑（使用者目錄）：

```text
~/.flutter_perf_traces.json
```

若曾使用舊版，會自動從 `~/.flutter_monitor_config.json` 複製一份。

也可在選單：**Reveal trace config** / **Open config in Finder** 開啟。

### 完整範例

```json
{
  "interval_seconds": 20,
  "compact_mode": true,
  "show_price_in_bar": false,
  "show_desktop_window": false,
  "desktop_always_on_top": true,
  "targets": [
    {
      "code": "2330",
      "market": "tse",
      "alias": "RenderViewport::build()"
    },
    {
      "code": "2317",
      "market": "tse",
      "alias": "MaterialApp::build()"
    },
    {
      "code": "6147",
      "market": "otc",
      "alias": "ShaderWarmUp::build()"
    }
  ]
}
```

### 欄位說明

| 欄位 | 說明 |
|------|------|
| `interval_seconds` | 自動採樣間隔（秒），建議 ≥ 20，最小 5 |
| `compact_mode` | `true`：選單 / 面板只顯示精簡列；`false`：顯示更多 isolate / pool 資訊 |
| `show_price_in_bar` | `true`：選單列標題顯示第一個 trace 的 frame ms |
| `show_desktop_window` | `true`：啟動時自動開啟 Performance 桌面面板 |
| `desktop_always_on_top` | `true`：桌面面板浮在其他視窗上方 |
| `targets` | 要追蹤的 widget trace 清單 |

### `targets` 每一筆

| 欄位 | 選單用語 | 實際意義 |
|------|----------|----------|
| `code` | trace **id** | 標的代號（例如 `2330`） |
| `market` | **pool** | `tse`＝上市、`otc`＝上櫃 |
| `alias` | **label** | 時間軸上顯示的名稱（建議用 `XXX::build()` 格式） |

### 用選單新增 / 修改（不必手動編輯 JSON）

**Pin widget trace…** 格式：

```text
id,pool,label
```

範例：

```text
2330,tse,RenderViewport::build()
6147,otc,ShaderWarmUp::build()
```

- **Unpin trace…**：輸入要移除的 `id`  
- **Rename trace label…**：格式 `id,new label`  
- **Sampling interval…**：修改自動更新秒數  

修改設定檔後，可 **Capture timeline** 或重啟 App 套用。

---

## 選單功能對照

| 選單項目 | 功能 |
|----------|------|
| **Capture timeline** | 立即重新採樣 |
| **Pin widget trace…** | 新增追蹤 |
| **Unpin trace…** | 移除追蹤 |
| **Rename trace label…** | 重新命名顯示標籤 |
| **Sampling interval…** | 設定自動採樣間隔 |
| **Compact timeline rows** | 精簡列顯示 |
| **Show frame ms in menu bar** | 選單列顯示第一筆 frame 時間 |
| **Show Performance panel** | 開關桌面 Performance 視窗 |
| **Panel always on top** | 面板是否永遠置頂 |
| **Reveal trace config** | 顯示設定檔路徑 |
| **Open config in Finder** | 在 Finder 中顯示設定檔 |
| **About DevTools** | 關於 |
| **Quit DevTools** | 結束程式 |

### 桌面 Performance 面板

勾選 **Show Performance panel** 後會出現深色視窗，內容包含：

- Recording 狀態與時間  
- Frame / UI / Build / Raster 欄位  
- GPU 長條與 jank / shader Δ 等指標  

可拖曳、縮放；關閉視窗紅燈會記住為關閉狀態。

---

## 開機自動啟動

1. 先將 **`Flutter DevTools.app`** 安裝到「應用程式」  
2. **系統設定** → **一般** → **登入項目**（或「使用者與群組」→ 登入項目）  
3. 按 **+** → 選擇 **Flutter DevTools** → 加入  

之後登入 macOS 會自動在選單列出現。

---

## 自行打包 App

```bash
./build_app.sh
```

腳本會安裝 `py2app`、`requests`、`rumps` 等，並在 `dist/` 產生 **`Flutter DevTools.app`**。

手動打包：

```bash
python3 -m pip install py2app requests rumps pyobjc-framework-Cocoa
python3 setup_app.py py2app
```

---

## 常見問題

**Q：執行後終端機立刻回到提示符？**  
A：可能執行到空檔案或路徑錯誤。請確認在專案目錄且 `flutter_monitor.py` 有內容（約 700 行）。

**Q：`import rumps` 失敗？**  
A：執行 `python3 -m pip install rumps pyobjc-framework-Cocoa`。

**Q：資料顯示 `—` 或 no sample？**  
A：非交易時段或該標的暫無成交，屬資料源限制；可稍後再 **Capture timeline**。

**Q：想還原預設設定？**  
A：刪除 `~/.flutter_perf_traces.json` 後重啟 App，會重新建立預設檔。

**Q：Git 要提交哪些檔案？**  
A：建議提交 `flutter_monitor.py`、`setup_app.py`、`build_app.sh`、`README.md`；**不要**提交 `build/`、`dist/`（體積大）。可新增 `.gitignore` 排除它們。

---

## 專案結構

```text
monitor/
├── flutter_monitor.py   # 主程式
├── setup_app.py         # py2app 打包設定
├── build_app.sh         # 一鍵建置 .app
├── README.md            # 本說明
├── build/               # 建置暫存（勿提交）
└── dist/                # 產出的 .app（勿提交）
    └── Flutter DevTools.app
```

---

## 從 GitHub 取得原始碼

```bash
git clone https://github.com/TONYCHOU81905/monitor.git
cd monitor
```

### 首次推送到自己的遠端（維護者）

```bash
git init
git add README.md flutter_monitor.py setup_app.py build_app.sh .gitignore
git commit -m "first commit"
git branch -M main
git remote add origin https://github.com/TONYCHOU81905/monitor.git
git push -u origin main
```

---

## 授權

本專案供個人學習與本機使用。資料來源為公開 API，請遵守相關服務條款與當地法規。

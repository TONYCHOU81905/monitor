#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Flutter DevTools Performance overlay (menu bar + optional panel)."""

import json
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

import objc
import requests
import rumps
from AppKit import (
    NSAttributedString,
    NSBackingStoreBuffered,
    NSBezelBorder,
    NSColor,
    NSFloatingWindowLevel,
    NSFont,
    NSMakeRect,
    NSNormalWindowLevel,
    NSScrollView,
    NSTextView,
    NSViewHeightSizable,
    NSViewWidthSizable,
    NSWindow,
    NSWindowStyleMaskClosable,
    NSWindowStyleMaskMiniaturizable,
    NSWindowStyleMaskResizable,
    NSWindowStyleMaskTitled,
)
from Foundation import NSObject
from PyObjCTools.AppHelper import callAfter


APP_NAME = "Flutter DevTools"
CONFIG_PATH = Path.home() / ".flutter_perf_traces.json"
LEGACY_CONFIG_PATH = Path.home() / ".flutter_monitor_config.json"

API_URL = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://mis.twse.com.tw/stock/index.jsp",
}

# DevTools Performance 色系
C_BG = (0.11, 0.11, 0.12)
C_PANEL = (0.14, 0.14, 0.15)
C_TEXT = (0.88, 0.89, 0.91)
C_DIM = (0.55, 0.57, 0.60)
C_ACCENT = (0.33, 0.77, 0.97)
C_GOOD = (0.30, 0.85, 0.45)
C_BAD = (0.95, 0.35, 0.35)
C_WARN = (0.98, 0.76, 0.25)

DEFAULT_CONFIG = {
    "interval_seconds": 20,
    "compact_mode": True,
    "show_price_in_bar": False,
    "show_desktop_window": False,
    "desktop_always_on_top": True,
    "targets": [
        {"code": "2330", "market": "tse", "alias": "RenderViewport"},
        {"code": "2317", "market": "tse", "alias": "MaterialApp"},
        {"code": "6147", "market": "otc", "alias": "ShaderWarmUp"},
    ],
}


def _rgb(rgb):
    return NSColor.colorWithRed_green_blue_alpha_(rgb[0], rgb[1], rgb[2], 1.0)


def load_config():
    if not CONFIG_PATH.exists() and LEGACY_CONFIG_PATH.exists():
        CONFIG_PATH.write_text(LEGACY_CONFIG_PATH.read_text(encoding="utf-8"), encoding="utf-8")

    if not CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
        for key, val in (
            ("interval_seconds", 20),
            ("compact_mode", True),
            ("show_price_in_bar", False),
            ("show_desktop_window", False),
            ("desktop_always_on_top", True),
        ):
            config.setdefault(key, val)
        config.setdefault("targets", [])
        return config
    except Exception:
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()


def save_config(config):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def safe_float(value):
    try:
        if value in ("-", "", None):
            return None
        return float(value)
    except Exception:
        return None


def build_ex_ch(targets):
    items = []
    for item in targets:
        code = str(item.get("code", "")).strip()
        market = str(item.get("market", "tse")).strip().lower()
        if not code:
            continue
        if market not in ("tse", "otc"):
            market = "tse"
        items.append(f"{market}_{code}.tw")
    return "|".join(items)


def fetch_targets(targets):
    if not targets:
        return []
    params = {
        "ex_ch": build_ex_ch(targets),
        "json": "1",
        "delay": "0",
        "_": int(time.time() * 1000),
    }
    response = requests.get(API_URL, params=params, headers=HEADERS, timeout=8)
    response.raise_for_status()
    return response.json().get("msgArray", [])


def quote_to_perf_view(q, alias_map):
    """將資料轉成 Performance 時間軸用的顯示欄位。"""
    code = q.get("c", "")
    alias = alias_map.get(code, q.get("n", code) or code)
    trace = alias if "::" in alias else f"{alias}::build()"

    price = safe_float(q.get("z"))
    yesterday = safe_float(q.get("y"))
    vol = safe_float(q.get("v")) or 0

    if price is not None:
        frame_ms = price / 100.0
        build_ms = frame_ms * 0.41
        raster_ms = frame_ms * 0.17
        ui_ms = frame_ms * 0.28
    else:
        frame_ms = build_ms = raster_ms = ui_ms = None

    delta_pct = 0.0
    if price is not None and yesterday is not None and yesterday != 0:
        delta_ms = (price - yesterday) / 100.0
        delta_pct = (price - yesterday) / yesterday * 100
        if delta_ms > 0:
            delta_short = f"▲ +{delta_ms:.2f}ms jank"
            delta_color = "bad"
        elif delta_ms < 0:
            delta_short = f"▼ {delta_ms:.2f}ms"
            delta_color = "good"
        else:
            delta_short = "→ stable"
            delta_color = "neutral"
        shader_delta = f"shader Δ {delta_pct:+.2f}%"
    else:
        delta_short = "no sample"
        delta_color = "neutral"
        shader_delta = "shader Δ —"
        delta_ms = 0

    sample_tick = q.get("t", "—")
    rebuilds = int(vol // 1000) if vol else 0
    gpu_load = min(100, max(4, int(abs(delta_pct) * 6))) if price and yesterday else 8

    return {
        "code": code,
        "alias": alias,
        "trace_name": trace,
        "frame_ms": f"{frame_ms:.2f}" if frame_ms is not None else "—",
        "build_ms": f"{build_ms:.2f}" if build_ms is not None else "—",
        "raster_ms": f"{raster_ms:.2f}" if raster_ms is not None else "—",
        "ui_ms": f"{ui_ms:.2f}" if ui_ms is not None else "—",
        "delta_short": delta_short,
        "delta_color": delta_color,
        "shader_delta": shader_delta,
        "sample_tick": sample_tick,
        "rebuilds": str(rebuilds),
        "gpu_load": gpu_load,
        "isolate": code,
        "pool": q.get("ch", "main"),
    }


def menu_line(view):
    return (
        f"{view['trace_name'][:26]:26}  "
        f"{view['frame_ms']} ms  "
        f"{view['delta_short']}  "
        f"@{view['sample_tick']}"
    )


def bar_title(views, ok_count, total):
    if not views:
        return "Perf: idle"
    if len(views) == 1:
        v = views[0]
        return f"Perf: {v['frame_ms']}ms"
    return f"Perf: {ok_count}/{total} traces"


class _DesktopWindowDelegate(NSObject):
    def initWithPanel_(self, panel):
        self = objc.super(_DesktopWindowDelegate, self).init()
        if self is None:
            return None
        self.panel = panel
        return self

    def windowWillClose_(self, notification):
        self.panel.on_window_closed()


class DesktopPanel:
    """Flutter DevTools Performance 深色面板。"""

    def __init__(self, app):
        self.app = app
        self.window = None
        self.text_view = None
        self._delegate = None

    def _ensure_window(self):
        if self.window is not None:
            return

        frame = NSMakeRect(120, 120, 480, 340)
        style = (
            NSWindowStyleMaskTitled
            | NSWindowStyleMaskClosable
            | NSWindowStyleMaskMiniaturizable
            | NSWindowStyleMaskResizable
        )
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            frame, style, NSBackingStoreBuffered, False
        )
        self.window.setTitle_("Performance — Flutter DevTools")
        self.window.setMinSize_((400, 240))
        self.window.setReleasedWhenClosed_(False)
        self.window.setBackgroundColor_(_rgb(C_BG))

        scroll = NSScrollView.alloc().initWithFrame_(self.window.contentView().bounds())
        scroll.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        scroll.setHasVerticalScroller_(True)
        scroll.setBorderType_(NSBezelBorder)
        scroll.setDrawsBackground_(False)

        self.text_view = NSTextView.alloc().initWithFrame_(scroll.bounds())
        self.text_view.setEditable_(False)
        self.text_view.setSelectable_(True)
        self.text_view.setRichText_(True)
        self.text_view.setDrawsBackground_(True)
        self.text_view.setBackgroundColor_(_rgb(C_BG))
        self.text_view.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)

        scroll.setDocumentView_(self.text_view)
        self.window.setContentView_(scroll)

        self._delegate = _DesktopWindowDelegate.alloc().initWithPanel_(self)
        self.window.setDelegate_(self._delegate)
        self._apply_window_level()

    def _apply_window_level(self):
        if not self.window:
            return
        level = NSFloatingWindowLevel if self.app.config.get("desktop_always_on_top", True) else NSNormalWindowLevel
        self.window.setLevel_(level)

    def is_visible(self):
        return self.window is not None and self.window.isVisible()

    def show(self):
        self._ensure_window()
        self._apply_window_level()
        self.update_content()
        self.window.makeKeyAndOrderFront_(None)

    def hide(self):
        if self.window:
            self.window.orderOut_(None)

    def toggle(self):
        if self.is_visible():
            self.hide()
            self.app.config["show_desktop_window"] = False
        else:
            self.show()
            self.app.config["show_desktop_window"] = True
        save_config(self.app.config)

    def on_window_closed(self):
        self.app.config["show_desktop_window"] = False
        save_config(self.app.config)
        self.hide()

    def _attr(self, text, color, bold=False, size=12):
        font = NSFont.monospacedSystemFontOfSize_weight_(size, 0.5 if bold else 0)
        return NSAttributedString.alloc().initWithString_attributes_(
            text,
            {
                "NSColor": color,
                "NSFont": font,
            },
        )

    def _bar(self, pct, width=28):
        filled = int(width * pct / 100)
        return "█" * filled + "░" * (width - filled)

    def build_attributed(self):
        app = self.app
        parts = []

        header = "  Performance"
        parts.append(self._attr(header + "\n", _rgb(C_ACCENT), bold=True, size=13))

        if app.last_error:
            sub = f"  ● Trace error  ·  {app.last_update or '—'}\n"
            parts.append(self._attr(sub, _rgb(C_BAD)))
            parts.append(self._attr(f"  {app.last_error[:120]}\n\n", _rgb(C_DIM)))
        else:
            sub = f"  ● Recording  ·  {app.last_update or '—'}  ·  60 FPS budget 16.67ms\n"
            parts.append(self._attr(sub, _rgb(C_GOOD)))

        parts.append(self._attr("  " + "─" * 52 + "\n", _rgb(C_PANEL)))
        parts.append(self._attr(
            f"  {'Frame':<28} {'UI':>7} {'Build':>7} {'Raster':>7}  GPU\n",
            _rgb(C_DIM),
            size=11,
        ))
        parts.append(self._attr("  " + "─" * 52 + "\n", _rgb(C_PANEL)))

        if not app.latest_views:
            parts.append(self._attr("  No pinned traces — use menu to pin widgets\n", _rgb(C_DIM)))
        else:
            for view in app.latest_views:
                color = {
                    "good": _rgb(C_GOOD),
                    "bad": _rgb(C_BAD),
                    "neutral": _rgb(C_TEXT),
                }[view["delta_color"]]

                row = (
                    f"  {view['trace_name'][:28]:<28} "
                    f"{view['ui_ms']:>6} "
                    f"{view['build_ms']:>6} "
                    f"{view['raster_ms']:>6}  "
                )
                parts.append(self._attr(row, _rgb(C_TEXT), size=11))
                bar = self._bar(view["gpu_load"])
                parts.append(self._attr(f"{bar}\n", _rgb(C_ACCENT), size=10))

                parts.append(self._attr(
                    f"      {view['frame_ms']} ms total  ·  {view['delta_short']}  ·  "
                    f"{view['shader_delta']}  ·  rebuilds {view['rebuilds']}\n",
                    color,
                    size=11,
                ))
                if not app.config.get("compact_mode", True):
                    parts.append(self._attr(
                        f"      isolate {view['isolate']}  ·  pool {view['pool']}  ·  tick {view['sample_tick']}\n",
                        _rgb(C_DIM),
                        size=10,
                    ))

        parts.append(self._attr("\n  Timeline · CPU profiler · Memory (tabs)\n", _rgb(C_DIM), size=10))
        return parts

    def update_content(self):
        if not self.text_view:
            return
        parts = self.build_attributed()
        result = parts[0]
        for p in parts[1:]:
            result = result.mutableCopy()
            result.appendAttributedString_(p)
        self.text_view.textStorage().setAttributedString_(result)

    def sync_visibility(self):
        if self.config_get_show():
            if self.is_visible():
                self.update_content()
            else:
                self.show()
        elif self.is_visible():
            self.update_content()

    def config_get_show(self):
        return self.app.config.get("show_desktop_window", False)


class FlutterMonitorApp(rumps.App):
    def __init__(self):
        super().__init__(APP_NAME, title="Perf: …", quit_button=None)
        self.config = load_config()
        self.latest_views = []
        self.last_error = None
        self.last_update = None
        self.is_refreshing = False
        self.desktop_panel = DesktopPanel(self)
        self._build_initial_menu()
        self.timer = rumps.Timer(self.on_timer, self.config["interval_seconds"])
        self.timer.start()
        self.refresh_async()

    def _build_initial_menu(self):
        self.menu = [
            rumps.MenuItem("Profiling: starting…", callback=None),
            None,
            rumps.MenuItem("Capture timeline", callback=self.refresh_now),
            rumps.MenuItem("Pin widget trace…", callback=self.add_target),
            rumps.MenuItem("Unpin trace…", callback=self.remove_target),
            rumps.MenuItem("Rename trace label…", callback=self.rename_target),
            rumps.MenuItem("Sampling interval…", callback=self.set_interval),
            None,
            rumps.MenuItem("Show Performance panel", callback=self.toggle_desktop_window),
            rumps.MenuItem("Reveal trace config", callback=self.show_config_path),
            rumps.MenuItem("Open config in Finder", callback=self.open_config_in_finder),
            None,
            rumps.MenuItem("結束程式", callback=self.quit_app),
            rumps.MenuItem("About DevTools", callback=self.about),
        ]

    def on_timer(self, _):
        self.refresh_async()

    def refresh_now(self, _):
        self.refresh_async(force=True)

    def refresh_async(self, force=False):
        if self.is_refreshing and not force:
            return
        self.is_refreshing = True
        threading.Thread(target=self.refresh_data, daemon=True).start()

    def refresh_data(self):
        try:
            targets = self.config.get("targets", [])
            alias_map = {
                str(item.get("code", "")).strip(): item.get("alias", item.get("code", ""))
                for item in targets
            }
            quotes = fetch_targets(targets)
            self.latest_views = [quote_to_perf_view(q, alias_map) for q in quotes]
            self.last_error = None
            self.last_update = datetime.now().strftime("%H:%M:%S")
        except Exception as e:
            self.last_error = str(e)
            self.last_update = datetime.now().strftime("%H:%M:%S")
        finally:
            self.is_refreshing = False
            callAfter(self.rebuild_menu)

    def rebuild_menu(self):
        self.menu.clear()
        total = len(self.config.get("targets", []))
        ok = len(self.latest_views)

        if self.last_error:
            self.title = "Perf: ERR"
            self.menu.add(rumps.MenuItem(f"Trace error · {self.last_update or '—'}", callback=None))
            self.menu.add(rumps.MenuItem(self.last_error[:72], callback=None))
        else:
            if self.config.get("show_price_in_bar") and self.latest_views:
                self.title = bar_title(self.latest_views, ok, total)
            else:
                self.title = bar_title(self.latest_views, ok, total) if self.latest_views else "Perf: idle"
            self.menu.add(rumps.MenuItem(f"Recording · {self.last_update or '—'} · {ok}/{total} traces", callback=None))

        self.menu.add(None)

        if not self.latest_views:
            self.menu.add(rumps.MenuItem("No pinned traces", callback=None))
        else:
            for view in self.latest_views:
                self.menu.add(rumps.MenuItem(menu_line(view), callback=None))
                if not self.config.get("compact_mode", True):
                    self.menu.add(rumps.MenuItem(
                        f"  ui {view['ui_ms']} · build {view['build_ms']} · raster {view['raster_ms']} · "
                        f"rebuilds {view['rebuilds']} · {view['shader_delta']}",
                        callback=None,
                    ))

        self.menu.add(None)
        self.menu.add(rumps.MenuItem("Capture timeline", callback=self.refresh_now))
        self.menu.add(rumps.MenuItem("Pin widget trace…", callback=self.add_target))
        self.menu.add(rumps.MenuItem("Unpin trace…", callback=self.remove_target))
        self.menu.add(rumps.MenuItem("Rename trace label…", callback=self.rename_target))
        self.menu.add(rumps.MenuItem("Sampling interval…", callback=self.set_interval))

        compact = rumps.MenuItem("Compact timeline rows", callback=self.toggle_compact_mode)
        compact.state = bool(self.config.get("compact_mode", True))
        self.menu.add(compact)

        overlay = rumps.MenuItem("Show frame ms in menu bar", callback=self.toggle_bar_price)
        overlay.state = bool(self.config.get("show_price_in_bar", False))
        self.menu.add(overlay)

        panel = rumps.MenuItem("Show Performance panel", callback=self.toggle_desktop_window)
        panel.state = bool(self.config.get("show_desktop_window", False))
        self.menu.add(panel)

        on_top = rumps.MenuItem("Panel always on top", callback=self.toggle_desktop_on_top)
        on_top.state = bool(self.config.get("desktop_always_on_top", True))
        self.menu.add(on_top)

        self.menu.add(None)
        self.menu.add(rumps.MenuItem("Reveal trace config", callback=self.show_config_path))
        self.menu.add(rumps.MenuItem("Open config in Finder", callback=self.open_config_in_finder))
        self.menu.add(None)
        self.menu.add(rumps.MenuItem("結束程式", callback=self.quit_app))
        self.menu.add(rumps.MenuItem("About DevTools", callback=self.about))

        if self.config.get("show_desktop_window"):
            if self.desktop_panel.is_visible():
                self.desktop_panel.update_content()
            else:
                self.desktop_panel.show()
        elif self.desktop_panel.is_visible():
            self.desktop_panel.update_content()

    def toggle_desktop_window(self, _):
        self.desktop_panel.toggle()
        self.rebuild_menu()

    def toggle_desktop_on_top(self, sender):
        self.config["desktop_always_on_top"] = not self.config.get("desktop_always_on_top", True)
        save_config(self.config)
        self.desktop_panel._apply_window_level()
        self.rebuild_menu()

    def add_target(self, _):
        w = rumps.Window(
            message=(
                "Pin widget trace\n\n"
                "Format: id,pool,label\n"
                "  id    internal channel (e.g. 2330)\n"
                "  pool  isolate pool: tse | otc\n"
                "  label timeline name\n\n"
                "Example:\n"
                "2330,tse,RenderViewport::build()"
            ),
            title="Pin Widget Trace",
            default_text="2330,tse,RenderViewport::build()",
            ok="Pin",
            cancel="Cancel",
            dimensions=(380, 200),
        )
        r = w.run()
        if not r.clicked:
            return
        parts = [p.strip() for p in r.text.strip().split(",", 2)]
        if len(parts) < 3:
            rumps.alert("Format", "Use: id,pool,label")
            return
        code, market, alias = parts
        if not code:
            rumps.alert("Input", "id cannot be empty.")
            return
        market = market.lower()
        if market not in ("tse", "otc"):
            rumps.alert("Input", "pool must be tse or otc.")
            return
        targets = self.config.setdefault("targets", [])
        for item in targets:
            if str(item.get("code")) == code:
                item["market"] = market
                item["alias"] = alias
                break
        else:
            targets.append({"code": code, "market": market, "alias": alias})
        save_config(self.config)
        self.refresh_async(force=True)

    def remove_target(self, _):
        current = "\n".join(
            f"{i.get('code')} · {i.get('alias')}" for i in self.config.get("targets", [])
        )
        w = rumps.Window(
            message=f"Pinned traces:\n{current}\n\nTrace id to unpin:",
            title="Unpin Trace",
            default_text="",
            ok="Unpin",
            cancel="Cancel",
            dimensions=(360, 180),
        )
        r = w.run()
        if not r.clicked:
            return
        code = r.text.strip()
        if not code:
            return
        before = len(self.config.get("targets", []))
        self.config["targets"] = [
            i for i in self.config.get("targets", []) if str(i.get("code")) != code
        ]
        save_config(self.config)
        if before == len(self.config["targets"]):
            rumps.alert("Not found", f"No trace id: {code}")
        self.refresh_async(force=True)

    def rename_target(self, _):
        current = "\n".join(
            f"{i.get('code')} · {i.get('alias')}" for i in self.config.get("targets", [])
        )
        w = rumps.Window(
            message=(
                f"Pinned traces:\n{current}\n\n"
                "Format: id,new label\n"
                "Example: 2330,RenderViewport::build()"
            ),
            title="Rename Trace",
            default_text="2330,RenderViewport::build()",
            ok="Save",
            cancel="Cancel",
            dimensions=(360, 190),
        )
        r = w.run()
        if not r.clicked:
            return
        parts = [p.strip() for p in r.text.strip().split(",", 1)]
        if len(parts) < 2:
            rumps.alert("Format", "Use: id,new label")
            return
        code, alias = parts
        found = False
        for item in self.config.get("targets", []):
            if str(item.get("code")) == code:
                item["alias"] = alias
                found = True
                break
        if not found:
            rumps.alert("Not found", f"No trace id: {code}")
            return
        save_config(self.config)
        self.refresh_async(force=True)

    def set_interval(self, _):
        w = rumps.Window(
            message="Sampling interval (seconds).\nRecommended: 20+",
            title="Sampling Interval",
            default_text=str(self.config.get("interval_seconds", 20)),
            ok="Save",
            cancel="Cancel",
            dimensions=(320, 120),
        )
        r = w.run()
        if not r.clicked:
            return
        try:
            sec = int(r.text.strip())
            if sec < 5:
                rumps.alert("Interval", "Use 5 seconds or more.")
                return
        except Exception:
            rumps.alert("Input", "Enter a number.")
            return
        self.config["interval_seconds"] = sec
        save_config(self.config)
        self.timer.stop()
        self.timer = rumps.Timer(self.on_timer, sec)
        self.timer.start()
        self.refresh_async(force=True)

    def toggle_compact_mode(self, sender):
        self.config["compact_mode"] = not self.config.get("compact_mode", True)
        save_config(self.config)
        self.rebuild_menu()

    def toggle_bar_price(self, sender):
        self.config["show_price_in_bar"] = not self.config.get("show_price_in_bar", False)
        save_config(self.config)
        self.rebuild_menu()

    def show_config_path(self, _):
        rumps.alert("Trace config", f"{CONFIG_PATH}\n\nEdit pinned traces and sampling options.")

    def open_config_in_finder(self, _):
        subprocess.run(["open", "-R", str(CONFIG_PATH)], check=False)

    def quit_app(self, _):
        rumps.quit_application()

    def about(self, _):
        rumps.alert(
            APP_NAME,
            "Flutter DevTools — Performance overlay\n\n"
            "Menu bar timeline sampler with optional Performance panel.\n"
            "Pin widget traces and capture timelines on an interval.",
        )


if __name__ == "__main__":
    FlutterMonitorApp().run()

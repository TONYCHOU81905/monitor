"""
建置 macOS 應用程式：python3 setup_app.py py2app

產出 dist/Flutter DevTools.app，可拖進「應用程式」資料夾雙擊開啟。
"""
from setuptools import setup

APP = ["flutter_monitor.py"]
DATA_FILES = []

OPTIONS = {
    "argv_emulation": False,
    "iconfile": None,
    "plist": {
        "CFBundleName": "Flutter DevTools",
        "CFBundleDisplayName": "Flutter DevTools",
        "CFBundleIdentifier": "com.flutter.devtools.perf",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "LSMinimumSystemVersion": "11.0",
        "LSUIElement": True,
        "NSHighResolutionCapable": True,
    },
    "packages": ["rumps", "requests", "objc"],
    "includes": ["AppKit", "Foundation", "PyObjCTools"],
}

setup(
    name="Flutter DevTools",
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)

# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all

TARGET_ARCH = os.environ.get("SENDTOMAC_ARCH", "universal2")

datas = [("web", "web")]
binaries = []
hiddenimports = ["webview", "webview.platforms.cocoa", "menu_app", "staging"]
for package in ("webview", "objc", "Foundation", "AppKit", "WebKit", "CoreFoundation"):
    extra_datas, extra_binaries, extra_hidden = collect_all(package)
    datas += extra_datas
    binaries += extra_binaries
    hiddenimports += extra_hidden

a = Analysis(
    ["site.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SendToMac",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=TARGET_ARCH,
    codesign_identity=None,
    entitlements_file=None,
    icon="icon.icns",
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="SendToMac",
)
app = BUNDLE(
    coll,
    name="SendToMac.app",
    icon="icon.icns",
    bundle_identifier="app.sendtomac",
    info_plist={
        "CFBundleDisplayName": "SendToMac",
        "CFBundleName": "SendToMac",
        "CFBundleShortVersionString": "2.4.2",
        "CFBundleVersion": "2.4.2",
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "11.0",
        "LSUIElement": True,
        "NSLocalNetworkUsageDescription": "SendToMac uses your Wi-Fi so the phone can scan the code and send a file.",
    },
)

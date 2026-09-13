# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ["site.py"],
    pathex=[],
    binaries=[],
    datas=[("web", "web")],
    hiddenimports=[],
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
    target_arch=None,
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
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "11.0",
        "NSLocalNetworkUsageDescription": "SendToMac uses your Wi-Fi so the phone can scan the code and send a file.",
    },
)

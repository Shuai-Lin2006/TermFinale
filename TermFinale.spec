# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置（macOS 生成 .app，Windows 生成 .exe）。

用法：
    pip install pyinstaller
    python -m PyInstaller --noconfirm --clean TermFinale.spec
产物：
    dist/TermFinale.app          (macOS)
    dist/TermFinale/TermFinale.exe (Windows)
"""
from PyInstaller.utils.hooks import collect_data_files

datas = []
datas += collect_data_files("customtkinter")   # 主题/皮肤资源，缺了会启动即崩
datas += collect_data_files("certifi")         # HTTPS 证书

hiddenimports = [
    "fitz",
    "pymupdf",
    "sqlalchemy.dialects.sqlite",
    "pptx",
    "docx",
    "PIL._tkinter_finder",
    "openai",
    "httpx",
    "loguru",
]

# 这些库只服务于开发期的可选功能，排除后体积小很多
excludes = [
    "matplotlib", "numpy", "pandas", "scipy", "onnxruntime",
    "pymupdf_layout", "pymupdf4llm", "zhipuai",
    "pytest", "tests", "legacy", "tools",
]

a = Analysis(
    ["launcher.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="TermFinale",
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
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="TermFinale",
)
app = BUNDLE(
    coll,
    name="TermFinale.app",
    icon=None,
    bundle_identifier="com.termfinale.desktop",
    info_plist={
        "NSHighResolutionCapable": True,
        "CFBundleShortVersionString": "2.0.0",
        "LSMinimumSystemVersion": "11.0",
    },
)

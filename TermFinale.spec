# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置（macOS 生成 .app，Windows 生成 .exe）。

用法：
    pip install pyinstaller
    python -m PyInstaller --noconfirm --clean TermFinale.spec
产物：
    dist/TermFinale.app          (macOS)
    dist/TermFinale/TermFinale.exe (Windows)
"""
import os as _os
import sys as _sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

_ICON = _os.path.join(SPECPATH, "assets", "icon.icns" if _sys.platform == "darwin" else "icon.ico")
if not _os.path.exists(_ICON):
    _ICON = None

datas = []
datas += collect_data_files("customtkinter")   # 主题/皮肤资源，缺了会启动即崩
datas += collect_data_files("certifi")
datas += collect_data_files("docx")          # Word 默认模板/页脚，缺了导出直接 500
datas += [("core/assets", "core/assets")]
datas += [("web", "web")]                         # legacy reader / KaTeX
datas += [("web_v2", "web_v2")]                   # 当前学习台 UI
datas += [("THIRD_PARTY_NOTICES.md", ".")]
datas += [("licenses", "licenses")]
datas += [("tools/docling_structure.py", "tools")]
_typst_name = "typst.exe" if _sys.platform == "win32" else "typst"
_typst_path = _os.path.join(SPECPATH, "tools", _typst_name)
if _os.path.exists(_typst_path):
    datas += [(_typst_path, "tools")]
try:
    datas += collect_data_files("opencc")
except Exception:
    pass

hiddenimports = [
    "tkinter",
    "fitz",
    "pymupdf",
    "sqlalchemy.dialects.sqlite",
    "pptx",
    "docx",
    "PIL._tkinter_finder",
    "openai",
    "httpx",
    "loguru",
    "webview",
    "clr",
    "pythonnet",
    "uvicorn",
    "fastapi",
    "starlette",
    "python_multipart",
    "opencc",
    "tfv2.product.backup",
    "tfv2.render.typst_lecture",
    "tfv2.render.typst_math",
    "tfv2.render.formula_asset",
]

if _sys.platform == "darwin":
    hiddenimports += ["webview.platforms.cocoa"]
elif _sys.platform == "win32":
    hiddenimports += ["webview.platforms.edgechromium", "webview.platforms.winforms", "webview.platforms.win32"]

# 音频转写：dashscope 内部有动态导入，显式收集
try:
    hiddenimports += collect_submodules("dashscope")
except Exception:
    pass

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
    icon=_ICON,
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
if _sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="TermFinale.app",
        icon=_ICON,
        bundle_identifier="com.termfinale.desktop",
        info_plist={
            "NSHighResolutionCapable": True,
            "CFBundleShortVersionString": "0.4.9",
            "LSMinimumSystemVersion": "11.0",
        },
    )

"""一键打包：检查环境 → 调 PyInstaller → 打印产物路径。

用法：python tools/build.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MIN_OK = (3, 10)
RECOMMENDED = (3, 12)


def main() -> int:
    version = sys.version_info[:3]
    print(f"Python {version[0]}.{version[1]}.{version[2]}  ({sys.executable})")
    if version[:2] > RECOMMENDED:
        print(f"⚠️  建议用 Python {RECOMMENDED[0]}.{RECOMMENDED[1]} 打包："
              "PyInstaller 对新版本解释器支持滞后，可能出现奇怪的导入错误。")
    if version[:2] < MIN_OK:
        print("❌ Python 版本过低，至少需要 3.10")
        return 1

    if shutil.which("pyinstaller") is None and not _has_module("PyInstaller"):
        print("❌ 未安装 PyInstaller，请先执行：pip install pyinstaller")
        return 1

    print("开始打包（首次约 1~3 分钟）...")
    env = dict(os.environ)
    # 某些环境禁止写 ~/Library，把 PyInstaller 缓存放到项目内
    env.setdefault("PYINSTALLER_CONFIG_DIR", str(ROOT / "build" / ".pyinstaller_cache"))
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "TermFinale.spec"],
        cwd=ROOT,
        env=env,
    )
    if result.returncode != 0:
        print("❌ 打包失败，请查看上方日志")
        return result.returncode

    print("\n✅ 打包完成")
    for candidate in (ROOT / "dist" / "TermFinale.app", ROOT / "dist" / "TermFinale"):
        if candidate.exists():
            print(f"   产物：{candidate}")
    return 0


def _has_module(name: str) -> bool:
    import importlib.util

    return importlib.util.find_spec(name) is not None


if __name__ == "__main__":
    raise SystemExit(main())

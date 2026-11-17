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

# Windows 控制台默认不是 UTF-8，直接 print 中文会 UnicodeEncodeError
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
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

    # 写入构建信息，界面上可直接确认版本
    import datetime
    import subprocess as _sp
    try:
        git_hash = _sp.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                    text=True, stderr=_sp.DEVNULL).strip()
    except Exception:
        git_hash = "dev"
    build_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        version = (ROOT / "VERSION").read_text(encoding="utf-8").strip() or "0.4.0"
    except Exception:
        version = "0.4.0"
    (ROOT / "core" / "build_info.py").write_text(
        f'"""构建信息：由 tools/build.py 自动生成。"""\n'
        f'VERSION = "{version}"\nBUILD_TIME = "{build_time}"\nGIT_HASH = "{git_hash}"\n',
        encoding="utf-8")
    print(f"构建信息：v{version} · {build_time} · {git_hash}")

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
    app_path = None
    for candidate in (ROOT / "dist" / "TermFinale.app", ROOT / "dist" / "TermFinale"):
        if candidate.exists():
            print(f"   产物：{candidate}")
            if candidate.suffix == ".app":
                app_path = candidate

    if "--desktop" in sys.argv and app_path and app_path.suffix == ".app":
        dest = Path.home() / "Desktop" / "TermFinale.app"
        if dest.exists():
            shutil.rmtree(dest)
        subprocess.run(["ditto", str(app_path), str(dest)], check=True)
        subprocess.run(["xattr", "-dr", "com.apple.quarantine", str(dest)],
                       check=False, stderr=subprocess.DEVNULL)
        print(f"   已安装到桌面：{dest}")
    return 0


def _has_module(name: str) -> bool:
    import importlib.util

    return importlib.util.find_spec(name) is not None


if __name__ == "__main__":
    raise SystemExit(main())

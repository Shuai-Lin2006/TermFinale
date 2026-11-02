"""跨平台路径与数据目录（唯一真源）。

所有需要读写用户数据的模块都必须从这里取路径。
禁止再出现 ``os.path.join(os.path.dirname(__file__), ...)`` 这类写法：
打包成 .app / .exe 后 ``__file__`` 会指向临时解压目录，数据会丢。

目录布局::

    <data_dir>/
        term_finale_pro.db
        assets/          # 解析抽出的图片
        logs/            # 日志
        debug/           # 原始 AI 输出、指标、失败样本
        outputs/         # 生成物（后续阶段接管默认输出位置）
"""
from __future__ import annotations

import os
import shutil
import sys
import warnings
from pathlib import Path

APP_NAME = "TermFinale"
DB_FILENAME = "term_finale_pro.db"

_ROOT: Path | None = None


# --------------------------------------------------------------------------- #
# 基础判定
# --------------------------------------------------------------------------- #
def is_frozen() -> bool:
    """是否运行在 PyInstaller 冻结环境。"""
    return bool(getattr(sys, "frozen", False))


def project_root() -> Path:
    """源码根目录 / 打包后可执行文件所在目录（**不用于存数据**）。"""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _platform_default() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    if os.name == "nt":
        base = os.environ.get("APPDATA")
        return Path(base) / APP_NAME if base else Path.home() / "AppData" / "Roaming" / APP_NAME
    base = os.environ.get("XDG_DATA_HOME")
    return Path(base) / APP_NAME if base else Path.home() / ".local" / "share" / APP_NAME


def _candidate_root() -> Path:
    override = os.environ.get("TERMFINALE_HOME", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    try:  # 可选依赖：有就用，没有就手写兜底
        from platformdirs import user_data_dir

        return Path(user_data_dir(APP_NAME, appauthor=False, roaming=False))
    except Exception:
        return _platform_default()


def _is_writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def data_dir() -> Path:
    """用户数据根目录。首次调用时确定并缓存，带只读兜底。"""
    global _ROOT
    if _ROOT is not None:
        return _ROOT

    candidate = _candidate_root()
    if _is_writable(candidate):
        _ROOT = candidate
        return _ROOT

    # 兜底：用户目录不可写（沙箱/权限异常）时退到项目内，保证程序能启动
    fallback = project_root() / ".termfinale_home"
    fallback.mkdir(parents=True, exist_ok=True)
    warnings.warn(f"数据目录不可写：{candidate}，已回退到 {fallback}", RuntimeWarning)
    _ROOT = fallback
    return _ROOT


# --------------------------------------------------------------------------- #
# 子目录
# --------------------------------------------------------------------------- #
def db_path() -> Path:
    return data_dir() / DB_FILENAME


def assets_dir() -> Path:
    return data_dir() / "assets"


def logs_dir() -> Path:
    return data_dir() / "logs"


def debug_dir() -> Path:
    return data_dir() / "debug"


def outputs_dir() -> Path:
    return data_dir() / "outputs"


def ensure_dirs() -> None:
    for d in (data_dir(), assets_dir(), logs_dir(), debug_dir(), outputs_dir()):
        d.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------- #
# 旧数据迁移（只复制，绝不移动/删除）
# --------------------------------------------------------------------------- #
def migrate_legacy() -> dict:
    """把源码目录里的旧 DB 与 assets 复制到新的用户数据目录。

    返回报告，便于调用方写日志。旧文件保持原样，用户随时可以反悔。
    """
    report: dict = {}
    src_root = project_root()
    try:
        if src_root.resolve() == data_dir().resolve():
            return {"status": "skipped", "reason": "same-root"}
    except OSError:
        pass

    ensure_dirs()

    src_db = src_root / DB_FILENAME
    dst_db = db_path()
    if src_db.exists() and not dst_db.exists():
        try:
            shutil.copy2(src_db, dst_db)
            report["db"] = f"copied {src_db.name}"
        except OSError as exc:
            report["db"] = f"failed: {exc}"

    src_assets = src_root / "assets_images"
    dst_assets = assets_dir()
    if src_assets.is_dir():
        has_files = any(dst_assets.iterdir())
        if not has_files:
            try:
                shutil.copytree(src_assets, dst_assets, dirs_exist_ok=True)
                report["assets"] = f"copied {len(list(dst_assets.iterdir()))} files"
            except OSError as exc:
                report["assets"] = f"failed: {exc}"
        else:
            report["assets"] = "skipped (target not empty)"

    if not report:
        report["status"] = "nothing-to-migrate"
    return report


def describe() -> str:
    """一行人类可读的路径说明，用于启动日志。"""
    return (
        f"data_dir={data_dir()} | db={db_path().exists() and 'exists' or 'new'} | "
        f"frozen={is_frozen()}"
    )


if __name__ == "__main__":  # 手动检查
    ensure_dirs()
    print(describe())
    print("migrate:", migrate_legacy())

"""从备份恢复 TermFinale 数据库（只动 DB，不删上传副本/原资料）。

用法：
    # 先退出 TermFinale，再执行
    python tools/restore_backup.py --backup "~/Library/.../backups/xxx.db" --yes

恢复前会自动把当前库另存为 backups/pre_restore_<时间>.db；恢复后校验表与行数。
没有 --yes 只做检查，不写入。
"""
from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import sys
import time
from pathlib import Path

REQUIRED_TABLES = {"courses", "materials", "generated_files"}
COUNT_TABLES = ("courses", "materials", "generated_files")


def inspect_backup(path: str | Path) -> dict:
    p = Path(path).expanduser()
    if not p.is_file():
        raise FileNotFoundError(f"备份不存在：{p}")
    with p.open("rb") as fh:
        if fh.read(16) != b"SQLite format 3\x00":
            raise ValueError("不是 SQLite 数据库文件")
    con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    try:
        integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
        names = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        missing = REQUIRED_TABLES - names
        if missing:
            raise ValueError("备份缺少表：" + "、".join(sorted(missing)))
        counts = {}
        for table in COUNT_TABLES:
            counts[table] = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        return {"path": str(p), "integrity": integrity, "counts": counts}
    finally:
        con.close()


def restore(backup: str | Path, data_dir: str | Path, yes: bool = False) -> dict:
    info = inspect_backup(backup)
    data = Path(data_dir).expanduser()
    target = data / "term_finale_pro.db"
    if not yes:
        return {"dry_run": True, "backup": info, "target": str(target)}
    data.mkdir(parents=True, exist_ok=True)
    pre = None
    if target.exists():
        pre_dir = data / "backups"
        pre_dir.mkdir(exist_ok=True)
        pre = pre_dir / f"pre_restore_{time.strftime('%Y%m%d_%H%M%S')}.db"
        # 用 SQLite backup API，而不是 copy2：把当前库未 checkpoint 的 WAL 也一起带走
        src = sqlite3.connect(target)
        dst = sqlite3.connect(pre)
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()
    tmp = data / "term_finale_pro.db.tmp"
    shutil.copy2(Path(backup).expanduser(), tmp)
    # 旧 WAL/SHM 必须清掉，否则 SQLite 可能把旧日志套到新库上
    for suffix in ("-wal", "-shm"):
        try:
            (data / f"term_finale_pro.db{suffix}").unlink()
        except FileNotFoundError:
            pass
    os.replace(tmp, target)
    after = inspect_backup(target)
    return {"dry_run": False, "pre_restore": str(pre) if pre else None,
            "target": str(target), "backup": info, "after": after}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="恢复 TermFinale 数据库备份（不删原资料）")
    ap.add_argument("--backup", required=True, help="备份 .db 路径")
    ap.add_argument("--data-dir", default=None, help="数据目录；默认 TermFinale 标准目录")
    ap.add_argument("--yes", action="store_true", help="确认写入；没有它只检查")
    args = ap.parse_args(argv)

    data_dir = args.data_dir
    if not data_dir:
        # 与 core.paths 保持一致，但不 import 整个应用
        if sys.platform == "darwin":
            data_dir = "~/Library/Application Support/TermFinale"
        elif os.name == "nt":
            data_dir = os.path.join(os.environ.get("APPDATA", "~"), "TermFinale")
        else:
            data_dir = "~/.local/share/TermFinale"

    try:
        result = restore(args.backup, data_dir, yes=args.yes)
    except Exception as exc:  # noqa: BLE001
        print(f"恢复失败：{exc}", file=sys.stderr)
        return 2

    info = result["backup"]
    print(f"备份：{info['path']}")
    print(f"完整性：{info['integrity']} · 课程 {info['counts']['courses']} / "
          f"资料 {info['counts']['materials']} / 生成物 {info['counts']['generated_files']}")
    if result["dry_run"]:
        print(f"未写入。确认后加 --yes；目标：{result['target']}")
        return 0
    if result.get("pre_restore"):
        print(f"恢复前当前库已另存：{result['pre_restore']}")
    print(f"已恢复：{result['target']}")
    print(f"恢复后：课程 {result['after']['counts']['courses']} / "
          f"资料 {result['after']['counts']['materials']} / "
          f"生成物 {result['after']['counts']['generated_files']}")
    print("上传副本与桌面原资料未动；重启 TermFinale 生效。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

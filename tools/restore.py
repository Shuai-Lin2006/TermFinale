"""从备份恢复：默认拒绝覆盖；先备份当前 DB。"""
from __future__ import annotations
import argparse, json, shutil, sqlite3, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def restore(zip_path: Path, replace: bool = False) -> None:
    with zipfile.ZipFile(zip_path) as z:
        names = set(z.namelist())
        if "product.sqlite3" not in names or "manifest.json" not in names:
            raise ValueError("不是 TermFinale 备份")
        if not replace and (ROOT / "data/product.sqlite3").exists():
            raise ValueError("数据库已存在；加 --replace 才覆盖")
        current = ROOT / "data/product.sqlite3"
        if current.exists():
            shutil.copy2(current, current.with_suffix(".sqlite3.before-restore"))
        tmp = ROOT / "data/.restore.sqlite3"
        tmp.write_bytes(z.read("product.sqlite3"))
        conn = sqlite3.connect(tmp)
        if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            conn.close(); tmp.unlink(missing_ok=True); raise ValueError("备份数据库损坏")
        conn.close(); tmp.replace(current)
        data = json.loads(z.read("artifacts.json"))
        for item in data:
            p = ROOT / "data/artifacts" / item["id"] / "project.json"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(item["project"], encoding="utf-8")
    print("restored", len(data), "artifacts")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("zip")
    ap.add_argument("--replace", action="store_true")
    a = ap.parse_args()
    restore(Path(a.zip), a.replace)

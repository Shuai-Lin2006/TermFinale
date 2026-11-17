"""一致性备份：SQLite + artifact 配置；默认不含大 PDF/图片。"""
from __future__ import annotations
import argparse, json, os, sqlite3, zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = Path(os.getenv("TFV2_DATA_ROOT", str(ROOT / "data"))).expanduser()


def backup(out_dir: Path, include_assets: bool = False) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = out_dir / f"termfinale-{stamp}.zip"
    db = DATA_ROOT / "product.sqlite3"
    tmp = out_dir / f".backup-{stamp}.sqlite3"
    src = sqlite3.connect(db)
    dst = sqlite3.connect(tmp)
    with dst:
        src.backup(dst)
    dst.close(); src.close()
    artifacts = []
    for p in sorted((DATA_ROOT / "artifacts").glob("*/project.json")):
        artifacts.append({"id": p.parent.name, "project": p.read_text(encoding="utf-8")})
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(tmp, "product.sqlite3")
        z.writestr("artifacts.json", json.dumps(artifacts, ensure_ascii=False, indent=2))
        z.writestr("manifest.json", json.dumps({"created": stamp, "include_assets": include_assets,
                                                "artifacts": len(artifacts)}, ensure_ascii=False, indent=2))
        if include_assets:
            for p in (DATA_ROOT / "artifacts").rglob("*"):
                if p.is_file() and p.name in ("lecture.pdf", "lecture.docx"):
                    z.write(p, str(p.relative_to(DATA_ROOT / "artifacts")))
    tmp.unlink(missing_ok=True)
    return path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/backups")
    ap.add_argument("--assets", action="store_true")
    a = ap.parse_args()
    print(backup(ROOT / a.out, a.assets))

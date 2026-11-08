"""图文配对审计 CLI：python tools/image_pairing_report.py <generated.md>"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import paths
from core.database import get_db_session, Material
from core.parser import extract_text_from_file
from core.quality.image_pairing import audit_images


def main():
    md_path = Path(sys.argv[1])
    mid = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    db = get_db_session()
    try:
        m = db.query(Material).filter(Material.id == mid).first()
        if not m:
            raise SystemExit("material not found")
        pages = extract_text_from_file(m.file_path)
    finally:
        db.close()
    r = audit_images(md_path.read_text(encoding="utf-8"), pages, paths.assets_dir())
    print(f"total={r.total} paired={r.paired} rate={r.rate:.2%}")
    for i in r.issues[:10]:
        print(f"- {i.file} P.{i.page}: {i.reason}")


if __name__ == "__main__":
    main()

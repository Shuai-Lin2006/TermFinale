import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import paths
from core.database import get_db_session, Material
from core.parser import extract_text_from_file
from core.quality.figure_ledger import audit_figures

def main():
    md_path=Path(sys.argv[1]); mid=int(sys.argv[2])
    db=get_db_session()
    try:
        m=db.query(Material).filter(Material.id==mid).first(); pages=extract_text_from_file(m.file_path)
    finally: db.close()
    led=audit_figures(pages,md_path.read_text(encoding='utf-8'),paths.assets_dir())
    print(f"source={led.source} used={led.used} missing={len(led.missing)} orphan={len(led.orphan)} issues={len(led.issues)}")
    for x in led.missing[:20]: print('MISSING',x)
    for x in led.orphan[:10]: print('ORPHAN',x)
    for x in led.issues[:10]: print('ISSUE',x)
if __name__=='__main__': main()


import json
from pathlib import Path
from tfv2.ingest.docling_pages import pages_from_structure
from tfv2.ingest.mineru_router import mineru_ledger,route_pages
d=pages_from_structure(json.loads(Path('data/golden/docling_50p/structure.json').read_text()),material='docling50')
m=mineru_ledger(Path('data/golden/mineru_50p').read_text(encoding='utf-8'))
r=route_pages(d,m)
Path('data/golden/routed_50p.json').write_text(json.dumps({'pages':[p.model_dump(mode='json') for p in r.pages]},ensure_ascii=False,indent=2),encoding='utf-8')
print({'pages':r.page_count,'chars':sum(len(p.text) for p in r.pages),'images':sum(len(p.images) for p in r.pages),'formula_pages':sum(1 for p in r.pages if p.formula_damage),'parser':r.parser_version})

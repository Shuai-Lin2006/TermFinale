
import json
from pathlib import Path
from tfv2.ingest.mineru_router import mineru_ledger,route_pages
from tfv2.domain.page import Page,PageLedger,PageQuality
raw=json.loads(Path('data/golden/docling_10p/pages.json').read_text()); rows=raw['pages']
d=PageLedger(material='m',page_count=len(rows),source_hash='docling',parser_version='docling',pages=[Page(material='m',page_no=int(x['page_no']),text=x.get('text') or '',quality=PageQuality.OCR) for x in rows])
m=mineru_ledger(Path('data/golden/mineru_10p').read_text(encoding='utf-8'))
r=route_pages(d,m)
Path('data/golden/routed_10p.json').write_text(json.dumps({'pages':[p.model_dump(mode='json') for p in r.pages]},ensure_ascii=False,indent=2),encoding='utf-8')
print({'docling':len(d.pages),'mineru':len(m.pages),'routed':len(r.pages),'mineru_pages':sum(1 for p in r.pages if p.material=='mineru'),'chars':sum(len(p.text) for p in r.pages)})

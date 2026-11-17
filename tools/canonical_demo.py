
import json
from pathlib import Path
from tfv2.domain.page import Page,PageLedger,PageQuality
from tfv2.canonical.pipeline import run_canonical
raw=json.loads(Path('data/golden/docling_10p/pages.json').read_text()); rows=raw['pages']
ledger=PageLedger(material='模电150-159',page_count=len(rows),source_hash='docling',parser_version='docling',pages=[Page(material='模电150-159',page_no=int(x['page_no']),text=x.get('text') or '',quality=PageQuality.OCR) for x in rows])
doc=run_canonical(ledger,document_id='canonical_10p')
Path('data/golden/canonical_10p.json').write_text(json.dumps(doc.model_dump(mode='json'),ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'pages':doc.page_count,'facts':len(doc.facts),'plans':len(doc.plans),'coverage':doc.coverage,'status':doc.status,'issues':doc.issues,'kinds':sorted({f.kind.value for f in doc.facts})},ensure_ascii=False))

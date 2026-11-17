
import json,time
from pathlib import Path
from tfv2.canonical.orchestrator import CanonicalOrchestrator
from tfv2.canonical.parsers import DoclingStructureParser
source=json.loads(Path('data/golden/docling_10p/structure.json').read_text()); source['material']='模电150-159'
orch=CanonicalOrchestrator(DoclingStructureParser(),cache_dir='data/cache/canonical')
t=time.time(); a=orch.run(source,document_id='canonical_10p_orch'); t1=round(time.time()-t,2)
t=time.time(); b=orch.run(source,document_id='canonical_10p_orch'); t2=round(time.time()-t,2)
Path('data/golden/canonical_10p_orch.json').write_text(json.dumps(a.model_dump(mode='json'),ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'pages':a.page_count,'facts':len(a.facts),'plans':len(a.plans),'coverage':a.coverage,'status':a.status,'first_s':t1,'cached_s':t2,'same':a.facts==b.facts},ensure_ascii=False))

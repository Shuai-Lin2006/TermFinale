
import json
from pathlib import Path
from tfv2.canonical.model import CanonicalDocument
from tfv2.canonical.generate import generate_slots
from tfv2.llm.qwen_text import QwenTextClient
d=CanonicalDocument.model_validate(json.loads(Path('data/golden/canonical_10p.json').read_text()))
ids=[f.fact_id for f in d.facts if f.page in (1,2)]
r=generate_slots(d,QwenTextClient(model='qwen-max'),batch_size=8,fact_ids=ids)
out={'facts':len(ids),'blocks':len(r.blocks),'missing':r.missing,'coverage':r.coverage,'status':r.status,'blocks_data':[b.model_dump() for b in r.blocks]}
Path('data/golden/slots_2p.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:out[k] for k in ('facts','blocks','missing','coverage','status')},ensure_ascii=False))

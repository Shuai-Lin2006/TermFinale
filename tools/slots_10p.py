
import json
from pathlib import Path
from tfv2.canonical.model import CanonicalDocument
from tfv2.canonical.generate import generate_slots
from tfv2.llm.qwen_text import QwenTextClient
p=Path('data/golden/canonical_10p_orch.json')
d=CanonicalDocument.model_validate(json.loads(p.read_text()))
ids=[f.fact_id for f in d.facts]
client=QwenTextClient(model='qwen-max')
r=generate_slots(d,client,batch_size=10,fact_ids=ids)
blocks=[b.model_dump() for b in r.blocks]
out={'facts':len(ids),'blocks':len(blocks),'missing':r.missing,'coverage':r.coverage,'status':r.status,'blocks_data':blocks}
Path('data/golden/slots_10p.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:out[k] for k in ('facts','blocks','missing','coverage','status')},ensure_ascii=False))

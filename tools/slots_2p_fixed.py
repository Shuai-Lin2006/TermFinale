
import json
from pathlib import Path
from tfv2.canonical.model import CanonicalDocument
from tfv2.canonical.generate import generate_slots
from tfv2.llm.qwen_text import QwenTextClient
d=CanonicalDocument.model_validate(json.loads(Path('data/golden/canonical_10p.json').read_text()))
base=json.loads(Path('data/golden/slots_2p.json').read_text())
r=generate_slots(d,QwenTextClient(model='qwen-max'),batch_size=1,fact_ids=["p1-2"])
blocks=base['blocks_data']+[b.model_dump() for b in r.blocks]
seen={b['fact_id'] for b in blocks}; ids={f.fact_id for f in d.facts if f.page in (1,2)}
out={'facts':len(ids),'blocks':len(blocks),'missing':sorted(ids-seen),'coverage':round(len(seen&ids)/len(ids),4),'status':'validated' if ids<=seen else 'partial','blocks_data':blocks}
Path('data/golden/slots_2p_fixed.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:out[k] for k in ('facts','blocks','missing','coverage','status')},ensure_ascii=False))

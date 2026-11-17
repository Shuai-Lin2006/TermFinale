
import json
from pathlib import Path
from tfv2.canonical.model import CanonicalDocument
from tfv2.canonical.generate import generate_slots
from tfv2.llm.qwen_text import QwenTextClient
d=CanonicalDocument.model_validate(json.loads(Path('data/golden/canonical_10p_orch.json').read_text()))
base=json.loads(Path('data/golden/slots_10p.json').read_text()); client=QwenTextClient(model='qwen-max')
blocks=base['blocks_data']; seen={b['fact_id'] for b in blocks}; ids={f.fact_id for f in d.facts}
for fid in base['missing']:
 if fid in seen: continue
 r=generate_slots(d,client,batch_size=1,fact_ids=[fid])
 print(fid,len(r.blocks),r.missing,flush=True)
 for b in r.blocks:
  if b.fact_id not in seen: blocks.append(b.model_dump()); seen.add(b.fact_id)
out={**base,'blocks':len(blocks),'missing':sorted(ids-seen),'coverage':round(len(seen&ids)/len(ids),4),'status':'validated' if ids<=seen else 'partial','blocks_data':blocks}
Path('data/golden/slots_10p_fixed.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:out[k] for k in ('facts','blocks','missing','coverage','status')},ensure_ascii=False))

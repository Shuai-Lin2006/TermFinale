
import json
from pathlib import Path
from tfv2.canonical.model import CanonicalDocument
from tfv2.canonical.synthesize import synthesize_section
from tfv2.llm.qwen_text import QwenTextClient
doc=CanonicalDocument.model_validate(json.loads(Path('data/golden/canonical_10p_orch.json').read_text())); client=QwenTextClient(model='qwen-max')
out=[]
for plan in doc.plans:
 r=synthesize_section(plan,doc.facts,client); out.append(r.model_dump()); print(plan.plan_id,len(r.blocks),r.missing,flush=True)
Path('data/golden/synthesis_10p.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print('plans',len(out),'validated',sum(1 for x in out if x['status']=='validated'),'missing',sum(len(x['missing']) for x in out))

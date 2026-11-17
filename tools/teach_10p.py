
import json
from pathlib import Path
from tfv2.canonical.model import CanonicalDocument
from tfv2.canonical.teach import synthesize_teaching
from tfv2.llm.qwen_text import QwenTextClient
doc=CanonicalDocument.model_validate(json.loads(Path('data/golden/canonical_10p_orch.json').read_text())); client=QwenTextClient(model='qwen-max')
out=[]
for plan in doc.plans:
 r=synthesize_teaching(plan,doc.facts,client); out.append(r.model_dump()); print(plan.plan_id,len(r.blocks),r.missing_facts,r.missing_roles,flush=True)
Path('data/golden/teaching_10p.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print('sections',len(out),'validated',sum(1 for x in out if x['status']=='validated'),'missing_facts',sum(len(x['missing_facts']) for x in out),'missing_roles',sum(len(x['missing_roles']) for x in out))

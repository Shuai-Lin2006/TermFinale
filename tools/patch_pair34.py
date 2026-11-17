
import json
from pathlib import Path
p=Path('data/artifacts/gen_pair_3_4'); sec=json.loads((p/'sections.json').read_text())[0]
for b in sec.get('blocks') or []:
 for r in b.get('source_refs') or []:
  r['page_start']=1 if int(r.get('page_start',3))<=3 else 2; r['page_end']=1 if int(r.get('page_end',3))<=3 else 2
sec['source_refs']=[{'material':'docling','page_start':1,'page_end':2}]
sec['objectives']=['理解镜像电流源与威尔逊电流源']
sec['key_terms']=['参考电流','镜像电流源','威尔逊电流源']
sec['self_test']=['镜像电流源为什么能恒流？']
(p/'sections.json').write_text(json.dumps([sec],ensure_ascii=False,indent=2),encoding='utf-8')
print('patched')

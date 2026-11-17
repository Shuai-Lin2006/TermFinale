
import json,shutil
from pathlib import Path
from tfv2.build import build_project
srcsecs=json.loads(Path('data/artifacts/gen_20261115_123905_f21786/sections.json').read_text())
for start,idx in ((32,6),(38,7)):
 p=Path(f'data/artifacts/gen_100p_pair_{start}_{start+1}'); sec=json.loads(json.dumps(srcsecs[idx]))
 sec['id']=f'第{start//2+1}节'; sec['source_refs']=[{'material':'m','page_start':1,'page_end':2}]
 for b in sec.get('blocks') or []:
  for r in b.get('source_refs') or []: r['page_start']=1; r['page_end']=2
 sec['objectives']=sec.get('objectives') or ['理解本节']
 sec['key_terms']=sec.get('key_terms') or ['核心概念']
 sec['self_test']=sec.get('self_test') or ['能否复述本节？']
 (p/'sections.json').write_text(json.dumps([sec],ensure_ascii=False,indent=2),encoding='utf-8')
 try:
  r=build_project(p/'project.json',pdf=True); print(start,'BUILD',r.get('pdf_pages'),r.get('gate'))
 except Exception as e: print(start,'ERR',type(e).__name__,e)

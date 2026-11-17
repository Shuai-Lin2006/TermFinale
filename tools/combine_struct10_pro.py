
import json,shutil
from pathlib import Path
from tfv2.domain.lecture import SourceRef
from tfv2.build import build_project
src=Path('data/artifacts/gen_fact10_20261115'); dst=Path('data/artifacts/gen_struct10_pro')
if dst.exists(): shutil.rmtree(dst)
dst.mkdir(parents=True); shutil.copytree(src/'source',dst/'source'); (dst/'source_assets').mkdir(exist_ok=True); shutil.copy2(src/'source_pages.json',dst/'source_pages.json')
pr=json.loads((src/'project.json').read_text()); pr.update({'id':dst.name,'page_count':10,'scope_pages':list(range(1,11)),'source_file':'source/'+next((dst/'source').glob('*')).name,'sections_files':['sections.json']}); (dst/'project.json').write_text(json.dumps(pr,ensure_ascii=False,indent=2),encoding='utf-8')
s12=json.loads(Path('data/artifacts/gen_struct2p_20261115/sections.json').read_text())[0]
s34=json.loads(Path('data/artifacts/gen_pair_3_4_pro/sections.json').read_text())[0]
s56=json.loads(Path('data/golden/pair_5_6.json').read_text()); s78=json.loads(Path('data/golden/pair_7_8.json').read_text()); s910=json.loads(Path('data/golden/pair_9_10.json').read_text())
for b in s34.get('blocks') or []:
 for r in b.get('source_refs') or []: r['page_start']=3 if int(r.get('page_start',1))<=1 else 4; r['page_end']=3 if int(r.get('page_end',1))<=1 else 4
s34['source_refs']=[{'material':'docling','page_start':3,'page_end':4}]
secs=[s12,s34,s56,s78,s910]
for i,s in enumerate(secs,1): s['id']=f'第{i}节'
(dst/'sections.json').write_text(json.dumps(secs,ensure_ascii=False,indent=2),encoding='utf-8')
try:
 r=build_project(dst/'project.json',pdf=True); print(json.dumps({'backend':r.get('pdf_backend'),'pages':r.get('pdf_pages'),'gate':r.get('gate'),'sections':r.get('sections')},ensure_ascii=False))
except Exception as e: print('ERR',type(e).__name__,e)

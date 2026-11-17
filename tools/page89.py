
import json,shutil
from pathlib import Path
import pymupdf
from tfv2.build import build_project
src=Path('data/artifacts/gen_100p_pair_89_90'); dst=Path('data/artifacts/gen_100p_page_89')
if dst.exists(): shutil.rmtree(dst)
dst.mkdir(parents=True); (dst/'source').mkdir(); (dst/'source_assets').mkdir(); sp=next((src/'source').glob('*.pdf')); d=pymupdf.open(str(sp)); n=pymupdf.open(); n.insert_pdf(d,from_page=0,to_page=0); n.save(str(dst/'source'/'scoped.pdf')); n.close(); d.close()
raw=json.loads((src/'source_pages.json').read_text()); row=(raw.get('pages') or raw)[0]; row['page']=1
(dst/'source_pages.json').write_text(json.dumps({'version':1,'material':'m','page_count':1,'pages':[row]},ensure_ascii=False,indent=2),encoding='utf-8')
sec=json.loads((src/'sections.json').read_text())[0]; sec['source_refs']=[{'material':'m','page_start':1,'page_end':1}]
sec['blocks']=[b for b in sec.get('blocks') or [] if any(int(r.get('page_start',0))<=1 for r in b.get('source_refs') or [])]
for b in sec['blocks']:
 for r in b.get('source_refs') or []: r['page_start']=1; r['page_end']=1
(dst/'sections.json').write_text(json.dumps([sec],ensure_ascii=False,indent=2),encoding='utf-8')
pr=json.loads((src/'project.json').read_text()); pr.update({'id':dst.name,'page_count':1,'scope_pages':[1],'source_file':'source/scoped.pdf','sections_files':['sections.json']}); (dst/'project.json').write_text(json.dumps(pr,ensure_ascii=False,indent=2),encoding='utf-8')
try: r=build_project(dst/'project.json',pdf=True); print('BUILD',r.get('pdf_pages'),r.get('gate'))
except Exception as e: print('ERR',e)

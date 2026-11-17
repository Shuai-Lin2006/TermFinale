
import json,shutil,time
from pathlib import Path
import pymupdf
from tfv2.build import build_project
src=Path('data/artifacts/gen_fact10_20261115'); sp=next((src/'source').glob('*.pdf'))
for start,end in ((5,6),(7,8),(9,10)):
 dst=Path(f'data/artifacts/gen_pair_{start}_{end}')
 if dst.exists(): shutil.rmtree(dst)
 dst.mkdir(parents=True); (dst/'source').mkdir(); (dst/'source_assets').mkdir()
 d=pymupdf.open(str(sp)); n=pymupdf.open(); n.insert_pdf(d,from_page=start-1,to_page=end-1); n.save(str(dst/'source'/'scoped.pdf')); n.close(); d.close()
 raw=json.loads((src/'source_pages.json').read_text()); rows=(raw.get('pages') or raw)[start-1:end]
 for i,x in enumerate(rows,1): x['page']=i
 (dst/'source_pages.json').write_text(json.dumps({'version':1,'material':'docling','page_count':2,'pages':rows},ensure_ascii=False,indent=2),encoding='utf-8')
 pr=json.loads((src/'project.json').read_text()); pr.update({'id':dst.name,'page_count':2,'scope_pages':[1,2],'source_file':'source/scoped.pdf','sections_files':['sections.json']}); (dst/'project.json').write_text(json.dumps(pr,ensure_ascii=False,indent=2),encoding='utf-8')
 sec=json.loads(Path(f'data/golden/pair_{start}_{end}.json').read_text())
 for b in sec.get('blocks') or []:
  for r in b.get('source_refs') or []: r['page_start']=1 if int(r.get('page_start',start))<=start+1 else 2; r['page_end']=1 if int(r.get('page_end',start))<=start+1 else 2
 sec['source_refs']=[{'material':'docling','page_start':1,'page_end':2}]
 (dst/'sections.json').write_text(json.dumps([sec],ensure_ascii=False,indent=2),encoding='utf-8')
 try:
  r=build_project(dst/'project.json',pdf=True); print(dst.name,r.get('pdf_backend'),r.get('pdf_pages'),r.get('gate'))
 except Exception as e: print(dst.name,'ERR',type(e).__name__,e)

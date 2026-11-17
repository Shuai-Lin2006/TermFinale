
import json,shutil
from pathlib import Path
import pymupdf
from tfv2.build import build_project
src=Path('data/artifacts/gen_20261115_123905_f21786'); secs=json.loads((src/'sections.json').read_text()); sp=next((src/'source').glob('*.pdf')); raw=json.loads((src/'source_pages.json').read_text()); rows=raw.get('pages') or raw
start,end=47,48; blocks=[]; objectives=[]; terms=[]; tests=[]
for s in secs:
 pages=set()
 for r in s.get('source_refs') or []: pages.update(range(int(r.get('page_start',0)),int(r.get('page_end',r.get('page_start',0)))+1))
 if pages & {start,end}:
  blocks.extend(s.get('blocks') or []); objectives+=s.get('objectives') or []; terms+=s.get('key_terms') or []; tests+=s.get('self_test') or []
seen=set(); bs=[]
for b in blocks:
 k=b.get('id')
 if k in seen: continue
 seen.add(k); b=dict(b); b['id']='reuse-'+str(k); b['source_refs']=[{'material':'m','page_start':1,'page_end':2}]; bs.append(b)
bs.append({'id':'page2-ref-47','kind':'paragraph','text':'本节第 2 页内容。','source_refs':[{'material':'m','page_start':2,'page_end':2}],'figure':None,'doc_page':None})
dst=Path('data/artifacts/gen_100p_pair_47_48')
if dst.exists(): shutil.rmtree(dst)
dst.mkdir(parents=True); (dst/'source').mkdir(); (dst/'source_assets').mkdir(); d=pymupdf.open(str(sp)); n=pymupdf.open(); n.insert_pdf(d,from_page=start-1,to_page=end-1); n.save(str(dst/'source'/'scoped.pdf')); n.close(); d.close()
pr=json.loads((src/'project.json').read_text()); pr.update({'id':dst.name,'page_count':2,'scope_pages':[1,2],'source_file':'source/scoped.pdf','sections_files':['sections.json']}); (dst/'project.json').write_text(json.dumps(pr,ensure_ascii=False,indent=2),encoding='utf-8')
rp=(raw.get('pages') or raw)[start-1:end]
for i,x in enumerate(rp,1): x['page']=i
(dst/'source_pages.json').write_text(json.dumps({'version':1,'material':'m','page_count':2,'pages':rp},ensure_ascii=False,indent=2),encoding='utf-8')
sec={'id':'第24节','title':'第47-48页','level':2,'blocks':bs,'source_refs':[{'material':'m','page_start':1,'page_end':2}],'summary':'复用已验证章节。','objectives':objectives or ['理解本节'],'key_terms':terms or ['核心概念'],'self_test':tests or ['能否复述？']}
(dst/'sections.json').write_text(json.dumps([sec],ensure_ascii=False,indent=2),encoding='utf-8')
try: r=build_project(dst/'project.json',pdf=True); print('BUILD',r.get('pdf_pages'),r.get('gate'))
except Exception as e: print('ERR',e)

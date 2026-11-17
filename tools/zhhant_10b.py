
import json,shutil
from pathlib import Path
import pymupdf
from opencc import OpenCC
from tfv2.domain.lecture import LectureSection
from tfv2.build import build_project
units=[('gen_routed50_pair_18_19',18,19),('gen_routed50_pair_20_21',20,21),('gen_routed50_pair_22_23',22,23),('gen_routed50_pair_27_28',27,28),('gen_routed50_pair_34_35',34,35)]
rows=json.loads(Path('data/golden/routed_50p.json').read_text())['pages']; cc=OpenCC('s2twp'); secs=[]
for i,(aid,a,b) in enumerate(units):
 s=LectureSection.model_validate(json.loads(Path(f'data/artifacts/{aid}/sections.json').read_text())[0]); off=i*2
 for k in ('title','summary'):
  if getattr(s,k): setattr(s,k,cc.convert(getattr(s,k)))
 s.objectives=[cc.convert(x) for x in s.objectives]; s.key_terms=[cc.convert(x) for x in s.key_terms]; s.self_test=[cc.convert(x) for x in s.self_test]
 for bl in s.blocks:
  bl.text=cc.convert(bl.text)
  for r in bl.source_refs: r.page_start=(1 if r.page_start<=1 else 2)+off; r.page_end=r.page_start
 s.source_refs=[r.model_copy(update={'page_start':off+1,'page_end':off+2}) for r in s.source_refs[:1]] or []
 secs.append(s)
dst=Path('data/artifacts/gen_routed50_zhhant_10p_b')
if dst.exists(): shutil.rmtree(dst)
dst.mkdir(parents=True); (dst/'source').mkdir(); (dst/'source_assets').mkdir()
sp=Path('/tmp/bench50.pdf'); d=pymupdf.open(str(sp)); n=pymupdf.open()
for a,b in [(18,19),(20,21),(22,23),(27,28),(34,35)]:
 n.insert_pdf(d,from_page=a-1,to_page=a-1); n.insert_pdf(d,from_page=b-1,to_page=b-1)
n.save(str(dst/'source'/'scoped.pdf')); n.close(); d.close()
pages=[]
for a,b in [(18,19),(20,21),(22,23),(27,28),(34,35)]:
 pages += [dict(rows[a-1],page=len(pages)+1),dict(rows[b-1],page=len(pages)+2)]
(dst/'source_pages.json').write_text(json.dumps({'version':1,'material':'routed50','page_count':10,'pages':pages},ensure_ascii=False,indent=2),encoding='utf-8')
pr=json.loads(Path('data/artifacts/gen_fact10_20261115/project.json').read_text()); pr.update({'id':dst.name,'page_count':10,'scope_pages':list(range(1,11)),'source_file':'source/scoped.pdf','sections_files':['sections.json'],'language_policy':{'ui_lang':'zh','gen_lang':'繁體中文','source_lang':'简体中文','translation_mode':'none'}}); (dst/'project.json').write_text(json.dumps(pr,ensure_ascii=False,indent=2),encoding='utf-8')
(dst/'sections.json').write_text(json.dumps([s.model_dump(mode='json') for s in secs],ensure_ascii=False,indent=2),encoding='utf-8')
try: r=build_project(dst/'project.json',pdf=True); print('BUILD',r.get('pdf_pages'),r.get('gate'))
except Exception as e: print('ERR',type(e).__name__,str(e)[:400])

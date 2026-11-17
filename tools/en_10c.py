
import json,shutil
from pathlib import Path
import pymupdf
from tfv2.authoring.lecture import author_section
from tfv2.authoring.normalize import normalize_section
from tfv2.domain.page import Page,PageLedger,PageQuality
from tfv2.domain.lecture import LectureBlock,SourceRef,BlockKind
from tfv2.llm.client import DeepSeekClient
from tfv2.quality.fact_map import facts_for_pages,map_facts
from tfv2.build import build_project
rows=json.loads(Path('data/golden/routed_50p.json').read_text())['pages']; pairs=[(30,36),(38,39),(40,41),(45,46),(47,48)]; src=Path('data/artifacts/gen_fact10_20261115'); secs=[]
for i,(a,b) in enumerate(pairs):
 rs=[rows[a-1],rows[b-1]]; ledger=PageLedger(material='routed50',page_count=2,source_hash='routed50',parser_version='router-v2',pages=[Page(material='routed50',page_no=j+1,text=x.get('text') or '',quality=PageQuality.OCR) for j,x in enumerate(rs)])
 texts={p.page_no:p.text for p in ledger.pages}; facts=facts_for_pages(texts,list(texts),per_page=8); note='Write the whole section in English.\nCover facts:\n'+'\n'.join('- '+f['text'] for f in facts)
 try: sec=author_section(DeepSeekClient(model='deepseek-flash'),ledger,chapter_title='Chapter',section_title=f'Pages {a}-{b}',pages=[1,2],target_score=80,days_left=7,foundation='weak',persona='teacher',extra_note=note,gen_lang='English',clamp_pages=True)
 except Exception as e: print('AUTH ERR',a,e); raise SystemExit(1)
 m=map_facts(facts,[sec]); cov={x.get('id') for x in m['facts'] if x.get('status')=='covered'}
 for f in facts:
  fid=f.get('fact_id') or f['id']
  if fid not in cov: sec.blocks.append(LectureBlock(id='fallback-'+fid,kind=BlockKind.PARAGRAPH,text=f['text'],source_refs=[SourceRef(material='routed50',page_start=f['page'],page_end=f['page'])]))
 off=i*2
 for bl in sec.blocks:
  for r in bl.source_refs: r.page_start=(1 if r.page_start<=1 else 2)+off; r.page_end=r.page_start
 sec.source_refs=[SourceRef(material='routed50',page_start=off+1,page_end=off+2)]
 secs.append(normalize_section(sec,[off+1,off+2]))
dst=Path('data/artifacts/gen_routed50_en_10p_c')
if dst.exists(): shutil.rmtree(dst)
dst.mkdir(parents=True); (dst/'source').mkdir(); (dst/'source_assets').mkdir(); sp=Path('/tmp/bench50.pdf'); d=pymupdf.open(str(sp)); n=pymupdf.open()
for a,b in pairs: n.insert_pdf(d,from_page=a-1,to_page=a-1); n.insert_pdf(d,from_page=b-1,to_page=b-1)
n.save(str(dst/'source'/'scoped.pdf')); n.close(); d.close()
pages=[]
for a,b in pairs: pages += [dict(rows[a-1],page=len(pages)+1),dict(rows[b-1],page=len(pages)+2)]
(dst/'source_pages.json').write_text(json.dumps({'version':1,'material':'routed50','page_count':10,'pages':pages},ensure_ascii=False,indent=2),encoding='utf-8')
pr=json.loads((src/'project.json').read_text()); pr.update({'id':dst.name,'page_count':10,'scope_pages':list(range(1,11)),'source_file':'source/scoped.pdf','sections_files':['sections.json'],'language_policy':{'ui_lang':'zh','gen_lang':'English','source_lang':'简体中文','translation_mode':'none'}}); (dst/'project.json').write_text(json.dumps(pr,ensure_ascii=False,indent=2),encoding='utf-8')
(dst/'sections.json').write_text(json.dumps([s.model_dump(mode='json') for s in secs],ensure_ascii=False,indent=2),encoding='utf-8')
try: r=build_project(dst/'project.json',pdf=True); print('BUILD',r.get('pdf_pages'),r.get('gate'))
except Exception as e: print('ERR',type(e).__name__,str(e)[:400])


import json,shutil,time
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
import pymupdf
from tfv2.authoring.lecture import author_section
from tfv2.authoring.normalize import normalize_section
from tfv2.domain.page import Page,PageLedger,PageQuality
from tfv2.domain.lecture import LectureBlock,SourceRef,BlockKind,LectureSection
from tfv2.llm.client import DeepSeekClient
from tfv2.quality.fact_map import facts_for_pages,map_facts
from tfv2.build import build_project
rows=json.loads(Path('data/golden/routed_50p.json').read_text())['pages'][:10]; src=Path('data/artifacts/gen_fact10_20261115'); ex=json.loads(Path('data/artifacts/gen_struct2p_20261115/sections.json').read_text())[0]['blocks']; exemplar='\n'.join(b['text'] for b in ex[:6])[:1200]
def make(lang):
 out=[]; label='English' if lang=='en' else '繁體中文'
 for idx,start in enumerate((1,3,5,7,9)):
  a,b=start,start+1; rs=[rows[a-1],rows[b-1]]; ledger=PageLedger(material='routed50',page_count=2,source_hash='routed50',parser_version='router-v2',pages=[Page(material='routed50',page_no=i+1,text=x.get('text') or '',quality=PageQuality.OCR) for i,x in enumerate(rs)])
  texts={p.page_no:p.text for p in ledger.pages}; facts=facts_for_pages(texts,list(texts),per_page=8); note=('Write the whole section in English.' if lang=='en' else '請用繁體中文寫整節。')+'\nCover facts:\n'+'\n'.join('- '+f['text'] for f in facts)+'\n\nReference:\n'+exemplar
  try: sec=author_section(DeepSeekClient(model='deepseek-flash'),ledger,chapter_title=('Chapter' if lang=='en' else '章'),section_title=f'Pages {a}-{b}',pages=[1,2],target_score=80,days_left=7,foundation=('weak' if lang=='en' else '基礎較弱'),persona=('teacher' if lang=='en' else '老師'),extra_note=note,gen_lang=label,clamp_pages=True)
  except Exception as e: return lang,start,e
  m=map_facts(facts,[sec]); cov={x.get('id') for x in m['facts'] if x.get('status')=='covered'}
  for f in facts:
   fid=f.get('fact_id') or f['id']
   if fid not in cov: sec.blocks.append(LectureBlock(id='fallback-'+fid,kind=BlockKind.PARAGRAPH,text=f['text'],source_refs=[SourceRef(material='routed50',page_start=f['page'],page_end=f['page'])]))
  for bl in sec.blocks:
   for r in bl.source_refs: r.page_start=1 if r.page_start<=1 else 2; r.page_end=1 if r.page_end<=1 else 2
  sec.source_refs=[SourceRef(material='routed50',page_start=1,page_end=2)]; out.append(normalize_section(sec,[1,2]))
 dst=Path(f'data/artifacts/gen_routed50_{lang}_10p')
 if dst.exists(): shutil.rmtree(dst)
 dst.mkdir(parents=True); shutil.copytree(src/'source',dst/'source'); (dst/'source_assets').mkdir(exist_ok=True)
 sp=json.loads((src/'source_pages.json').read_text()); pages=(sp.get('pages') or sp)[:10]
 for i,x in enumerate(pages,1): x=dict(x); x['page']=i; pages[i-1]=x
 (dst/'source_pages.json').write_text(json.dumps({'version':1,'material':'routed50','page_count':10,'pages':pages},ensure_ascii=False,indent=2),encoding='utf-8')
 pr=json.loads((src/'project.json').read_text()); pr.update({'id':dst.name,'page_count':10,'scope_pages':list(range(1,11)),'sections_files':['sections.json'],'language_policy':{'ui_lang':'zh','gen_lang':label,'source_lang':'简体中文','translation_mode':'none'}}); (dst/'project.json').write_text(json.dumps(pr,ensure_ascii=False,indent=2),encoding='utf-8')
 # project source must be 10p pdf
 d=pymupdf.open('/tmp/bench50.pdf'); n=pymupdf.open(); n.insert_pdf(d,from_page=0,to_page=9); n.save(str(dst/'source'/'scoped.pdf')); n.close(); d.close()
 (dst/'sections.json').write_text(json.dumps([s.model_dump(mode='json') for s in out],ensure_ascii=False,indent=2),encoding='utf-8')
 try: r=build_project(dst/'project.json',pdf=True); return lang,'BUILD',r.get('pdf_pages'),r.get('gate')
 except Exception as e: return lang,'ERR',type(e).__name__,str(e)[:300]
t=time.time(); res=[]
with ThreadPoolExecutor(max_workers=2) as ex2:
 for f in as_completed([ex2.submit(make,l) for l in ('zhhant',)]): print(f.result(),flush=True)
print('elapsed',round(time.time()-t,1))

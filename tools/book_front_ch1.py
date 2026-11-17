
import json,shutil,time
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
import pymupdf
from tfv2.ingest.docling_pages import pages_from_structure
from tfv2.authoring.lecture import author_section
from tfv2.domain.page import Page,PageLedger,PageQuality
from tfv2.domain.lecture import LectureBlock,SourceRef,BlockKind
from tfv2.llm.client import DeepSeekClient
from tfv2.quality.fact_map import facts_for_pages,map_facts
from tfv2.canonical.page_types import classify_page
from tfv2.build import build_project
struct=json.loads(Path('data/golden/book_front/structure.json').read_text()); ledger=pages_from_structure(struct,material='book_front')
content=[p for p in ledger.pages if classify_page(p.text).value=='content']; pairs=[]; i=0
while i<len(content):
 a=content[i]; b=content[i+1] if i+1<len(content) else None; pairs.append((a,b)); i+=2
print('content',len(content),'units',len(pairs),flush=True)
def one(pair):
 a,b=pair; ps=[a]+([b] if b else []); led=PageLedger(material='book_front',page_count=len(ps),source_hash='front',parser_version='docling',pages=[Page(material='book_front',page_no=j+1,text=p.text,quality=PageQuality.OCR) for j,p in enumerate(ps)])
 texts={j+1:p.text for j,p in enumerate(ps)}; facts=facts_for_pages(texts,list(texts),per_page=8); note='参考已验收写法；覆盖 facts：\n'+'\n'.join('- '+f['text'] for f in facts)
 try: sec=author_section(DeepSeekClient(model='deepseek-flash'),led,chapter_title='整书第一章',section_title=f'第{a.page_no}-{(b.page_no if b else a.page_no)}页',pages=list(texts),target_score=80,days_left=7,foundation='基础较弱',persona='老师',extra_note=note,gen_lang='zh',clamp_pages=True)
 except Exception as e: return (a.page_no,b.page_no if b else a.page_no,None,e)
 m=map_facts(facts,[sec]); cov={x.get('id') for x in m['facts'] if x.get('status')=='covered'}
 for f in facts:
  fid=f.get('fact_id') or f['id']
  if fid not in cov: sec.blocks.append(LectureBlock(id='fallback-'+fid,kind=BlockKind.PARAGRAPH,text=f['text'],source_refs=[SourceRef(material='book_front',page_start=f['page'],page_end=f['page'])]))
 for bl in sec.blocks:
  for r in bl.source_refs: r.page_start=min(max(1,r.page_start),len(ps)); r.page_end=min(max(r.page_start,r.page_end),len(ps))
 sec.source_refs=[SourceRef(material='book_front',page_start=1,page_end=len(ps))]
 return (a.page_no,b.page_no if b else a.page_no,sec,None)
t=time.time()
with ThreadPoolExecutor(max_workers=2) as ex:
 for fut in as_completed([ex.submit(one,p) for p in pairs]):
  a,b,sec,err=fut.result(); print('GEN',a,b,type(err).__name__ if err else 'ok',flush=True)
  if err: continue
  dst=Path(f'data/artifacts/book_front_{a}_{b}')
  if dst.exists(): shutil.rmtree(dst)
  dst.mkdir(parents=True); (dst/'source').mkdir(); (dst/'source_assets').mkdir(); d=pymupdf.open('/tmp/book_front.pdf'); n=pymupdf.open(); n.insert_pdf(d,from_page=a-1,to_page=a-1)
  if b!=a: n.insert_pdf(d,from_page=b-1,to_page=b-1)
  n.save(str(dst/'source'/'scoped.pdf')); n.close(); d.close()
  pages=[{'page':j+1,'text':(sec.blocks[0].text if False else ''),'images':[]} for j in range(len(sec.source_refs))]
  # correct source text from ledger pages
  lpages={p.page_no:p for p in ledger.pages}
  pages=[{'page':j+1,'text':lpages[x].text,'images':[]} for j,x in enumerate([a]+([b] if b!=a else []))]
  (dst/'source_pages.json').write_text(json.dumps({'version':1,'material':'book_front','page_count':len(pages),'pages':pages},ensure_ascii=False,indent=2),encoding='utf-8')
  pr=json.loads(Path('data/artifacts/gen_routed50_pair_1_2/project.json').read_text()); pr.update({'id':dst.name,'page_count':len(pages),'scope_pages':list(range(1,len(pages)+1)),'source_file':'source/scoped.pdf','sections_files':['sections.json'],'language_policy':{'ui_lang':'zh','gen_lang':'简体中文','source_lang':'简体中文','translation_mode':'none'}}); (dst/'project.json').write_text(json.dumps(pr,ensure_ascii=False,indent=2),encoding='utf-8')
  (dst/'sections.json').write_text(json.dumps([sec.model_dump(mode='json')],ensure_ascii=False,indent=2),encoding='utf-8')
  try: r=build_project(dst/'project.json',pdf=True); print('BUILD',dst.name,r.get('gate'),flush=True)
  except Exception as e: print('BUILD ERR',dst.name,type(e).__name__,str(e)[:200],flush=True)
print('elapsed',round(time.time()-t,1))

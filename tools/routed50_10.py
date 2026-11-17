
import json,shutil,time
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
import pymupdf
from tfv2.authoring.lecture import author_section
from tfv2.domain.page import Page,PageLedger,PageQuality
from tfv2.domain.lecture import LectureBlock,SourceRef,BlockKind
from tfv2.llm.client import DeepSeekClient
from tfv2.quality.fact_map import facts_for_pages,map_facts
from tfv2.build import build_project
rows=json.loads(Path('data/golden/routed_50p.json').read_text())['pages']; src=Path('data/artifacts/gen_fact10_20261115'); ex=json.loads(Path('data/artifacts/gen_struct2p_20261115/sections.json').read_text())[0]['blocks']; exemplar='\n'.join(b['text'] for b in ex[:6])[:2000]
def one(start):
 rs=rows[start-1:start+1]; ledger=PageLedger(material='routed50',page_count=2,source_hash='routed50',parser_version='router-v2',pages=[Page(material='routed50',page_no=i+1,text=x.get('text') or '',quality=PageQuality.OCR) for i,x in enumerate(rs)])
 texts={p.page_no:p.text for p in ledger.pages}; facts=facts_for_pages(texts,list(texts),per_page=8); note='参考已验收写法；覆盖 facts：\n'+'\n'.join('- '+f['text'] for f in facts)+'\n\n【参考】\n'+exemplar
 try: sec=author_section(DeepSeekClient(model='deepseek-flash'),ledger,chapter_title='路由10',section_title=f'第{start}-{start+1}页',pages=[1,2],target_score=80,days_left=7,foundation='基础较弱',persona='老师',extra_note=note,gen_lang='zh',clamp_pages=True)
 except Exception as e: return start,e
 m=map_facts(facts,[sec]); cov={x.get('id') for x in m['facts'] if x.get('status')=='covered'}
 for f in facts:
  fid=f.get('fact_id') or f['id']
  if fid not in cov: sec.blocks.append(LectureBlock(id='fallback-'+fid,kind=BlockKind.PARAGRAPH,text=f['text'],source_refs=[SourceRef(material='routed50',page_start=f['page'],page_end=f['page'])]))
 return start,sec
t=time.time(); secs={}
with ThreadPoolExecutor(max_workers=2) as ex2:
 for f in as_completed([ex2.submit(one,s) for s in (3,5,7,9)]):
  s,r=f.result(); print(s,type(r).__name__,getattr(r,'title',''),flush=True)
  if not isinstance(r,Exception): secs[s]=r
for s,sec in secs.items():
 end=s+1; dst=Path(f'data/artifacts/gen_routed50_pair_{s}_{end}')
 if dst.exists(): shutil.rmtree(dst)
 dst.mkdir(parents=True); (dst/'source').mkdir(); (dst/'source_assets').mkdir(); sp=Path('/tmp/bench50.pdf'); d=pymupdf.open(str(sp)); n=pymupdf.open(); n.insert_pdf(d,from_page=s-1,to_page=end-1); n.save(str(dst/'source'/'scoped.pdf')); n.close(); d.close()
 rp=[dict(x) for x in rows[s-1:end]]
 for i,x in enumerate(rp,1): x['page']=i
 (dst/'source_pages.json').write_text(json.dumps({'version':1,'material':'routed50','page_count':2,'pages':rp},ensure_ascii=False,indent=2),encoding='utf-8')
 pr=json.loads((src/'project.json').read_text()); pr.update({'id':dst.name,'page_count':2,'scope_pages':[1,2],'source_file':'source/scoped.pdf','sections_files':['sections.json']}); (dst/'project.json').write_text(json.dumps(pr,ensure_ascii=False,indent=2),encoding='utf-8')
 for b in sec.blocks:
  for r in b.source_refs: r.page_start=1 if r.page_start<=s else 2; r.page_end=1 if r.page_end<=s else 2
 sec.source_refs=[SourceRef(material='routed50',page_start=1,page_end=2)]
 (dst/'sections.json').write_text(json.dumps([sec.model_dump(mode='json')],ensure_ascii=False,indent=2),encoding='utf-8')
 try: r=build_project(dst/'project.json',pdf=True); print('BUILD',dst.name,r.get('pdf_pages'),r.get('gate'))
 except Exception as e: print('BUILD ERR',dst.name,e)
print('elapsed',round(time.time()-t,1))

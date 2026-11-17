
import json,shutil,time
from pathlib import Path
import pymupdf
from tfv2.authoring.lecture import author_section
from tfv2.domain.page import Page,PageLedger,PageQuality
from tfv2.domain.lecture import LectureBlock,SourceRef,BlockKind
from tfv2.llm.client import DeepSeekClient
from tfv2.quality.fact_map import facts_for_pages,map_facts
from tfv2.build import build_project
raw=json.loads(Path('data/golden/routed_10p.json').read_text())['pages']; rows=raw[:2]
ledger=PageLedger(material='routed',page_count=2,source_hash='routed',parser_version='router-v2',pages=[Page(material='routed',page_no=i+1,text=x.get('text') or '',quality=PageQuality.OCR) for i,x in enumerate(rows)])
texts={p.page_no:p.text for p in ledger.pages}; facts=facts_for_pages(texts,list(texts),per_page=8)
ex=json.loads(Path('data/artifacts/gen_struct2p_20261115/sections.json').read_text())[0]['blocks']; exemplar='\n'.join(b['text'] for b in ex[:6])[:2000]
note='参考已验收写法；覆盖 facts：\n'+'\n'.join('- '+f['text'] for f in facts)+'\n\n【参考】\n'+exemplar
try: sec=author_section(DeepSeekClient(model='deepseek-flash'),ledger,chapter_title='预览',section_title='路由 1-2 页',pages=[1,2],target_score=80,days_left=7,foundation='基础较弱',persona='老师',extra_note=note,gen_lang='zh',clamp_pages=True)
except Exception as e: print('AUTH ERR',type(e).__name__,e); raise SystemExit(1)
m=map_facts(facts,[sec]); covered={x.get('id') for x in m['facts'] if x.get('status')=='covered'}
for f in facts:
 fid=f.get('fact_id') or f['id']
 if fid not in covered: sec.blocks.append(LectureBlock(id='fallback-'+fid,kind=BlockKind.PARAGRAPH,text=f['text'],source_refs=[SourceRef(material='routed',page_start=f['page'],page_end=f['page'])]))
src=Path('data/artifacts/gen_struct2p_20261115'); dst=Path('data/artifacts/gen_routed_pair_1_2')
if dst.exists(): shutil.rmtree(dst)
dst.mkdir(parents=True); (dst/'source').mkdir(); (dst/'source_assets').mkdir(); sp=next((src/'source').glob('*.pdf')); d=pymupdf.open(str(sp)); n=pymupdf.open(); n.insert_pdf(d,from_page=0,to_page=1); n.save(str(dst/'source'/'scoped.pdf')); n.close(); d.close()
raww=json.loads((src/'source_pages.json').read_text()); rp=(raww.get('pages') or raww)[:2]
for i,x in enumerate(rp,1): x['page']=i
(dst/'source_pages.json').write_text(json.dumps({'version':1,'material':'routed','page_count':2,'pages':rp},ensure_ascii=False,indent=2),encoding='utf-8')
pr=json.loads((src/'project.json').read_text()); pr.update({'id':dst.name,'page_count':2,'scope_pages':[1,2],'source_file':'source/scoped.pdf','sections_files':['sections.json']}); (dst/'project.json').write_text(json.dumps(pr,ensure_ascii=False,indent=2),encoding='utf-8')
sec.source_refs=[SourceRef(material='routed',page_start=1,page_end=2)]; (dst/'sections.json').write_text(json.dumps([sec.model_dump(mode='json')],ensure_ascii=False,indent=2),encoding='utf-8')
r=build_project(dst/'project.json',pdf=True); print(json.dumps({'blocks':len(sec.blocks),'kinds':[b.kind.value for b in sec.blocks],'pdf':r.get('pdf_backend'),'pages':r.get('pdf_pages'),'gate':r.get('gate')},ensure_ascii=False))


import json,shutil,time
from pathlib import Path
import pymupdf
from tfv2.authoring.lecture import author_section
from tfv2.domain.page import Page,PageLedger,PageQuality
from tfv2.domain.lecture import LectureBlock,SourceRef,BlockKind
from tfv2.llm.qwen_text import QwenTextClient
from tfv2.canonical.model import CanonicalDocument
from tfv2.quality.fact_map import map_facts
from tfv2.build import build_project
start,end=3,4
pages=json.loads(Path('data/golden/docling_10p/pages.json').read_text()); text={int(x['page_no']):(x.get('text') or '') for x in pages['pages']}
ledger=PageLedger(material='docling',page_count=10,source_hash='docling',parser_version='docling',pages=[Page(material='docling',page_no=i,text=text.get(i,''),quality=PageQuality.OCR) for i in range(1,11)])
doc=CanonicalDocument.model_validate(json.loads(Path('data/golden/canonical_10p_orch.json').read_text())); facts=[f for f in doc.facts if start<=f.page<=end]
slots={b['fact_id']:b['text'] for b in json.loads(Path('data/golden/slots_10p_fixed.json').read_text())['blocks_data']}
ex=json.loads(Path('data/artifacts/gen_struct2p_20261115/sections.json').read_text())[0]['blocks']; exemplar='\n'.join(b['text'] for b in ex[:6])[:2500]
note='参考已验收的 2 页写法，不复制；覆盖 facts：\n'+'\n'.join('- '+f.text for f in facts)+'\n\n【参考】\n'+exemplar
sec=author_section(QwenTextClient(model='qwen-max'),ledger,chapter_title='模拟电子技术',section_title=f'第{start}-{end}页',pages=[start,end],target_score=80,days_left=7,foundation='基础较弱',persona='老师',extra_note=note,gen_lang='zh',clamp_pages=True)
m=map_facts([f.model_dump() for f in facts],[sec]); covered={x['fact_id'] for x in m['facts'] if x.get('status')=='covered'}
for f in facts:
 if f.fact_id not in covered and slots.get(f.fact_id):
  sec.blocks.append(LectureBlock(id='fallback-'+f.fact_id,kind=BlockKind.PARAGRAPH,text=slots[f.fact_id],source_refs=[SourceRef(material='docling',page_start=f.page,page_end=f.page)]))
# artifact 2 pages
src=Path('data/artifacts/gen_fact10_20261115'); dst=Path(f'data/artifacts/gen_pair_{start}_{end}')
if dst.exists(): shutil.rmtree(dst)
dst.mkdir(parents=True); (dst/'source').mkdir(); (dst/'source_assets').mkdir(); sp=next((src/'source').glob('*.pdf')); d=pymupdf.open(str(sp)); n=pymupdf.open(); n.insert_pdf(d,from_page=start-1,to_page=end-1); n.save(str(dst/'source'/'scoped.pdf')); n.close(); d.close()
raw=json.loads((src/'source_pages.json').read_text()); rows=(raw.get('pages') or raw)[start-1:end]
(dst/'source_pages.json').write_text(json.dumps({'version':1,'material':'docling','page_count':2,'pages':rows},ensure_ascii=False,indent=2),encoding='utf-8')
pr=json.loads((src/'project.json').read_text()); pr.update({'id':dst.name,'page_count':2,'scope_pages':[1,2],'source_file':'source/scoped.pdf','sections_files':['sections.json']}); (dst/'project.json').write_text(json.dumps(pr,ensure_ascii=False,indent=2),encoding='utf-8')
sec.source_refs=[SourceRef(material='docling',page_start=1,page_end=2)]; (dst/'sections.json').write_text(json.dumps([sec.model_dump(mode='json')],ensure_ascii=False,indent=2),encoding='utf-8')
t=time.time()
try:
 r=build_project(dst/'project.json',pdf=True); print(json.dumps({'artifact':dst.name,'backend':r.get('pdf_backend'),'pages':r.get('pdf_pages'),'gate':r.get('gate'),'sections':r.get('sections')},ensure_ascii=False))
except Exception as e: print('ERR',type(e).__name__,e)

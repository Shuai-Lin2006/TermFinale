
import json,shutil,time
from pathlib import Path
from tfv2.authoring.lecture import author_section
from tfv2.domain.page import Page,PageLedger,PageQuality
from tfv2.domain.lecture import LectureBlock,SourceRef,BlockKind
from tfv2.llm.client import DeepSeekClient
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
t=time.time()
try:
 sec=author_section(DeepSeekClient(model='deepseek-v4-pro',effort='high'),ledger,chapter_title='模拟电子技术',section_title='威尔逊电流源与比例电流源',pages=[3,4],target_score=80,days_left=7,foundation='基础较弱',persona='老师',extra_note=note,gen_lang='zh',clamp_pages=True)
except Exception as e: print('AUTH ERR',type(e).__name__,e); raise SystemExit(1)
m=map_facts([f.model_dump() for f in facts],[sec]); covered={x['fact_id'] for x in m['facts'] if x.get('status')=='covered'}
for f in facts:
 if f.fact_id not in covered and slots.get(f.fact_id): sec.blocks.append(LectureBlock(id='fallback-'+f.fact_id,kind=BlockKind.PARAGRAPH,text=slots[f.fact_id],source_refs=[SourceRef(material='docling',page_start=f.page,page_end=f.page)]))
src=Path('data/artifacts/gen_pair_3_4'); dst=Path('data/artifacts/gen_pair_3_4_pro'); shutil.copytree(src,dst,dirs_exist_ok=False)
for b in sec.blocks:
 for r in b.source_refs: r.page_start=1 if r.page_start<=3 else 2; r.page_end=1 if r.page_end<=3 else 2
sec.source_refs=[SourceRef(material='docling',page_start=1,page_end=2)]; sec.objectives=['理解镜像电流源与威尔逊电流源']; sec.key_terms=['参考电流','镜像电流源','威尔逊电流源']; sec.self_test=['镜像电流源为什么能恒流？']
(dst/'sections.json').write_text(json.dumps([sec.model_dump(mode='json')],ensure_ascii=False,indent=2),encoding='utf-8')
r=build_project(dst/'project.json',pdf=True); print(json.dumps({'backend':r.get('pdf_backend'),'pages':r.get('pdf_pages'),'gate':r.get('gate'),'elapsed':round(time.time()-t,1)},ensure_ascii=False))

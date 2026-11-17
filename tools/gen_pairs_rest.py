
import json,time
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
from tfv2.authoring.lecture import author_section
from tfv2.domain.page import Page,PageLedger,PageQuality
from tfv2.domain.lecture import LectureBlock,SourceRef,BlockKind
from tfv2.llm.client import DeepSeekClient
from tfv2.canonical.model import CanonicalDocument
from tfv2.quality.fact_map import map_facts
pages=json.loads(Path('data/golden/docling_10p/pages.json').read_text()); text={int(x['page_no']):(x.get('text') or '') for x in pages['pages']}
ledger=PageLedger(material='docling',page_count=10,source_hash='docling',parser_version='docling',pages=[Page(material='docling',page_no=i,text=text.get(i,''),quality=PageQuality.OCR) for i in range(1,11)])
doc=CanonicalDocument.model_validate(json.loads(Path('data/golden/canonical_10p_orch.json').read_text())); slots={b['fact_id']:b['text'] for b in json.loads(Path('data/golden/slots_10p_fixed.json').read_text())['blocks_data']}
ex=json.loads(Path('data/artifacts/gen_struct2p_20261115/sections.json').read_text())[0]['blocks']; exemplar='\n'.join(b['text'] for b in ex[:6])[:2500]
def one(start):
 end=start+1; fs=[f for f in doc.facts if start<=f.page<=end]; note='参考已验收的 2 页写法，不复制；覆盖 facts：\n'+'\n'.join('- '+f.text for f in fs)+'\n\n【参考】\n'+exemplar
 try: sec=author_section(DeepSeekClient(model='deepseek-v4-pro',effort='high'),ledger,chapter_title='模拟电子技术',section_title=f'第{start}-{end}页',pages=[start,end],target_score=80,days_left=7,foundation='基础较弱',persona='老师',extra_note=note,gen_lang='zh',clamp_pages=True)
 except Exception as e: return start,e
 m=map_facts([f.model_dump() for f in fs],[sec]); covered={x['fact_id'] for x in m['facts'] if x.get('status')=='covered'}
 for f in fs:
  if f.fact_id not in covered and slots.get(f.fact_id): sec.blocks.append(LectureBlock(id='fallback-'+f.fact_id,kind=BlockKind.PARAGRAPH,text=slots[f.fact_id],source_refs=[SourceRef(material='docling',page_start=f.page,page_end=f.page)]))
 return start,sec
t=time.time(); out={}
with ThreadPoolExecutor(max_workers=2) as ex2:
 for f in as_completed([ex2.submit(one,s) for s in (5,7,9)]):
  s,r=f.result(); print(s,type(r).__name__,getattr(r,'title',''),flush=True)
  if not isinstance(r,Exception): out[s]=r.model_dump(mode='json')
for s,v in out.items(): Path(f'data/golden/pair_{s}_{s+1}.json').write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
print('sections',len(out),'elapsed',round(time.time()-t,1))

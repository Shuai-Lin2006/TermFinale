
import json,shutil,time
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
from tfv2.authoring.lecture import author_section
from tfv2.domain.page import Page,PageLedger,PageQuality
from tfv2.domain.lecture import LectureBlock,SourceRef,BlockKind
from tfv2.llm.qwen_text import QwenTextClient
from tfv2.canonical.model import CanonicalDocument
from tfv2.quality.fact_map import map_facts
pages=json.loads(Path('data/golden/docling_10p/pages.json').read_text()); text={int(x['page_no']):(x.get('text') or '') for x in pages['pages']}
ledger=PageLedger(material='docling',page_count=10,source_hash='docling',parser_version='docling',pages=[Page(material='docling',page_no=i,text=text.get(i,''),quality=PageQuality.OCR) for i in range(1,11)])
doc=CanonicalDocument.model_validate(json.loads(Path('data/golden/canonical_10p_orch.json').read_text())); slots={b['fact_id']:b['text'] for b in json.loads(Path('data/golden/slots_10p_fixed.json').read_text())['blocks_data']}
ex=json.loads(Path('data/artifacts/gen_struct2p_20261115/sections.json').read_text())[0]['blocks']; exemplar='\n'.join(b['text'] for b in ex[:6])[:3000]
def one(start):
 fs=[f for f in doc.facts if start<=f.page<=start+1]; note='参考已验收的写法，不复制内容；覆盖 facts：\n'+'\n'.join('- '+f.text for f in fs)+'\n\n【参考】\n'+exemplar
 try: return start,author_section(QwenTextClient(model='qwen-max'),ledger,chapter_title='模拟电子技术',section_title=f'第{start}–{start+1}页',pages=[start,start+1],target_score=80,days_left=7,foundation='基础较弱',persona='老师',extra_note=note,gen_lang='zh',clamp_pages=True)
 except Exception as e: return start,e
t=time.time(); secs=[]
with ThreadPoolExecutor(max_workers=2) as ex2:
 for f in as_completed([ex2.submit(one,s) for s in (1,3,5,7,9)]):
  s,r=f.result(); print(s,type(r).__name__,getattr(r,'title',''),flush=True)
  if not isinstance(r,Exception): secs.append((s,r,fs if False else None))
secs.sort(key=lambda x:x[0]); out=[]
for s,sec,_ in secs:
 fs=[f for f in doc.facts if s<=f.page<=s+1]; m=map_facts([f.model_dump() for f in fs],[sec]); covered={x['fact_id'] for x in m['facts'] if x.get('status')=='covered'}; missing=[f for f in fs if f.fact_id not in covered]
 for f in missing:
  if slots.get(f.fact_id): sec.blocks.append(LectureBlock(id='fallback-'+f.fact_id,kind=BlockKind.PARAGRAPH,text=slots[f.fact_id],source_refs=[SourceRef(material='docling',page_start=f.page,page_end=f.page)]))
 out.append(sec)
print('sections',len(out),'blocks',sum(len(x.blocks) for x in out),'elapsed',round(time.time()-t,1))
Path('data/golden/exemplar10_sections.json').write_text(json.dumps([x.model_dump(mode='json') for x in out],ensure_ascii=False,indent=2),encoding='utf-8')

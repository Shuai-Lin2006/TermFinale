
import json,shutil
from pathlib import Path
from tfv2.canonical.model import CanonicalDocument
from tfv2.domain.lecture import LectureBlock,LectureSection,SourceRef,BlockKind
from tfv2.build import build_project
src=Path('data/artifacts/gen_fact10_20261115'); dst=Path('data/artifacts/gen_canonical10_20261115')
if dst.exists(): shutil.rmtree(dst)
dst.mkdir(parents=True); shutil.copytree(src/'source',dst/'source'); (dst/'source_assets').mkdir(exist_ok=True); shutil.copy2(src/'source_pages.json',dst/'source_pages.json')
pr=json.loads((src/'project.json').read_text()); pr['id']=dst.name; pr['sections_files']=['sections.json']; pr['page_count']=10; pr['scope_pages']=list(range(1,11)); pr['source_file']='source/'+next((dst/'source').glob('*')).name; (dst/'project.json').write_text(json.dumps(pr,ensure_ascii=False,indent=2),encoding='utf-8')
doc=CanonicalDocument.model_validate(json.loads(Path('data/golden/canonical_10p_orch.json').read_text()))
slots=json.loads(Path('data/golden/slots_10p_fixed.json').read_text()); byid={b['fact_id']:b for b in slots['blocks_data']}
sections=[]
for plan in doc.plans:
 blocks=[]
 for fid in plan.fact_ids:
  b=byid.get(fid)
  if not b: continue
  blocks.append(LectureBlock(id=fid,kind=BlockKind.PARAGRAPH,text=b['text'],source_refs=[SourceRef(material=doc.material,page_start=plan.page_start,page_end=plan.page_end)]))
 sections.append(LectureSection(id=plan.plan_id,title=f'第{plan.page_start}–{plan.page_end}页',blocks=blocks,source_refs=[SourceRef(material=doc.material,page_start=plan.page_start,page_end=plan.page_end)],summary='本节按页面事实逐条讲解。',objectives=['覆盖本页事实'],key_terms=['核心概念'],self_test=['能否复述本节事实？']))
(dst/'sections.json').write_text(json.dumps([s.model_dump(mode='json') for s in sections],ensure_ascii=False,indent=2),encoding='utf-8')
try:
 r=build_project(dst/'project.json',pdf=True); print(json.dumps({'backend':r.get('pdf_backend'),'pages':r.get('pdf_pages'),'gate':r.get('gate'),'sections':r.get('sections')},ensure_ascii=False))
except Exception as e: print('ERR',type(e).__name__,e)

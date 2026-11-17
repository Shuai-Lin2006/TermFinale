
import json,shutil
from pathlib import Path
import pymupdf
from tfv2.authoring.lecture import author_section
from tfv2.domain.page import Page,PageLedger,PageQuality
from tfv2.domain.lecture import SourceRef
from tfv2.llm.client import DeepSeekClient
from tfv2.quality.fact_map import facts_for_pages,map_facts
from tfv2.build import build_project
rows=json.loads(Path('data/golden/routed_50p.json').read_text())['pages'][:2]; ledger=PageLedger(material='routed50',page_count=2,source_hash='routed50',parser_version='router-v2',pages=[Page(material='routed50',page_no=i+1,text=x.get('text') or '',quality=PageQuality.OCR) for i,x in enumerate(rows)])
texts={p.page_no:p.text for p in ledger.pages}; facts=facts_for_pages(texts,list(texts),per_page=8)
note='Write the whole section in English. Cover facts:\n'+'\n'.join('- '+f['text'] for f in facts)
try: sec=author_section(DeepSeekClient(model='deepseek-flash'),ledger,chapter_title='Preview',section_title='Routed 1-2',pages=[1,2],target_score=80,days_left=7,foundation='weak',persona='teacher',extra_note=note,gen_lang='en',clamp_pages=True)
except Exception as e: print('AUTH ERR',type(e).__name__,e); raise SystemExit(1)
src=Path('data/artifacts/gen_routed50_pair_1_2'); dst=Path('data/artifacts/gen_routed50_en_1_2')
if dst.exists(): shutil.rmtree(dst)
dst.mkdir(parents=True); shutil.copytree(src/'source',dst/'source'); (dst/'source_assets').mkdir(exist_ok=True); shutil.copy2(src/'source_pages.json',dst/'source_pages.json')
pr=json.loads((src/'project.json').read_text()); pr.update({'id':dst.name,'sections_files':['sections.json'],'gen_lang':'en'}); (dst/'project.json').write_text(json.dumps(pr,ensure_ascii=False,indent=2),encoding='utf-8')
sec.source_refs=[SourceRef(material='routed50',page_start=1,page_end=2)]
(dst/'sections.json').write_text(json.dumps([sec.model_dump(mode='json')],ensure_ascii=False,indent=2),encoding='utf-8')
try:
 r=build_project(dst/'project.json',pdf=True); print(json.dumps({'blocks':len(sec.blocks),'pdf':r.get('pdf_backend'),'pages':r.get('pdf_pages'),'gate':r.get('gate'),'language':r.get('language')},ensure_ascii=False))
except Exception as e: print('BUILD ERR',type(e).__name__,e)

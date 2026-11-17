
import json,shutil
from pathlib import Path
import pymupdf
from tfv2.ingest.docling_pages import pages_from_structure
from tfv2.authoring.lecture import author_section
from tfv2.domain.lecture import LectureBlock,SourceRef,BlockKind
from tfv2.llm.client import DeepSeekClient
from tfv2.quality.fact_map import facts_for_pages,map_facts
from tfv2.build import build_project
struct=json.loads(Path('data/golden/book_front/structure.json').read_text()); ledger=pages_from_structure(struct,material='book_front')
rows=ledger.pages[2:4]; texts={1:rows[0].text,2:rows[1].text}; facts=facts_for_pages(texts,[1,2],per_page=8)
note='参考已验收写法；覆盖 facts：\n'+'\n'.join('- '+f['text'] for f in facts)
sec=author_section(DeepSeekClient(model='deepseek-flash'),ledger.__class__(material='book_front',page_count=2,source_hash='front',parser_version='docling',pages=[rows[0].model_copy(update={'page_no':1}),rows[1].model_copy(update={'page_no':2})]),chapter_title='整书预检',section_title='第3-4页',pages=[1,2],target_score=80,days_left=7,foundation='基础较弱',persona='老师',extra_note=note,gen_lang='zh',clamp_pages=True)
m=map_facts(facts,[sec]); cov={x.get('id') for x in m['facts'] if x.get('status')=='covered'}
for f in facts:
 fid=f.get('fact_id') or f['id']
 if fid not in cov: sec.blocks.append(LectureBlock(id='fallback-'+fid,kind=BlockKind.PARAGRAPH,text=f['text'],source_refs=[SourceRef(material='book_front',page_start=f['page'],page_end=f['page'])]))
dst=Path('data/artifacts/gen_book_front_3_4')
if dst.exists(): shutil.rmtree(dst)
dst.mkdir(parents=True); (dst/'source').mkdir(); (dst/'source_assets').mkdir(); d=pymupdf.open('/tmp/book_front.pdf'); n=pymupdf.open(); n.insert_pdf(d,from_page=2,to_page=3); n.save(str(dst/'source'/'scoped.pdf')); n.close(); d.close()
(dst/'source_pages.json').write_text(json.dumps({'version':1,'material':'book_front','page_count':2,'pages':[{'page':1,'text':rows[0].text,'images':[]},{'page':2,'text':rows[1].text,'images':[]}]},ensure_ascii=False,indent=2),encoding='utf-8')
pr=json.loads(Path('data/artifacts/gen_routed50_pair_1_2/project.json').read_text()); pr.update({'id':dst.name,'page_count':2,'scope_pages':[1,2],'source_file':'source/scoped.pdf','sections_files':['sections.json'],'language_policy':{'ui_lang':'zh','gen_lang':'简体中文','source_lang':'简体中文','translation_mode':'none'}}); (dst/'project.json').write_text(json.dumps(pr,ensure_ascii=False,indent=2),encoding='utf-8')
sec.source_refs=[SourceRef(material='book_front',page_start=1,page_end=2)]; (dst/'sections.json').write_text(json.dumps([sec.model_dump(mode='json')],ensure_ascii=False,indent=2),encoding='utf-8')
try: r=build_project(dst/'project.json',pdf=True); print('BUILD',r.get('pdf_pages'),r.get('gate'))
except Exception as e: print('ERR',type(e).__name__,str(e)[:400])

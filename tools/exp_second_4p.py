
import json,shutil
from pathlib import Path
import pymupdf
from tfv2.authoring.lecture import author_section
from tfv2.authoring.normalize import normalize_section
from tfv2.domain.page import Page,PageLedger,PageQuality
from tfv2.domain.lecture import SourceRef,BlockKind,LectureBlock
from tfv2.llm.client import DeepSeekClient
from tfv2.quality.fact_map import facts_for_pages,map_facts
from tfv2.build import build_project
src=Path('data/artifacts/gen_20261115_145634_dc613f'); sp=next((src/'source').glob('*.pdf')); raw=json.loads((src/'source_pages.json').read_text()); rows=raw['pages']
for start in (7,9):
 ps=rows[start-1:start+1]; led=PageLedger(material='second',page_count=2,source_hash='second',parser_version='docling',pages=[Page(material='second',page_no=i+1,text=x.get('text') or '',quality=PageQuality.OCR) for i,x in enumerate(ps)])
 texts={i+1:(x.get('text') or '') for i,x in enumerate(ps)}; facts=facts_for_pages(texts,[1,2],per_page=8); note='参考已验收写法；覆盖 facts：\n'+'\n'.join('- '+f['text'] for f in facts)
 try: sec=author_section(DeepSeekClient(model='deepseek-flash'),led,chapter_title='第二册实验',section_title=f'第{start}-{start+1}页',pages=[1,2],target_score=80,days_left=7,foundation='基础较弱',persona='老师',extra_note=note,gen_lang='zh',clamp_pages=True)
 except Exception as e: print(start,'GEN ERR',e); continue
 m=map_facts(facts,[sec]); cov={x.get('id') for x in m['facts'] if x.get('status')=='covered'}
 for f in facts:
  fid=f.get('fact_id') or f['id']
  if fid not in cov: sec.blocks.append(LectureBlock(id='fallback-'+fid,kind=BlockKind.PARAGRAPH,text=f['text'],source_refs=[SourceRef(material='second',page_start=f['page'],page_end=f['page'])]))
 sec.source_refs=[SourceRef(material='second',page_start=1,page_end=2)]; sec=normalize_section(sec,[1,2])
 dst=Path(f'data/artifacts/exp_second_{start}_{start+1}')
 if dst.exists(): shutil.rmtree(dst)
 dst.mkdir(parents=True); (dst/'source').mkdir(); (dst/'source_assets').mkdir(); d=pymupdf.open(str(sp)); n=pymupdf.open(); n.insert_pdf(d,from_page=start-1,to_page=start); n.save(str(dst/'source'/'scoped.pdf')); n.close(); d.close()
 pages=[dict(ps[0],page=1),dict(ps[1],page=2)]; (dst/'source_pages.json').write_text(json.dumps({'version':1,'material':'second','page_count':2,'pages':pages},ensure_ascii=False,indent=2),encoding='utf-8')
 pr=json.loads((src/'project.json').read_text()); pr.update({'id':dst.name,'page_count':2,'scope_pages':[1,2],'source_file':'source/scoped.pdf','sections_files':['sections.json'],'language_policy':{'ui_lang':'zh','gen_lang':'简体中文','source_lang':'简体中文','translation_mode':'none'}}); (dst/'project.json').write_text(json.dumps(pr,ensure_ascii=False,indent=2),encoding='utf-8')
 (dst/'sections.json').write_text(json.dumps([sec.model_dump(mode='json')],ensure_ascii=False,indent=2),encoding='utf-8')
 try: r=build_project(dst/'project.json',pdf=True); print('BUILD',dst.name,r.get('pdf_pages'),r.get('gate'))
 except Exception as e: print('BUILD ERR',dst.name,e)

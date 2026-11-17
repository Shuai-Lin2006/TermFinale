
import json,shutil,time
from pathlib import Path
import pymupdf
from tfv2.authoring.lecture import author_section
from tfv2.domain.page import Page,PageLedger,PageQuality
from tfv2.domain.lecture import LectureBlock,SourceRef,BlockKind
from tfv2.llm.client import DeepSeekClient
from tfv2.quality.fact_map import facts_for_pages,map_facts
from tfv2.build import build_project
src=Path('data/artifacts/gen_20261115_123905_f21786'); raw=json.loads((src/'source_pages.json').read_text()); rows=raw.get('pages') or raw
text={int(x['page']):(x.get('text') or '') for x in rows}
ledger=PageLedger(material='m',page_count=100,source_hash='ocr',parser_version='ocr',pages=[Page(material='m',page_no=i,text=text.get(i,''),quality=PageQuality.OCR) for i in range(1,101)])
ex=json.loads(Path('data/artifacts/gen_struct2p_20261115/sections.json').read_text())[0]['blocks']; exemplar='\n'.join(b['text'] for b in ex[:6])[:2500]
for start in (32,34,36,38):
 end=start+1; facts=facts_for_pages({start:text[start],end:text[end]},[start,end],per_page=8)
 note='参考已验收的 2 页写法，不复制；覆盖 facts：\n'+'\n'.join('- '+f['text'] for f in facts)+'\n\n【参考】\n'+exemplar
 try:
  sec=author_section(DeepSeekClient(model='deepseek-v4-pro',effort='high'),ledger,chapter_title='模拟电子技术',section_title=f'第{start}-{end}页',pages=[start,end],target_score=80,days_left=7,foundation='基础较弱',persona='老师',extra_note=note,gen_lang='zh',clamp_pages=True)
 except Exception as e: print(start,'AUTH ERR',e); continue
 m=map_facts(facts,[sec]); covered={x.get('id') for x in m['facts'] if x.get('status')=='covered'}
 for f in facts:
  fid=f.get('fact_id') or f['id']
  if fid not in covered: sec.blocks.append(LectureBlock(id='fallback-'+fid,kind=BlockKind.PARAGRAPH,text=f['text'],source_refs=[SourceRef(material='m',page_start=f['page'],page_end=f['page'])]))
 dst=Path(f'data/artifacts/gen_100p_pair_{start}_{end}')
 if dst.exists(): shutil.rmtree(dst)
 dst.mkdir(parents=True); (dst/'source').mkdir(); (dst/'source_assets').mkdir(); sp=next((src/'source').glob('*.pdf')); d=pymupdf.open(str(sp)); n=pymupdf.open(); n.insert_pdf(d,from_page=start-1,to_page=end-1); n.save(str(dst/'source'/'scoped.pdf')); n.close(); d.close()
 for b in sec.blocks:
  for r in b.source_refs: r.page_start=1 if r.page_start<=start else 2; r.page_end=1 if r.page_end<=start else 2
 sec.source_refs=[SourceRef(material='m',page_start=1,page_end=2)]; sec.objectives=['理解本节']; sec.key_terms=['核心概念']; sec.self_test=['能否复述？']
 (dst/'sections.json').write_text(json.dumps([sec.model_dump(mode='json')],ensure_ascii=False,indent=2),encoding='utf-8')
 (dst/'source_pages.json').write_text(json.dumps({'version':1,'material':'m','page_count':2,'pages':[dict(rows[start-1],page=1),dict(rows[end-1],page=2)]},ensure_ascii=False,indent=2),encoding='utf-8')
 pr=json.loads((src/'project.json').read_text()); pr.update({'id':dst.name,'page_count':2,'scope_pages':[1,2],'source_file':'source/scoped.pdf','sections_files':['sections.json']}); (dst/'project.json').write_text(json.dumps(pr,ensure_ascii=False,indent=2),encoding='utf-8')
 try:
  r=build_project(dst/'project.json',pdf=True); print(start,r.get('pdf_backend'),r.get('pdf_pages'),r.get('gate'),flush=True)
 except Exception as e: print(start,'BUILD ERR',type(e).__name__,e,flush=True)

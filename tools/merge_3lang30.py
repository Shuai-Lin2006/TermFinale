
from pathlib import Path
import pymupdf,json
units=[('data/artifacts/combined_routed30.pdf','zh'),('data/artifacts/gen_routed50_en_10p/lecture.pdf','en-1'),('data/artifacts/gen_routed50_en_10p_b/lecture.pdf','en-2'),('data/artifacts/gen_routed50_en_10p_c/lecture.pdf','en-3'),('data/artifacts/gen_routed50_zhhant_10p/lecture.pdf','zh-Hant-1'),('data/artifacts/gen_routed50_zhhant_10p_b/lecture.pdf','zh-Hant-2'),('data/artifacts/gen_routed50_zhhant_10p_c/lecture.pdf','zh-Hant-3')]
out=pymupdf.open(); rows=[]
for path,label in units:
 d=pymupdf.open(path); out.insert_pdf(d); rows.append({'unit':label,'pages':len(d)}); d.close()
out.set_metadata({'title':'TermFinale 三语言 30 页（zh/en/zh-Hant）','author':'TermFinale'}); p=Path('data/artifacts/combined_3lang_30p.pdf'); out.save(str(p)); out.close()
d=pymupdf.open(str(p)); n=len(d); d.close(); Path('data/golden/3lang_30p_manifest.json').write_text(json.dumps({'units':rows,'source_pages_per_lang':30,'pdf_pages':n},ensure_ascii=False,indent=2),encoding='utf-8'); print({'pdf_pages':n,'file':str(p)})

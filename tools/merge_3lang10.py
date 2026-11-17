
from pathlib import Path
import pymupdf,json
units=[('data/artifacts/combined_routed10.pdf','zh-CN'),('data/artifacts/gen_routed50_en_10p/lecture.pdf','en'),('data/artifacts/gen_routed50_zhhant_10p/lecture.pdf','zh-Hant')]
out=pymupdf.open(); rows=[]
for path,label in units:
 d=pymupdf.open(path); out.insert_pdf(d); rows.append({'lang':label,'pdf':path,'pages':len(d)}); d.close()
out.set_metadata({'title':'TermFinale 三语言 10 页样张（zh/en/zh-Hant）','author':'TermFinale'}); p=Path('data/artifacts/combined_3lang_10p.pdf'); out.save(str(p)); out.close()
d=pymupdf.open(str(p)); n=len(d); d.close(); Path('data/golden/3lang_10p_manifest.json').write_text(json.dumps({'units':rows,'pdf_pages':n,'note':'10 source pages; zh/en/zh-Hant; English and Traditional language reports clean'},ensure_ascii=False,indent=2),encoding='utf-8'); print({'pdf_pages':n,'file':str(p)})

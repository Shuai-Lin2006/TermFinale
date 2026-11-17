
from pathlib import Path
import pymupdf,json
units=[('data/artifacts/gen_routed50_pair_1_2/lecture.pdf','1-2'),('data/artifacts/gen_routed50_pair_3_4/lecture.pdf','3-4'),('data/artifacts/gen_routed50_pair_5_6/lecture.pdf','5-6'),('data/artifacts/gen_routed50_pair_7_8/lecture.pdf','7-8'),('data/artifacts/gen_routed50_page_9/lecture.pdf','9')]
out=pymupdf.open(); rows=[]
for path,label in units:
 d=pymupdf.open(path); out.insert_pdf(d); rows.append({'unit':label,'pdf':path,'pages':len(d)}); d.close()
out.set_metadata({'title':'TermFinale 路由10页验证（7讲解+3习题/空页）','author':'TermFinale'}); p=Path('data/artifacts/combined_routed10.pdf'); out.save(str(p)); out.close()
d=pymupdf.open(str(p)); n=len(d); d.close(); Path('data/golden/routed10_manifest.json').write_text(json.dumps({'units':rows,'pdf_pages':n,'content_pages':7,'non_content_pages':3},ensure_ascii=False,indent=2),encoding='utf-8'); print({'pdf_pages':n,'file':str(p)})

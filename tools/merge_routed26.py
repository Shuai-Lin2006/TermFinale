
from pathlib import Path
import pymupdf,json
units=[('data/artifacts/combined_routed20.pdf','20页'),('data/artifacts/gen_routed50_pair_38_39/lecture.pdf','38-39'),('data/artifacts/gen_routed50_pair_40_41/lecture.pdf','40-41'),('data/artifacts/gen_routed50_pair_45_46/lecture.pdf','45-46')]
out=pymupdf.open(); rows=[]
for path,label in units:
 d=pymupdf.open(path); out.insert_pdf(d); rows.append({'unit':label,'pdf':path,'pages':len(d)}); d.close()
out.set_metadata({'title':'TermFinale 路由26页验证（22讲解+4习题/空页）','author':'TermFinale'}); p=Path('data/artifacts/combined_routed26.pdf'); out.save(str(p)); out.close()
d=pymupdf.open(str(p)); n=len(d); d.close(); Path('data/golden/routed26_manifest.json').write_text(json.dumps({'units':rows,'source_pages':26,'content_pages':22,'non_content_pages':4,'pdf_pages':n},ensure_ascii=False,indent=2),encoding='utf-8'); print({'pdf_pages':n,'file':str(p)})

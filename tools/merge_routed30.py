
from pathlib import Path
import pymupdf,json
units=[('data/artifacts/combined_routed26.pdf','26页'),('data/artifacts/gen_routed50_pair_30_36/lecture.pdf','30-36'),('data/artifacts/gen_routed50_pair_47_48/lecture.pdf','47-48')]
out=pymupdf.open(); rows=[]
for path,label in units:
 d=pymupdf.open(path); out.insert_pdf(d); rows.append({'unit':label,'pdf':path,'pages':len(d)}); d.close()
out.set_metadata({'title':'TermFinale 路由30页验证（23讲解+7习题/空页）','author':'TermFinale'}); p=Path('data/artifacts/combined_routed30.pdf'); out.save(str(p)); out.close()
d=pymupdf.open(str(p)); n=len(d); d.close(); Path('data/golden/routed30_manifest.json').write_text(json.dumps({'units':rows,'source_pages':30,'content_pages':23,'non_content_pages':7,'pdf_pages':n},ensure_ascii=False,indent=2),encoding='utf-8'); print({'pdf_pages':n,'file':str(p)})

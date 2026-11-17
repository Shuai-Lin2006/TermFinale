
from pathlib import Path
import pymupdf,json
units=[('data/artifacts/gen_routed50_pair_1_2/lecture.pdf','1-2'),('data/artifacts/gen_routed50_pair_3_4/lecture.pdf','3-4'),('data/artifacts/gen_routed50_pair_5_6/lecture.pdf','5-6'),('data/artifacts/gen_routed50_pair_7_8/lecture.pdf','7-8'),('data/artifacts/gen_routed50_page_9/lecture.pdf','9'),('data/artifacts/gen_routed50_pair_18_19/lecture.pdf','18-19'),('data/artifacts/gen_routed50_pair_20_21/lecture.pdf','20-21'),('data/artifacts/gen_routed50_pair_22_23/lecture.pdf','22-23'),('data/artifacts/gen_routed50_pair_27_28/lecture.pdf','27-28'),('data/artifacts/gen_routed50_pair_34_35/lecture.pdf','34-35')]
out=pymupdf.open(); rows=[]
for path,label in units:
 d=pymupdf.open(path); out.insert_pdf(d); rows.append({'unit':label,'pdf':path,'pages':len(d)}); d.close()
out.set_metadata({'title':'TermFinale 路由20页验证（17讲解+3习题/空页）','author':'TermFinale'}); p=Path('data/artifacts/combined_routed20.pdf'); out.save(str(p)); out.close()
d=pymupdf.open(str(p)); n=len(d); d.close(); Path('data/golden/routed20_manifest.json').write_text(json.dumps({'units':rows,'source_pages':20,'content_pages':17,'non_content_pages':3,'pdf_pages':n},ensure_ascii=False,indent=2),encoding='utf-8'); print({'pdf_pages':n,'file':str(p)})

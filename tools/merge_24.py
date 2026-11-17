
from pathlib import Path
import pymupdf,json
units=[('data/artifacts/combined_20p_delivered.pdf','1-10 + 30-39'),('data/artifacts/gen_100p_pair_11_12/lecture.pdf','11-12'),('data/artifacts/gen_100p_pair_17_18/lecture.pdf','17-18')]
out=pymupdf.open(); rows=[]
for path,label in units:
 d=pymupdf.open(path); out.insert_pdf(d); rows.append({'unit':label,'pdf':path,'pages':len(d)}); d.close()
out.set_metadata({'title':'TermFinale 24页已验收交付','author':'TermFinale'}); p=Path('data/artifacts/combined_24p_delivered.pdf'); out.save(str(p)); out.close()
d=pymupdf.open(str(p)); n=len(d); d.close(); Path('data/golden/combined24_manifest.json').write_text(json.dumps({'units':rows,'pages':n},ensure_ascii=False,indent=2),encoding='utf-8'); print({'pages':n,'file':str(p),'units':len(units)})

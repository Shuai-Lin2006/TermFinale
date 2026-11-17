
from pathlib import Path
import pymupdf,json
units=[('data/artifacts/combined_16p_delivered.pdf','1-10 + 30-31 + 34-35 + 36-37'),('data/artifacts/gen_100p_pair_32_33/lecture.pdf','32-33')]
out=pymupdf.open(); rows=[]
for path,label in units:
 d=pymupdf.open(path); out.insert_pdf(d); rows.append({'unit':label,'pdf':path,'pages':len(d)}); d.close()
out.set_metadata({'title':'TermFinale 18页已验收交付（38-39待复核）','author':'TermFinale'}); p=Path('data/artifacts/combined_18p_delivered.pdf'); out.save(str(p)); out.close()
d=pymupdf.open(str(p)); n=len(d); d.close(); Path('data/golden/combined18_manifest.json').write_text(json.dumps({'units':rows,'pages':n},ensure_ascii=False,indent=2),encoding='utf-8'); print({'pages':n,'file':str(p),'units':len(units)})

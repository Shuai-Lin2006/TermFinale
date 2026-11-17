
from pathlib import Path
import pymupdf,json
units=[('data/artifacts/combined_10p_delivered.pdf','10页'),('data/artifacts/gen_100p_pair_30_31/lecture.pdf','30-31'),('data/artifacts/gen_100p_pair_34_35/lecture.pdf','34-35'),('data/artifacts/gen_100p_pair_36_37/lecture.pdf','36-37')]
out=pymupdf.open(); rows=[]
for path,label in units:
 d=pymupdf.open(path); out.insert_pdf(d); rows.append({'unit':label,'pdf':path,'pages':len(d)}); d.close()
out.set_metadata({'title':'TermFinale 16页已验收交付（32-33/38-39待复核）','author':'TermFinale'}); p=Path('data/artifacts/combined_16p_delivered.pdf'); out.save(str(p)); out.close()
d=pymupdf.open(str(p)); n=len(d); d.close(); Path('data/golden/combined16_manifest.json').write_text(json.dumps({'units':rows,'pages':n},ensure_ascii=False,indent=2),encoding='utf-8'); print({'pages':n,'file':str(p),'units':len(units)})

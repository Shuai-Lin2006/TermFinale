
from pathlib import Path
import pymupdf,json
units=[('data/artifacts/combined_34p_delivered.pdf','34页'),('data/artifacts/gen_100p_pair_59_60/lecture.pdf','59-60'),('data/artifacts/gen_100p_pair_63_64/lecture.pdf','63-64')]
out=pymupdf.open(); rows=[]
for path,label in units:
 d=pymupdf.open(path); out.insert_pdf(d); rows.append({'unit':label,'pdf':path,'pages':len(d)}); d.close()
out.set_metadata({'title':'TermFinale 37页已验收交付','author':'TermFinale'}); p=Path('data/artifacts/combined_37p_delivered.pdf'); out.save(str(p)); out.close()
d=pymupdf.open(str(p)); n=len(d); d.close(); Path('data/golden/combined37_manifest.json').write_text(json.dumps({'units':rows,'pages':n},ensure_ascii=False,indent=2),encoding='utf-8'); print({'pages':n,'file':str(p)})

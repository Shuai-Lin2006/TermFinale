
from pathlib import Path
import pymupdf,json
units=[('data/artifacts/combined_24p_delivered.pdf','24页'),('data/artifacts/gen_100p_pair_21_22/lecture.pdf','21-22'),('data/artifacts/gen_100p_pair_23_24/lecture.pdf','23-24')]
out=pymupdf.open(); rows=[]
for path,label in units:
 d=pymupdf.open(path); out.insert_pdf(d); rows.append({'unit':label,'pdf':path,'pages':len(d)}); d.close()
out.set_metadata({'title':'TermFinale 28页已验收交付','author':'TermFinale'}); p=Path('data/artifacts/combined_28p_delivered.pdf'); out.save(str(p)); out.close()
d=pymupdf.open(str(p)); n=len(d); d.close(); Path('data/golden/combined28_manifest.json').write_text(json.dumps({'units':rows,'pages':n},ensure_ascii=False,indent=2),encoding='utf-8'); print({'pages':n,'file':str(p),'units':len(units)})

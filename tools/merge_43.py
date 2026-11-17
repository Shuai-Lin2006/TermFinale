
from pathlib import Path
import pymupdf,json
units=[('data/artifacts/combined_40p_delivered.pdf','40页'),('data/artifacts/gen_100p_pair_71_72/lecture.pdf','71-72'),('data/artifacts/gen_100p_pair_75_76/lecture.pdf','75-76')]
out=pymupdf.open(); rows=[]
for path,label in units:
 d=pymupdf.open(path); out.insert_pdf(d); rows.append({'unit':label,'pdf':path,'pages':len(d)}); d.close()
out.set_metadata({'title':'TermFinale 43页已验收交付','author':'TermFinale'}); p=Path('data/artifacts/combined_43p_delivered.pdf'); out.save(str(p)); out.close()
d=pymupdf.open(str(p)); n=len(d); d.close(); Path('data/golden/combined43_manifest.json').write_text(json.dumps({'units':rows,'pages':n},ensure_ascii=False,indent=2),encoding='utf-8'); print({'pages':n,'file':str(p)})

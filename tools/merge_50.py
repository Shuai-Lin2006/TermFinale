
from pathlib import Path
import pymupdf,json
units=[('data/artifacts/combined_47p_delivered.pdf','47页'),('data/artifacts/gen_100p_page_73/lecture.pdf','73'),('data/artifacts/gen_100p_page_87/lecture.pdf','87'),('data/artifacts/gen_100p_page_89/lecture.pdf','89')]
out=pymupdf.open(); rows=[]
for path,label in units:
 d=pymupdf.open(path); out.insert_pdf(d); rows.append({'unit':label,'pdf':path,'pages':len(d)}); d.close()
out.set_metadata({'title':'TermFinale 50页已验收交付','author':'TermFinale'}); p=Path('data/artifacts/combined_50p_delivered.pdf'); out.save(str(p)); out.close()
d=pymupdf.open(str(p)); n=len(d); d.close(); Path('data/golden/combined50_manifest.json').write_text(json.dumps({'units':rows,'pages':n},ensure_ascii=False,indent=2),encoding='utf-8'); print({'pages':n,'file':str(p)})

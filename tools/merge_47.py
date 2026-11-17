
from pathlib import Path
import pymupdf,json
units=[('data/artifacts/combined_43p_delivered.pdf','43页'),('data/artifacts/gen_100p_pair_81_82/lecture.pdf','81-82'),('data/artifacts/gen_100p_pair_83_84/lecture.pdf','83-84'),('data/artifacts/gen_100p_pair_85_86/lecture.pdf','85-86')]
out=pymupdf.open(); rows=[]
for path,label in units:
 d=pymupdf.open(path); out.insert_pdf(d); rows.append({'unit':label,'pdf':path,'pages':len(d)}); d.close()
out.set_metadata({'title':'TermFinale 47页已验收交付','author':'TermFinale'}); p=Path('data/artifacts/combined_47p_delivered.pdf'); out.save(str(p)); out.close()
d=pymupdf.open(str(p)); n=len(d); d.close(); Path('data/golden/combined47_manifest.json').write_text(json.dumps({'units':rows,'pages':n},ensure_ascii=False,indent=2),encoding='utf-8'); print({'pages':n,'file':str(p)})

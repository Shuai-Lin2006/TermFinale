
from pathlib import Path
import pymupdf,json
units=[('data/artifacts/gen_struct2p_20261115/lecture.pdf','1-2'),('data/artifacts/gen_pair_3_4_pro/lecture.pdf','3-4'),('data/artifacts/gen_pair_5_6/lecture.pdf','5-6'),('data/artifacts/gen_pair_7_8/lecture.pdf','7-8'),('data/artifacts/gen_pair_9_10/lecture.pdf','9-10')]
out=pymupdf.open(); rows=[]
for path,label in units:
 d=pymupdf.open(path); out.insert_pdf(d); rows.append({'range':label,'pdf':path,'pages':len(d)}); d.close()
out.set_metadata({'title':'TermFinale 10页讲义（5×2页已验收单元）','author':'TermFinale'}); p=Path('data/artifacts/combined_10p_delivered.pdf'); out.save(str(p)); out.close()
d=pymupdf.open(str(p)); total=len(d); d.close()
Path('data/golden/pair_delivery_manifest.json').write_text(json.dumps({'units':rows,'combined':str(p),'pages':total},ensure_ascii=False,indent=2),encoding='utf-8')
print({'pages':total,'file':str(p),'size':p.stat().st_size,'units':len(units)})

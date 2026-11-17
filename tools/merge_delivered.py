
from pathlib import Path
import pymupdf
files=[('data/artifacts/gen_struct2p_20261115/lecture.pdf','1-2'),('data/artifacts/gen_pair_3_4_pro/lecture.pdf','3-4'),('data/artifacts/gen_pair_5_6/lecture.pdf','5-6'),('data/artifacts/gen_pair_9_10/lecture.pdf','9-10')]
out=pymupdf.open()
for path,label in files:
 d=pymupdf.open(path); out.insert_pdf(d); d.close()
out.set_metadata({'title':'TermFinale 8页已验收单元（7-8待复核）','author':'TermFinale'})
p=Path('data/artifacts/combined_8p_delivered.pdf'); out.save(str(p)); out.close()
d=pymupdf.open(str(p)); print({'pages':len(d),'file':str(p),'size':p.stat().st_size}); d.close()

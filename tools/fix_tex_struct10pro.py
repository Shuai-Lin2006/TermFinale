
import json,re
from pathlib import Path
from tfv2.build import build_project
p=Path('data/artifacts/gen_struct10_pro'); secs=json.loads((p/'sections.json').read_text())
def fix(t):
 t=re.sub(r'\\\((.*?)\\\)', r'$\1$', t, flags=re.S)
 t=re.sub(r'\\\[(.*?)\\\]', r'$$\1$$', t, flags=re.S)
 return t
for s in secs:
 for b in s.get('blocks') or []: b['text']=fix(b.get('text') or '')
(p/'sections.json').write_text(json.dumps(secs,ensure_ascii=False,indent=2),encoding='utf-8')
try: r=build_project(p/'project.json',pdf=True); print('OK',r.get('pdf_backend'),r.get('pdf_pages'),r.get('gate'))
except Exception as e: print('ERR',type(e).__name__,e)

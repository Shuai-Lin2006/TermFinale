
import json
from collections import Counter
from pathlib import Path
from tfv2.canonical.page_types import classify_page
p=Path('data/artifacts/gen_20261115_123905_f21786/source_pages.json'); rows=json.loads(p.read_text()).get('pages') or json.loads(p.read_text())
out=[]
for x in rows:
 t=classify_page(x.get('text') or ''); out.append({'page':int(x['page']),'type':t.value})
Path('data/golden/page_types_100p.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(Counter(x['type'] for x in out))
print('content',[x['page'] for x in out if x['type']=='content'][:40])

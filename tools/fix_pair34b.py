
import json
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
from tfv2.llm.qwen_text import QwenTextClient
p=Path('data/artifacts/gen_pair_3_4'); aud=json.loads((p/'coverage_audit.json').read_text()); secs=json.loads((p/'sections.json').read_text())
missing=[]
for x in aud:
 for m in x.get('missing') or []: missing.append((int(x['page_no']),m))
client=QwenTextClient(model='qwen-max')
def work(item):
 pg,m=item
 try:
  d=client.json('你是教材讲解员。只依据缺失点写 3-5 句解释；只输出 JSON：{"text":"..."}。',f'缺失点：{m}\n\n写解释。',max_tokens=500,temperature=0.2); return pg,m,str(d.get('text') or '').strip()
 except Exception: return pg,m,''
got=[]
with ThreadPoolExecutor(max_workers=4) as ex:
 for f in as_completed([ex.submit(work,x) for x in missing]):
  pg,m,t=f.result()
  if t: got.append((pg,m,t))
for i,(pg,m,t) in enumerate(got):
 secs[0]['blocks'].append({'id':f'pairfix2-{i}','kind':'paragraph','text':f'公式/结论：{m}\n讲解：{t}','source_refs':[{'material':'docling','page_start':pg,'page_end':pg,'quote':m[:160]}],'figure':None,'doc_page':None})
(p/'sections.json').write_text(json.dumps(secs,ensure_ascii=False,indent=2),encoding='utf-8'); print('missing',len(missing),'added',len(got))

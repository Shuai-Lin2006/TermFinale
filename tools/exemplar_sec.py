
import json
from pathlib import Path
from tfv2.authoring.lecture import author_section
from tfv2.domain.page import Page,PageLedger,PageQuality
from tfv2.llm.qwen_text import QwenTextClient
from tfv2.canonical.model import CanonicalDocument
pages=json.loads(Path('data/golden/docling_10p/pages.json').read_text()); text={int(x['page_no']):(x.get('text') or '') for x in pages['pages']}
ledger=PageLedger(material='docling',page_count=10,source_hash='docling',parser_version='docling',pages=[Page(material='docling',page_no=i,text=text.get(i,''),quality=PageQuality.OCR) for i in range(1,11)])
doc=CanonicalDocument.model_validate(json.loads(Path('data/golden/canonical_10p_orch.json').read_text())); facts=[f for f in doc.facts if f.page in (1,2)]
ex=json.loads(Path('data/artifacts/gen_struct2p_20261115/sections.json').read_text())[0]['blocks']
exemplar='\n'.join(b['text'] for b in ex[:6])[:3500]
note='参考下面已验收的 2 页写法（结构/公式/例子/易错），不要复制内容；本节必须覆盖 facts：\n'+'\n'.join('- '+f.text for f in facts)+'\n\n【参考写法】\n'+exemplar
sec=author_section(QwenTextClient(model='qwen-max'),ledger,chapter_title='模拟电子技术',section_title='镜像电流源',pages=[1,2],target_score=80,days_left=7,foundation='基础较弱',persona='老师',extra_note=note,gen_lang='zh',clamp_pages=True)
print(json.dumps({'blocks':len(sec.blocks),'kinds':[b.kind.value for b in sec.blocks],'first':[b.text[:200] for b in sec.blocks[:4]]},ensure_ascii=False,indent=1)[:4000])
Path('data/golden/exemplar_sec.json').write_text(json.dumps(sec.model_dump(mode='json'),ensure_ascii=False,indent=2),encoding='utf-8')

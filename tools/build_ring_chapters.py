import re,sys,json
from pathlib import Path
sys.path.insert(0,'.')
from pptx import Presentation
from core.exam_engine import call_ai_with_retry
from core.generate.outline import generate_outline

prs=Presentation('/tmp/tf_p0_convert/第四章 环烃.pptx'); pages=[]
for idx in range(len(prs.slides)):
    txt=[]
    for sh in prs.slides[idx].shapes:
        if hasattr(sh,'text') and sh.text.strip(): txt.append(sh.text.strip())
    pages.append(re.sub(r'<number>','','\n'.join(txt)))
def ai(s,u): return call_ai_with_retry(s,u,temp=0.2,min_budget=3000)
outline=generate_outline(pages,{'name':'第四章 环烃','major':'有机化学','target_score':80},ai_call=ai)
print('outline',outline.source,'chapters',len(outline.chapters))
for c in outline.chapters: print(c.index,c.title,c.pages,c.must_know[:3])
sysp='''你是大学有机化学教材作者。根据本章全部资料，写一节完整教材正文。
硬性要求：
1. 覆盖本章资料的全部定义、分类、命名、结构、构象、性质、反应、例子，不得遗漏，不得新增资料没有的事实；
2. 直接成文，不要出现“原文/讲解/这一页/这里/这句/图示/配图/你可以/我们/页码/P.x”；
3. 第一行必须是 `## <本章标题>`，正文可用 `###` 小标题；
4. 1200–1800 字，教材书面语；不要目录、考点、总结、复习建议；
5. 只输出 Markdown 正文。
'''
secs=[]
for c in outline.chapters:
    text='\n\n'.join(f'【第 {i+1} 页】\n{pages[i]}' for i in c.pages if 0<=i<len(pages))
    user=f'章节标题：{c.title}\n必考点：{"、".join(c.must_know)}\n\n【本章资料】\n{text}'
    out=ai(sysp,user)
    out=re.sub(r'^```(?:markdown)?\s*','',out.strip()); out=re.sub(r'\s*```$','',out)
    out=re.sub(r'(?m)^##\s+.*$', '## '+re.sub(r'^第[一二三四五六七八九十\d]+章[:：]?','',c.title).strip(), out, count=1)
    if not out.startswith('## '): out='## '+c.title+'\n\n'+out
    # clean RDKit images, based on chapter topic
    if '脂环' in c.title and '芳香' not in c.title:
        out+='\n\n[[[IMAGE: ring_alkanes.png | 图注: 环丙烷、环丁烷、环戊烷与环己烷的结构（第 6 页）]]]'
        out+='\n\n[[[IMAGE: ring_unsat.png | 图注: 环戊烯、环辛炔与1,3-环己二烯的结构（第 3 页）]]]'
    if '芳香' in c.title or '苯' in c.title:
        out+='\n\n[[[IMAGE: benzene.png | 图注: 苯的六元环结构（第 30 页）]]]'
    lo=min(c.pages)+1; hi=max(c.pages)+1
    out+=f'\n\n<div class="source-line">来源：P.{lo}–P.{hi}</div>'
    secs.append(out); print('wrote',c.title,'chars',len(out))
must=[]
for c in outline.chapters:
    for k in c.must_know:
        if k and k not in must: must.append(k)
ka='## 本章考点\n\n'+'\n'.join(f'- {k}' for k in must[:12])+'\n'
md=ka+'\n'+'\n\n'.join(secs)+'\n\n---\n\n<div class="source-line">来源：第四章 环烃 P.1–P.50</div>\n'
Path('/tmp/tf_verify/ring_chapters.md').write_text(md,encoding='utf-8')
print('total',len(md),'chapters',len(secs),'must',len(must),'images',md.count('[[[IMAGE:'))

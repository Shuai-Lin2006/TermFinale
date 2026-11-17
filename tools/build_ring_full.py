import re,sys,json
from pathlib import Path
sys.path.insert(0,'.')
from pptx import Presentation
from core.exam_engine import call_ai_with_retry
from core.paths import assets_dir

PPT='/tmp/tf_p0_convert/第四章 环烃.pptx'
prs=Presentation(PPT); pages=[]
for idx in range(len(prs.slides)):
    s=prs.slides[idx]; txt=[]
    for sh in s.shapes:
        if hasattr(sh,'text') and sh.text.strip():
            txt.append(sh.text.strip())
    page='\n'.join(txt)
    page=re.sub(r'<number>','',page)
    pages.append(page)
print('pages',len(pages))
sysp='''你是大学有机化学教材作者。根据给定的 5 页资料，写一节可直接阅读的教材正文。
硬性要求：
1. 覆盖资料里的全部知识点：定义、分类、命名、结构、构象、性质、反应、例子；不得遗漏；不得新增资料没有的事实；
2. 直接成文，不要出现“原文/讲解/这一页/这里/这句/图示/配图/你可以/我们/页码/P.x”；
3. 用 Markdown：第一行必须是 `## <本节标题>`，正文可用 `###` 小标题；
4. 700–1000 字，教材书面语；不要写目录、考点、总结、复习建议；
5. 不要输出代码块或解释，只输出正文。
'''
sections=[]
for start in range(0,len(pages),5):
    chunk=pages[start:start+5]
    text='\n\n'.join(f'【第 {start+i+1} 页】\n{p}' for i,p in enumerate(chunk))
    out=call_ai_with_retry(sysp,f'【资料】\n{text}',temp=0.2,min_budget=4096)
    out=re.sub(r'^```(?:markdown)?\s*','',out.strip()); out=re.sub(r'\s*```$','',out)
    if not re.search(r'(?m)^##\s+',out): out='## 第 %d–%d 页内容\n\n'%(start+1,min(start+5,len(pages)))+out
    out=re.sub(r'(?m)^##\s+', '## ', out, count=1)
    # images clean, inserted by page range
    if start==0:
        out+='\n\n[[[IMAGE: ring_alkanes.png | 图注: 环丙烷、环丁烷、环戊烷与环己烷的结构（第 6 页）]]]'
        out+='\n\n[[[IMAGE: ring_unsat.png | 图注: 环戊烯、环辛炔与1,3-环己二烯的结构（第 3 页）]]]'
    if start==25:
        out+='\n\n[[[IMAGE: benzene.png | 图注: 苯的六元环结构（第 30 页）]]]'
    out+=f'\n\n<div class="source-line">来源：P.{start+1}–P.{min(start+5,len(pages))}</div>'
    sections.append(out)
    print('section',start+1,'chars',len(out),out.splitlines()[0][:50])
# 考点速览
heads=[re.search(r'(?m)^##\s+(.+)',x).group(1) for x in sections]
ksys='''你是大学有机化学老师。根据以下章节标题和资料主题，列出本章 10 条考试考点（必背/常考/易错），每条一句话，具体到知识点；不要编造资料没有的内容；只输出 Markdown 列表，不要标题。'''
kuser='章节：\n'+'\n'.join(heads)+'\n\n资料摘录：\n'+'\n'.join(p[:400] for p in pages[:20])
kout=call_ai_with_retry(ksys,kuser,temp=0.2,min_budget=1500).strip()
kout=re.sub(r'^```(?:markdown)?\s*','',kout); kout=re.sub(r'\s*```$','',kout)
md='## 本章考点速览\n\n'+kout+'\n\n'+'\n\n'.join(sections)+'\n\n---\n\n<div class="source-line">来源：第四章 环烃 P.1–P.50</div>\n'
Path('/tmp/tf_verify/ring_fullbook.md').write_text(md,encoding='utf-8')
print('total',len(md),'sections',len(sections),'images',md.count('[[[IMAGE:'))

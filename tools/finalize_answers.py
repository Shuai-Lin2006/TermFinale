"""把四遍自解整理成：高置信/单源/人工，不伪装官方答案。"""
import json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

def canon(v):
    t=str(v or '')
    t=re.sub(r'\$|\\mathrm|\\left|\\right|\\,|\\;|\\!|[{}\s]', '', t)
    t=t.replace('−','-').replace('，',',').replace('；',';')
    return t.lower()

def main():
    for p in Path('docs/evidence').glob('*_4way.json'):
        d=json.loads(p.read_text(encoding='utf-8')); high=[]; single=[]; manual=[]
        for it in d['items']:
            vals=[it.get('a',''),it.get('b',''),it.get('c',''),it.get('d','')]
            present=[canon(x) for x in vals if canon(x)]
            uniq=list(dict.fromkeys(present))
            if not present:
                manual.append({**it,'reason':'四遍都没有答案'})
            elif len(present)==1:
                single.append({**it,'final':vals[present.index(uniq[0])],'reason':'仅一个模型作答'})
            else:
                counts={}
                for x in present: counts[x]=counts.get(x,0)+1
                best=max(counts.values())
                winners=[x for x,c in counts.items() if c==best]
                if best>=2 and len(winners)==1:
                    high.append({**it,'final':vals[present.index(winners[0])],'reason':f'{best}/{len(present)} 多数'})
                else:
                    manual.append({**it,'reason':'平票或多个不同答案'})
        out={'exam':d['exam'],'mode':'self_consistency_not_official','total':d['questions'],'high':len(high),'single_source':len(single),'manual':len(manual),'high_items':high,'single_items':single,'manual_items':manual}
        dst=p.with_name(p.name.replace('_4way.json','_final.json')); dst.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
        print(d['exam'],'high',len(high),'single',len(single),'manual',len(manual),'saved',dst)
if __name__=='__main__': main()

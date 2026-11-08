"""第三遍自解 + 三方一致性（不是官方答案）。"""
import json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core.parser import extract_text_from_file
from tools.self_solve_exam import solve

def norm(v): return re.sub(r'\s+','',str(v or '')).lower()

def main():
    name=sys.argv[1]; pdf=sys.argv[2]
    p=Path('docs/evidence')/f'{name}_self_solve.json'
    d=json.loads(p.read_text(encoding='utf-8'))
    text='\n\n'.join(extract_text_from_file(pdf))
    c=solve(text)
    a=d.get('answers_a',{}); b=d.get('answers_b',{})
    def get(m,k):
        for key in (f'{k[0]}#{k[1]}', k):
            if key in m: return m[key]
        return ''
    keys=set(a)|set(b)|{f'{k[0]}#{k[1]}' for k in c}
    cc={f'{k[0]}#{k[1]}':v for k,v in c.items()}
    results=[]
    for k in sorted(keys):
        va=get(a,k); vb=get(b,k); vc=cc.get(k,'')
        vals=[norm(va),norm(vb),norm(vc)]
        present=[x for x in vals if x]
        # majority logic
        counts={}
        for x in present: counts[x]=counts.get(x,0)+1
        if not present:
            status='missing'
        elif len(present)>=2 and max(counts.values())>=2:
            status='agree'
        else:
            status='conflict'
        results.append({'key':k,'a':va,'b':vb,'c':vc,'status':status})
    agree=sum(1 for x in results if x['status']=='agree'); conflict=sum(1 for x in results if x['status']=='conflict'); missing=sum(1 for x in results if x['status']=='missing')
    out={'exam':name,'mode':'three_way_self_consistency_not_ground_truth','questions':len(results),'agree':agree,'conflict':conflict,'missing':missing,'items':results}
    dst=Path('docs/evidence')/f'{name}_3way.json'; dst.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:out[k] for k in ('exam','questions','agree','conflict','missing')},ensure_ascii=False)); print('saved',dst)
if __name__=='__main__': main()

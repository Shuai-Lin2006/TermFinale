"""第四遍自解，收敛三方冲突；仍平票的标人工（不是官方答案）。"""
import json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core.parser import extract_text_from_file
from tools.self_solve_exam import solve

def norm(v): return re.sub(r'\s+','',str(v or '')).lower()

def main():
    name=sys.argv[1]; pdf=sys.argv[2]
    p=Path('docs/evidence')/f'{name}_3way.json'; d=json.loads(p.read_text(encoding='utf-8'))
    text='\n\n'.join(extract_text_from_file(pdf))
    fourth=solve(text); fourth={f'{k[0]}#{k[1]}':v for k,v in fourth.items()}
    out=[]
    for it in d['items']:
        vals=[it.get('a',''),it.get('b',''),it.get('c',''),fourth.get(it['key'],'')]
        present=[norm(x) for x in vals if norm(x)]
        counts={}
        for x in present: counts[x]=counts.get(x,0)+1
        if not present:
            status='missing'
        elif len(present)>=2 and max(counts.values())>=2 and list(counts.values()).count(max(counts.values()))==1:
            status='agree'
        else:
            status='conflict'
        out.append({**it,'d':fourth.get(it['key'],''),'four_way_status':status})
    agree=sum(1 for x in out if x['four_way_status']=='agree'); conflict=sum(1 for x in out if x['four_way_status']=='conflict'); missing=sum(1 for x in out if x['four_way_status']=='missing')
    dst=Path('docs/evidence')/f'{name}_4way.json'; dst.write_text(json.dumps({'exam':name,'mode':'four_way_self_consistency_not_ground_truth','questions':len(out),'agree':agree,'conflict':conflict,'missing':missing,'items':out},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'exam':name,'questions':len(out),'agree':agree,'conflict':conflict,'missing':missing},ensure_ascii=False)); print('saved',dst)
if __name__=='__main__': main()

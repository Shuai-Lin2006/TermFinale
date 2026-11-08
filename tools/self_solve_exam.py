"""无标准答案试卷：两遍独立自解 + 一致性标记（不是官方答案）。"""
import json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core.parser import extract_text_from_file
from core.exam_engine import call_ai_with_retry
from core.quality.answer_verify import independent_prompt, parse_independent

def canon_section(s):
    s=str(s or '')
    for kw, name in [('判断','判断题'),('选择','选择题'),('填空','填空题'),('计算','计算题'),('证明','证明题'),('简答','简答题'),('论述','论述题')]:
        if kw in s: return name
    return s.strip()

def solve(text):
    raw=call_ai_with_retry('你是独立阅卷人。只根据题目作答，不引用外部答案。只输出 JSON。', independent_prompt(text), temp=0.2, min_budget=8192)
    return { (canon_section(k[0]),k[1]):v for k,v in parse_independent(raw).items() }

def main():
    path=Path(sys.argv[1]); name=sys.argv[2] if len(sys.argv)>2 else path.stem
    pages=extract_text_from_file(str(path)); text='\n\n'.join(pages)
    a=solve(text); b=solve(text)
    keys=sorted(set(a)|set(b))
    same=[]; diff=[]
    for k in keys:
        va,vb=a.get(k,''),b.get(k,'')
        na=re.sub(r'\s+','',str(va)).lower(); nb=re.sub(r'\s+','',str(vb)).lower()
        if na and na==nb: same.append(k)
        elif na and nb: diff.append((k,va,vb))
    out={'exam':name,'mode':'self_solve_consistency_not_ground_truth','questions':len(keys),'agree':len(same),'disagree':len(diff),'answers_a':{f'{k[0]}#{k[1]}':v for k,v in a.items()},'answers_b':{f'{k[0]}#{k[1]}':v for k,v in b.items()},'disagreements':[{'section':k[0],'no':k[1],'a':va,'b':vb} for k,va,vb in diff]}
    dst=Path('docs/evidence')/f'{name}_self_solve.json'; dst.parent.mkdir(parents=True,exist_ok=True); dst.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:out[k] for k in ('exam','questions','agree','disagree')},ensure_ascii=False)); print('saved',dst)
if __name__=='__main__': main()

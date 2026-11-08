"""独立双解校验：python tools/verify_exam_answers.py <exam.md> [out.json]"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.exam_engine import call_ai_with_retry
from core.quality.answer_verify import (answer_key, compare, independent_prompt,
                                        parse_independent, split_exam)


def main():
    md = Path(sys.argv[1]).read_text(encoding="utf-8")
    q, a = split_exam(md)
    key = answer_key(a)
    raw = call_ai_with_retry(
        "你是独立阅卷人，只根据题目作答，不要臆测已有答案。只输出 JSON。",
        independent_prompt(q), temp=0.1, min_budget=4096)
    got = parse_independent(raw)
    rep = compare(key, got)
    out = {"total": rep.total, "match": rep.match, "mismatch": rep.mismatch,
           "manual": rep.manual,
           "items": [{"section": x.section, "no": x.no, "expected": x.expected,
                      "got": x.got, "status": x.status} for x in rep.items]}
    dst = Path(sys.argv[2] if len(sys.argv) > 2 else "docs/evidence/exam_double_check.json")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("total", "match", "mismatch", "manual")}, ensure_ascii=False))
    for it in out["items"]:
        print(it["status"], it["section"], it["no"], "expected=", it["expected"][:50], "got=", it["got"][:50])


if __name__ == "__main__":
    main()

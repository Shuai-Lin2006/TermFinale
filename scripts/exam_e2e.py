"""出卷 e2e：真实资料出一份两题型的整卷，验收题型、题量、分值、审计、页码。

用法：
  .venv/bin/python scripts/exam_e2e.py [--artifact sel-8918678c191c] [--keep]

验收（任一不满足即非零退出）：
1. 每个题型的题量 = 蓝图题量；
2. 每个题型的分值合计 = 蓝图分值，整卷总分 = 100；
3. 每题都有答案、解析、分值 > 0、来源页落在资料页内；
4. 选择题做了独立答案审计（answer_audit.checked）；
5. 状态只能是 validated / review / rejected，且 rejected 必须写原因。
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SCRATCH = Path(tempfile.mkdtemp(prefix="tf_exam_e2e_"))
DATA = SCRATCH / "data"
(DATA / "artifacts").mkdir(parents=True, exist_ok=True)
os.environ["TFV2_DATA_ROOT"] = str(DATA)

from tfv2.product import service  # noqa: E402
from tfv2.product.exam import run_exam  # noqa: E402

REAL = ROOT / "data" / "artifacts"
FAILURES: list[str] = []
BLUEPRINT = "选择题 8 题 50 分；填空题 4 题 50 分"


def check(cond: bool, msg: str) -> None:
    print(f"  [{'ok' if cond else 'FAIL'}] {msg}")
    if not cond:
        FAILURES.append(msg)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", default="sel-8918678c191c")
    ap.add_argument("--blueprint", default=BLUEPRINT)
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args()

    src = REAL / args.artifact
    if not src.is_dir():
        raise SystemExit(f"缺少真实资料：{src}")
    link = DATA / "artifacts" / args.artifact
    if not link.exists():
        os.symlink(src.resolve(), link, target_is_directory=True)
    pages = (service.get_artifact(args.artifact) or {}).get("page_count") or 0
    print(f"== 出卷 e2e：{args.artifact}（{pages} 页）蓝图：{args.blueprint} ==")

    from tfv2.llm.client import DeepSeekClient
    t0 = time.time()
    doc = run_exam(args.artifact, mode="mock", subject="其他", difficulty=3,
                   blueprint_text=args.blueprint, client=DeepSeekClient(),
                   progress=lambda pct, step: print(f"  [{pct:3d}%] {step}"))
    print(f"  [info] 耗时 {time.time() - t0:.1f}s · status={doc.get('status')}")

    content = doc.get("content") or {}
    sections = content.get("sections") or []
    check(len(sections) == 2, f"题型数 {len(sections)} = 2")
    want_counts = [8, 4]   # 与 BLUEPRINT 一致，且 12 题 = 单卷最少题量
    check([int(s.get("count") or 0) for s in sections] == want_counts,
          f"题量照蓝图执行：{[int(s.get('count') or 0) for s in sections]} = {want_counts}")
    names = [s.get("name") for s in sections]
    print(f"  [info] 题型：{names}")

    rejected_with_reason = doc.get("status") == "rejected" and bool(doc.get("issues"))
    short_sections = []
    for sec in sections:
        qs = sec.get("questions") or []
        want = int(sec.get("count") or 0)
        if len(qs) != want:
            short_sections.append(f"{sec.get('name')} {len(qs)}/{want}")
        check(len(qs) == want or rejected_with_reason,
              f"{sec.get('name')} 题量 {len(qs)}/{want}" + ("（已按原因拒收）" if rejected_with_reason else ""))
        got = round(sum(float(q.get("score") or 0) for q in qs), 1)
        need = round(float(sec.get("score") or 0), 1)
        check(abs(got - need) <= 0.1, f"{sec.get('name')} 分值 {got} = 蓝图 {need}")

    all_qs = [q for sec in sections for q in sec.get("questions") or []]
    total = round(sum(float(q.get("score") or 0) for q in all_qs), 1)
    check(total == 100.0, f"整卷总分 {total} = 100")
    # 选择题用 answer(0-3)，非选择题用 answer_text；两者都不能空。
    def _has_answer(q) -> bool:
        if q.get("qtype") == "choice":
            return isinstance(q.get("answer"), int) and 0 <= q["answer"] <= 3
        return bool(str(q.get("answer_text") or "").strip())

    check(all(_has_answer(q) for q in all_qs), "每题都有答案")
    check(all(str(q.get("analysis") or "").strip() for q in all_qs), "每题都有解析")
    allowed = set((doc.get("coverage") or {}).get("pages") or [])
    bad_pages = [q.get("source_page") for q in all_qs if q.get("source_page") not in allowed]
    check(not bad_pages, f"题目来源页都在资料页内（越界：{bad_pages[:5]}）")

    audit = content.get("answer_audit") or {}
    check(bool(audit.get("checked")), "选择题做了独立答案审计")
    paper = content.get("paper_audit") or {}
    check(paper.get("total_score") == 100.0, f"整卷体检总分 {paper.get('total_score')}")
    check(doc.get("status") in ("validated", "review", "rejected"), f"状态合法：{doc.get('status')}")
    if doc.get("status") == "rejected":
        check(bool(doc.get("issues")), f"rejected 必须写原因：{doc.get('issues')[:3]}")
    warnings = doc.get("warnings") or []
    if warnings:
        print(f"  [info] 生成过程记录：{warnings[:6]}")
    else:
        check(not paper.get("issues"), f"通过时整卷体检无问题：{paper.get('issues')}")

    if args.keep:
        print(f"\n产物文档 json：{SCRATCH / 'exam.json'}")
        (SCRATCH / "exam.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    if FAILURES:
        print(f"\nFAILED（{len(FAILURES)} 条）：")
        for item in FAILURES:
            print(f" - {item}")
        raise SystemExit(1)
    print("\nALL PASSED")
    if not args.keep:
        shutil.rmtree(SCRATCH, ignore_errors=True)


if __name__ == "__main__":
    main()

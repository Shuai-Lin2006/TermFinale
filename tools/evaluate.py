"""批量评测工具：把一组资料跑一遍，输出可写进评测报告的指标。

用法：
    # 只测解析（不花钱）
    python tools/evaluate.py ~/Desktop/a.pdf ~/Desktop/b.pptx

    # 加测 AI 环节（会产生费用，建议先小样本）
    python tools/evaluate.py a.pdf --ai extract,exam
    python tools/evaluate.py a.pdf --ai guide

说明：
- 评测使用独立数据目录 `_backup/eval_home`，不会污染你真实的课程库。
- 报告写到 `evaluation/report_<时间>.md` 和同名 .json。
- 生成质量仍需你人工打分（报告里留了空表）。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("TERMFINALE_HOME", str(ROOT / "_backup" / "eval_home"))
os.environ.setdefault("TERMFINALE_OUTPUT_DIR", str(ROOT / "evaluation" / "artifacts"))
os.environ.setdefault("TERMFINALE_SKIP_PROJECT_ENV", "1")

from core.database import Course, Material, get_db_session  # noqa: E402
from core.parser import extract_text_from_file  # noqa: E402
from services import guide_service, review_service  # noqa: E402

HUMAN_TABLE = """
| 维度 | 1 分 | 3 分 | 5 分 | 你的打分 |
|---|---|---|---|---|
| 知识点覆盖是否完整 | 漏很多 | 少量漏 | 基本完整 |  |
| 是否有编造/错讲 | 明显编造 | 个别错误 | 未发现 |  |
| 结构是否清晰 | 混乱 | 一般 | 清晰可读 |  |
| 图片/公式是否正确 | 大量缺失 | 少量问题 | 基本正确 |  |
| 是否愿意推荐给同学 | 不会 | 看情况 | 会 |  |
"""


def _course_for(name: str, file_path: Path) -> dict:
    db = get_db_session()
    try:
        course = db.query(Course).filter(Course.name == name).first()
        if course:
            db.delete(course)
            db.commit()
        course = Course(name=name, major="评测", school_level="普通一本", credits=3.0,
                        days_left=7, target_score=80, user_difficulty=3, is_major=True)
        db.add(course)
        db.commit()
        db.add(Material(course_id=course.id, file_path=str(file_path),
                        file_type="core", filename=file_path.name))
        db.commit()
        return {"id": course.id, "name": course.name, "major": course.major,
                "school": course.school_level, "credits": course.credits,
                "days_left": course.days_left, "target_score": course.target_score,
                "is_major": course.is_major, "difficulty": course.user_difficulty}
    finally:
        db.close()


def evaluate_file(path: Path, tasks: set[str]) -> dict:
    result: dict = {"file": path.name}
    started = time.time()
    pages = extract_text_from_file(str(path))
    text = "\n\n".join(pages)
    result["parse"] = {
        "pages": len(pages),
        "chars": len(text),
        "images": text.count("[[[IMAGE:"),
        "seconds": round(time.time() - started, 1),
    }
    print(f"  解析：{len(pages)} 页 / {len(text)} 字 / {result['parse']['seconds']}s", flush=True)
    if not text.strip():
        result["error"] = "没有解析到文字"
        return result

    course = _course_for(f"评测-{path.stem}", path)

    if "extract" in tasks:
        started = time.time()
        res = review_service.run_review(course, "extract", text,
                                        extract_type="questions", with_answer=True)
        import re
        result["extract"] = {
            "seconds": round(time.time() - started, 1),
            "chars": res.metrics["chars"],
            "coverage": res.metrics["coverage"],
            "questions": len(re.findall(r"(?m)^\s*(?:\*\*)?\d{1,2}\s*[.、．)）]", res.markdown)),
        }
        print(f"  提取：{result['extract']}", flush=True)

    if "exam" in tasks:
        started = time.time()
        res = review_service.run_review(course, "exam", text, train_type="mock", num_sets=1,
                                        difficulty=3, user_context={"target_score": 80})
        result["exam"] = {k: v for k, v in res.metrics.get("paper", {}).items() if k != "sections"}
        result["exam"]["seconds"] = round(time.time() - started, 1)
        print(f"  试卷：{result['exam']}", flush=True)

    if "guide" in tasks:
        started = time.time()
        res = guide_service.run_guide(course, mode="key", persona="温柔小姐姐")
        m = res.metrics
        result["guide"] = {k: m.get(k) for k in
                           ("chapters", "chapters_done", "empty_calls", "images_expected",
                            "images_reinjected", "chars", "qa_ok", "elapsed_s", "outline_source")}
        print(f"  讲义：{result['guide']}", flush=True)

    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+", help="要评测的资料（pdf/pptx/docx）")
    parser.add_argument("--ai", default="", help="额外跑哪些 AI 环节：extract,exam,guide（逗号分隔）")
    args = parser.parse_args()

    tasks = {t.strip() for t in args.ai.split(",") if t.strip()}
    unknown = tasks - {"extract", "exam", "guide"}
    if unknown:
        print(f"未知环节：{unknown}")
        return 1
    if tasks:
        print(f"⚠️ 将调用 AI 环节：{', '.join(sorted(tasks))}，会产生费用。\n")

    out_dir = ROOT / "evaluation"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M")
    results = []
    for raw in args.files:
        path = Path(raw).expanduser()
        print(f"\n▶ {path.name}", flush=True)
        try:
            results.append(evaluate_file(path, tasks))
        except Exception as exc:  # noqa: BLE001
            print(f"  ❌ 失败：{type(exc).__name__}: {exc}", flush=True)
            results.append({"file": path.name, "error": f"{type(exc).__name__}: {exc}"})

    (out_dir / f"report_{stamp}.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [f"# 评测报告 {stamp}", "", "## 机器指标", "",
             "| 文件 | 页数 | 字数 | 图片 | 解析秒 | 其他 |", "|---|---|---|---|---|---|"]
    for r in results:
        p = r.get("parse", {})
        extra = []
        if "extract" in r:
            extra.append(f"提取 {r['extract']['questions']} 题/覆盖 {r['extract']['coverage']}")
        if "exam" in r:
            extra.append(f"试卷 {r['exam'].get('score_total')} 分/{r['exam'].get('questions')} 题")
        if "guide" in r:
            extra.append(f"讲义 {r['guide'].get('chapters_done')} 章 QA={r['guide'].get('qa_ok')}")
        if r.get("error"):
            extra.append(f"❌ {r['error']}")
        lines.append(f"| {r['file']} | {p.get('pages','-')} | {p.get('chars','-')} | "
                     f"{p.get('images','-')} | {p.get('seconds','-')} | {'；'.join(extra) or '-'} |")
    lines += ["", "## 人工评分（请自己填）", HUMAN_TABLE]
    (out_dir / f"report_{stamp}.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"\n✅ 报告：{out_dir / f'report_{stamp}.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

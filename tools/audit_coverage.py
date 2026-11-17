"""逐页语义覆盖审计 CLI：project.json -> coverage_audit.json/md。

用法：
  PYTHONPATH=. .venv/bin/python tools/audit_coverage.py docs/evidence/v2_circuit_full/project.json
  ... --pages 56,57,58 --workers 3
  ... --only-bad            # 只重审已报告 partial/missing 的页（迭代用）

最终验收必须无 --pages/--only-bad 全量跑一遍。
"""
from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from tfv2.build import load_project
from tfv2.domain.page import Page, PageLedger
from tfv2.ingest.pdf import build_pdf_page_ledger
from tfv2.ingest.pptx import build_pptx_page_ledger
from tfv2.llm.client import DeepSeekClient
from tfv2.quality.coverage_audit import PageCoverage, audit_page


def load_ledger(project_path: Path) -> PageLedger:
    project = load_project(project_path)
    if not project.source_file:
        raise SystemExit("project.json 没有 source_file，无法建立页账本")
    src = (project_path.parent / project.source_file).resolve()
    if src.suffix.lower() == ".pdf":
        return build_pdf_page_ledger(src, material_name=src.name)
    return build_pptx_page_ledger(src, material_name=src.name)


def load_sections(project_path: Path):
    from tfv2.domain.lecture import LectureSection

    project = load_project(project_path)
    sections = []
    for name in project.sections_files:
        data = json.loads((project_path.parent / name).read_text(encoding="utf-8"))
        sections.extend(LectureSection.model_validate(x) for x in data)
    return project, sections


def _audit_one(client, page: Page, sections, overview: bool) -> PageCoverage:
    last: Exception | None = None
    for attempt in range(3):
        try:
            return audit_page(client, page, sections, overview=overview)
        except Exception as exc:  # noqa: BLE001 - 单页失败要记录，不拖垮整轮
            last = exc
            time.sleep(1.5 * (attempt + 1))
    return PageCoverage(
        page_no=page.page_no,
        status="partial",
        missing=[f"审计调用失败，需要重跑：{last}"],
        note="审计失败",
    )


def markdown(results: list[PageCoverage]) -> str:
    lines = ["# 电路全章覆盖审计", "", f"- 页数：{len(results)}", ""]
    bad = [r for r in results if r.status in ("partial", "missing")]
    lines += [
        f"- covered：{sum(1 for r in results if r.status == 'covered')}",
        f"- partial：{sum(1 for r in results if r.status == 'partial')}",
        f"- missing：{sum(1 for r in results if r.status == 'missing')}",
        f"- overview：{sum(1 for r in results if r.status == 'overview')}",
        f"- visual：{sum(1 for r in results if r.status == 'visual')}",
        f"- empty：{sum(1 for r in results if r.status == 'empty')}",
        "",
    ]
    for r in results:
        lines += [f"## 第 {r.page_no} 页 · {r.status}", ""]
        if r.note:
            lines.append(f"- {r.note}")
        for p in r.points:
            if p.covered:
                lines.append(f"- ✓ {p.point}")
            else:
                lines.append(f"- ✗ {p.point}")
        for m in r.missing:
            lines.append(f"- ❌ 缺：{m}")
        lines.append("")
    if bad:
        lines += ["## 未通过页汇总", ""]
        for r in bad:
            lines.append(f"- 第 {r.page_no} 页（{r.status}）：{'；'.join(r.missing) or r.note or ''}")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--pages", help="逗号分隔的页码；默认全量")
    ap.add_argument("--only-bad", action="store_true", help="只重审已有报告中的 partial/missing 页")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--out-json", help="默认写到项目 out_dir/coverage_audit.json")
    ap.add_argument("--out-md", help="默认写到项目 out_dir/coverage_audit.md")
    args = ap.parse_args()

    project_path = Path(args.project).resolve()
    project, sections = load_sections(project_path)
    ledger = load_ledger(project_path)
    out_dir = (project_path.parent / project.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_json = Path(args.out_json) if args.out_json else out_dir / "coverage_audit.json"
    out_md = Path(args.out_md) if args.out_md else out_dir / "coverage_audit.md"

    pages = {p.page_no: p for p in ledger.pages}
    wanted: list[int]
    if args.pages:
        wanted = [int(x) for x in args.pages.split(",") if x.strip()]
    elif args.only_bad and out_json.is_file():
        previous = json.loads(out_json.read_text(encoding="utf-8"))
        wanted = [int(x["page_no"]) for x in previous if x.get("status") in ("partial", "missing")]
    else:
        wanted = sorted(pages)
    wanted = [p for p in wanted if p in pages]
    overview = set(project.overview_pages or [])

    client = DeepSeekClient()
    results: dict[int, PageCoverage] = {}
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {
            pool.submit(_audit_one, client, pages[p], sections, p in overview): p
            for p in wanted
        }
        for fut in as_completed(futures):
            page_no = futures[fut]
            result = fut.result()
            results[page_no] = result
            print(f"  p{page_no:03d} {result.status} missing={len(result.missing)}")

    if args.pages or args.only_bad:
        # 迭代模式：合并旧结果，避免覆盖丢掉已通过的页。
        previous = {}
        if out_json.is_file():
            previous = {int(x["page_no"]): x for x in json.loads(out_json.read_text(encoding="utf-8"))}
        merged = []
        for page_no in sorted(pages):
            if page_no in results:
                merged.append(results[page_no])
            elif page_no in previous:
                merged.append(PageCoverage.model_validate(previous[page_no]))
        final = merged
    else:
        final = [results[p] for p in sorted(results)]

    out_json.write_text(
        json.dumps([r.model_dump() for r in final], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    out_md.write_text(markdown(final), encoding="utf-8")

    counts = Counter(r.status for r in final)
    print("\n汇总：", dict(counts))
    bad = [r for r in final if r.status in ("partial", "missing")]
    if bad:
        print("未通过页：", [r.page_no for r in bad])
        for r in bad:
            print(f"  p{r.page_no}: {r.missing or r.note}")
    print(f"写出：{out_json}")
    print(f"写出：{out_md}")


if __name__ == "__main__":
    main()

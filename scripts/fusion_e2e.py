"""多资料自然融合 e2e 验收：真资料、真产物、真检查。

用法：
  .venv/bin/python scripts/fusion_e2e.py            # 跑 A/B/C 三个用例
  .venv/bin/python scripts/fusion_e2e.py --only B   # 只跑一个
  .venv/bin/python scripts/fusion_e2e.py --author   # 走模型成文（慢、耗 token）

用例：
  A 跨科目：两份不同资料（模拟电子技术 / 数学分析）→ 不应硬合章，出处与搜索必须对；
  B 同教材重叠：同一本书第 1–8 页 + 第 5–12 页 → 同名章节合并，重叠页去重；
  C 扫描件：两份真实扫描 PDF → 原页影像不丢页，不硬转乱码。

任何一条断言失败都非零退出；不允许“看起来还行”就通过。
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

SCRATCH = Path(tempfile.mkdtemp(prefix="tf_fusion_e2e_"))
DATA = SCRATCH / "data"
(DATA / "artifacts").mkdir(parents=True, exist_ok=True)
os.environ["TFV2_DATA_ROOT"] = str(DATA)

from tfv2.product import service  # noqa: E402
from tfv2.product.combine import combine_materials  # noqa: E402
from tfv2.product.source_artifact import create_exam_source  # noqa: E402
from tfv2.product.source_digest import build_source_digest  # noqa: E402

REAL_ARTIFACTS = ROOT / "data" / "artifacts"
TEXTBOOK = REAL_ARTIFACTS / "gen_20261115_123905_f21786"
SCANNED = [
    ROOT / "重庆大学24-25高数上期中.pdf",
    ROOT / "第十五届全国大学生数学竞赛初赛非数A.pdf",
]
BAD_CHARS = ("\ufffd", "\ue000", "锟斤拷", "\uf8ff")
FAILURES: list[str] = []
AUTHOR = False
LLM_CLIENT = None


def check(cond: bool, msg: str) -> None:
    if cond:
        print(f"  [ok] {msg}")
    else:
        print(f"  [FAIL] {msg}")
        FAILURES.append(msg)


def link(aid: str) -> str:
    """把仓库里已有的真实产物挂进本次临时数据目录（只读使用）。"""
    src = REAL_ARTIFACTS / aid
    if not src.is_dir():
        raise SystemExit(f"缺少真实产物：{src}")
    dst = DATA / "artifacts" / aid
    if not dst.exists():
        os.symlink(src, dst, target_is_directory=True)
    return aid


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def inspect(out_id: str, *, expect_pages: int) -> dict:
    dest = service.artifact_path(out_id)
    if dest is None or not (dest / "lecture.pdf").is_file():
        raise SystemExit(f"{out_id}：没有生成 lecture.pdf")
    report = read_json(dest / "fusion_report.json")
    project = read_json(dest / "project.json")
    sections = read_json(dest / "sections.json")
    rows = read_json(dest / "source_pages.json")["pages"]
    html = (dest / "lecture.html").read_text(encoding="utf-8")

    check(project["page_count"] == expect_pages, f"页轴 {project['page_count']} 页，应为 {expect_pages}")
    check(len(rows) == expect_pages, "source_pages 页数与页轴一致")
    missing_refs = [b["id"] for s in sections for b in s.get("blocks") or []
                    if b.get("kind") != "figure" and not b.get("source_refs")]
    check(not missing_refs, f"每个正文块都有出处（{len(missing_refs)} 个缺失）")
    bad_src = [b["id"] for s in sections for b in s.get("blocks") or []
               for r in b.get("source_refs") or [] if int(r.get("source_page") or 0) < 1]
    check(not bad_src, "出处都带原资料页码")
    cited: set[int] = set()
    for s in sections:
        for b in s.get("blocks") or []:
            for r in b.get("source_refs") or []:
                start = int(r["page_start"])
                cited.update(range(start, int(r.get("page_end") or start) + 1))
    missing_pages = sorted(set(range(1, expect_pages + 1)) - cited)
    check(not missing_pages, f"没有丢页（未引用：{missing_pages[:8]}）")
    bad = [c for c in BAD_CHARS if c in html]
    check(not bad, f"无乱码字符（命中：{bad}）")
    check(all(s.get("source_refs") for s in sections), "每节都有出处")
    modes = {}
    for ch in report["chapters"]:
        modes[ch["mode"]] = modes.get(ch["mode"], 0) + 1
    # 模型成文的章节：正文与引用页的支持率不能太低（校准过：真实改写实测 100%）
    authored_rows = [c for c in report["chapters"] if c.get("mode") == "authored"]
    if authored_rows:
        weak = [c for c in authored_rows if (c.get("citation_support") or 0) < 0.5]
        check(not weak, "成文章节引用支持率 ≥50%"
              + ("" if not weak else f"（偏低：{[(c['index'], c.get('citation_support')) for c in weak]}）"))
        ratios = [c.get("citation_support") for c in authored_rows if c.get("citation_support") is not None]
        if ratios:
            print(f"  [info] 成文引用支持率：{min(ratios):.0%}–{max(ratios):.0%}")
    print(f"  [info] 章节 {len(sections)}，成文方式 {modes}，跨资料章 "
          f"{sum(1 for c in report['chapters'] if len(c['materials']) > 1)}")
    return {"dest": dest, "report": report, "sections": sections, "rows": rows, "html": html}


def _pdf_text(path: Path) -> str:
    import pymupdf
    doc = pymupdf.open(str(path))
    try:
        return "\n".join(page.get_text("text") for page in doc)
    finally:
        doc.close()


def searchable(info: dict, *, authored: bool = False) -> None:
    """可搜索性检查。

    digest：原文整行必须原样可搜（文字就是资料原文）；
    authored：模型会改写，不能要求逐行一致；改为验证产物是文本版 + 关键术语覆盖。
    """
    lines = []
    for row in info["rows"]:
        for raw in (row.get("text") or "").splitlines():
            line = raw.strip()
            cjk = "".join(ch for ch in line if "\u4e00" <= ch <= "\u9fff")
            if len(cjk) >= 10:
                lines.append(line)
    probes = lines[:6] + lines[len(lines) // 2: len(lines) // 2 + 6] + lines[-6:]
    probes = [p for p in dict.fromkeys(probes)][:12]
    pdf_text = _pdf_text(Path(info["dest"]) / "lecture.pdf")
    if authored:
        print("  [info] 模型成文：不做逐行原文比对（正文已被改写）")
        probes = []
    else:
        html_hits = sum(1 for p in probes if p in info["html"])
        check(bool(probes) and html_hits >= max(1, len(probes) // 2),
              f"HTML 逐行可搜索（抽检 {len(probes)} 行命中 {html_hits} 行）")
    # PDF 由浏览器渲染，公式/换行会重排，逐行匹配不可靠；改为验证两件事：
    # (1) PDF 是文本版而不是影像（文字量不缩水）；(2) 大段散文段落能原样命中。
    def _cjk(text: str) -> str:
        return "".join(ch for ch in text if "\u4e00" <= ch <= "\u9fff")
    src_cjk = sum(len(_cjk(r.get("text") or "")) for r in info["rows"])
    pdf_cjk = len(_cjk(pdf_text))
    ratio = 0.5 if authored else 0.8
    check(src_cjk == 0 or pdf_cjk >= int(src_cjk * ratio),
          f"PDF 是文本版（正文中文 {pdf_cjk} 字 / 资料 {src_cjk} 字，阈值 {int(ratio*100)}%）")
    prose = []
    for row in info["rows"]:
        for raw in (row.get("text") or "").splitlines():
            line = _cjk(raw)
            if len(line) >= 24:
                prose.append(line[:24])
    prose = [x for x in dict.fromkeys(prose)][:10]
    flat_pdf = _cjk(pdf_text)
    if authored:
        # 改写后比对术语而不是整段：从原文取 4 字片段，看是否仍能在成稿里检索到。
        terms = []
        for row in info["rows"]:
            cjk = _cjk(row.get("text") or "")
            for i in range(0, max(0, len(cjk) - 4), 12):
                terms.append(cjk[i:i + 4])
        terms = [t for t in dict.fromkeys(terms)][:40]
        hits = sum(1 for t in terms if t in flat_pdf)
        check(bool(terms) and hits >= max(3, len(terms) // 4),
              f"成稿仍覆盖资料术语（抽检 {len(terms)} 个术语命中 {hits} 个）")
    else:
        prose_hits = sum(1 for x in prose if x in flat_pdf)
        check(not prose or prose_hits >= max(1, len(prose) // 2),
              f"PDF 里能搜到整段原文（抽检 {len(prose)} 段命中 {prose_hits} 段）")


def case_a() -> None:
    print("\n== 用例 A：跨科目两份资料（不应硬合章）==")
    a = link("sel-8918678c191c")     # 模拟电子技术，60 页
    b = link("sel-9123a789c28c")     # 数学分析，500 页（有 manifest，可被 service 解析）
    materials = [{"artifact_id": a, "pages": list(range(1, 9))},
                 {"artifact_id": b, "pages": list(range(1, 9))}]
    t0 = time.time()
    combine_materials("fuse-e2e-a", materials, title="模电 + 数分 融合测试", course="测试课程",
                      author=AUTHOR, client=LLM_CLIENT, progress=lambda p, s: None)
    print(f"  [info] 生成耗时 {time.time() - t0:.1f}s")
    info = inspect("fuse-e2e-a", expect_pages=16)
    cross = [c for c in info["report"]["chapters"] if len(c["materials"]) > 1]
    check(len(cross) == 0, f"两个不同科目没有按页码硬合章（跨资料章 {len(cross)}）")
    check(len(info["sections"]) >= 2, f"章节数 {len(info['sections'])} ≥ 2")
    searchable(info, authored=AUTHOR)
    labels = {r.get("material") for r in info["rows"]}
    check(len(labels) == 2, f"页轴保留了 2 份资料的来源标记（{len(labels)}）")


def case_b() -> None:
    print("\n== 用例 B：同一教材重叠页（同名章节合并 + 去重）==")
    if not TEXTBOOK.is_dir():
        raise SystemExit(f"缺少教材产物：{TEXTBOOK}")
    base = link(TEXTBOOK.name)
    m1, m2 = "fuse-src-1-8", "fuse-src-5-12"
    build_source_digest(base, list(range(1, 9)), m1)
    build_source_digest(base, list(range(5, 13)), m2)
    rows1 = read_json(service.artifact_path(m1) / "source_pages.json")["pages"]
    src1 = [r.get("source_page") for r in rows1]
    check(src1 == list(range(1, 9)), f"裁切后仍记录原资料页码：{src1}")
    materials = [{"artifact_id": m1, "pages": list(range(1, 9))},
                 {"artifact_id": m2, "pages": list(range(1, 9))}]
    combine_materials("fuse-e2e-b", materials, title="同一教材重叠融合", course="模拟电子技术",
                      author=AUTHOR, client=LLM_CLIENT, progress=lambda p, s: None)
    info = inspect("fuse-e2e-b", expect_pages=16)
    cross = [c for c in info["report"]["chapters"] if len(c["materials"]) > 1]
    check(len(cross) >= 1, f"同名章节跨资料合并成功（{len(cross)} 章）")
    deduped = sum(len(c.get("deduped") or []) for c in info["report"]["chapters"])
    check(deduped >= 1, f"重叠页被去重（命中 {deduped} 处）")
    # 跨资料章节里必须出现过渡句，读者才知道下文换了一份资料
    merged_titles = {c["title"] for c in cross}
    transitions = 0
    for sec in info["sections"]:
        if sec["title"] not in merged_titles:
            continue
        transitions += sum(1 for b in sec.get("blocks") or [] if "衔接" in (b.get("text") or ""))
    check(transitions >= 1, f"跨资料章节有过渡句（{transitions} 处）")
    by_artifact: dict[str, list[int]] = {}
    for item in info["report"]["page_map"]:
        by_artifact.setdefault(item["artifact_id"], []).append(int(item["source_page"]))
    got1 = sorted(set(by_artifact.get(m1, [])))
    got2 = sorted(set(by_artifact.get(m2, [])))
    check(got1 == list(range(1, 9)), f"资料一的出处回到原书 1–8 页：{got1}")
    check(got2 == list(range(5, 13)), f"资料二的出处回到原书 5–12 页：{got2}")
    labels = {r["material"] for r in info["rows"]}
    check(len(labels) == 2, f"两份资料在出处里可区分（{sorted(labels)}）")


def case_c() -> None:
    print("\n== 用例 C：两份真实扫描件（原页影像、不丢页）==")
    for pdf in SCANNED:
        if not pdf.is_file():
            raise SystemExit(f"缺少样张：{pdf}")
    materials = []
    for pdf in SCANNED:
        made = create_exam_source(pdf, title=pdf.stem)
        materials.append({"artifact_id": made["id"], "pages": list(range(1, min(6, made["pages"]) + 1))})
        print(f"  [info] {pdf.name}：{made['pages']} 页，取前 {len(materials[-1]['pages'])} 页")
    combine_materials("fuse-e2e-c", materials, title="扫描件融合测试", course="扫描件",
                      author=AUTHOR, client=LLM_CLIENT, progress=lambda p, s: None)
    expect = sum(len(m["pages"]) for m in materials)
    info = inspect("fuse-e2e-c", expect_pages=expect)
    figs = [b for s in info["sections"] for b in s.get("blocks") or [] if b.get("kind") == "figure"]
    check(len(figs) >= expect, f"扫描页都放了原页影像（{len(figs)} 张 / {expect} 页）")
    check(all(b.get("source_refs") for b in figs), "原页影像带出处")


def case_d() -> None:
    print("\n== 用例 D：不拼接（N 份资料 → N 份讲义）==")
    a = link("sel-8918678c191c")
    b = link("sel-9123a789c28c")
    materials = [{"artifact_id": a, "pages": list(range(1, 5))},
                 {"artifact_id": b, "pages": list(range(1, 5))}]
    result = combine_materials("fuse-e2e-d", materials, merge=False, title="不拼接测试",
                               progress=lambda p, s: None)
    ids = result.get("artifacts") or []
    check(result.get("merge") is False, "结果标记为未拼接")
    check(len(ids) == 2, f"N→N：生成 {len(ids)} 份讲义")
    for aid in ids:
        path = service.artifact_path(aid)
        check(path is not None and (path / "lecture.pdf").is_file(), f"{aid} 有自己独立的 lecture.pdf")
        check((path / "sections.json").is_file(), f"{aid} 有独立目录")
    # 两份讲义的章节归属必须各自独立：不拼接不允许互相引用
    for aid in ids:
        secs = read_json(service.artifact_path(aid) / "sections.json")
        labels = {r.get("material") for s in secs for b in s.get("blocks") or []
                  for r in b.get("source_refs") or []}
        check(len(labels) <= 1, f"{aid} 只引用自己的资料（{sorted(labels)}）")


CASES = {"A": case_a, "B": case_b, "C": case_c, "D": case_d}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="只跑某个用例：A/B/C")
    ap.add_argument("--keep", action="store_true", help="保留临时数据目录")
    ap.add_argument("--author", action="store_true", help="（预留）走模型成文")
    args = ap.parse_args()
    global AUTHOR, LLM_CLIENT
    AUTHOR = bool(args.author)
    if AUTHOR:
        from tfv2.llm.client import DeepSeekClient
        LLM_CLIENT = DeepSeekClient()
        print("[llm] 模型成文已开启")
    started = time.time()
    try:
        for name, fn in CASES.items():
            if args.only and name != args.only.upper():
                continue
            fn()
    finally:
        pass
    print(f"\n总耗时 {time.time() - started:.1f}s")
    if args.keep:
        print(f"产物目录：{DATA / 'artifacts'}")
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

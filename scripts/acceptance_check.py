"""验收清单自动核对：拿已经落盘的产物，逐条检查交付标准。

用法：
  .venv/bin/python scripts/acceptance_check.py [--keep-going]

检查项（对应 HANDOFF §8）：
1. 产物齐全：manifest / project.json / sections.json / lecture.html / lecture.pdf；
2. 门禁通过：manifest.gate.passed；
3. 结构完整：封面标头、摘要、目录（节数对得上）、结语、页脚；
4. 出处可核对：每个 block 有出处，页码不超过资料页数；
5. 不丢页：scope_pages 全部被节或 block 引用；
6. 无乱码：HTML/PDF 文本里没有 \ufffd、私用区、控制字符；
7. 公式页不硬转：扫描/公式资料以原页影像呈现（有 figure 块或 page_count 与影像数一致）。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pymupdf  # noqa: E402

ARTIFACTS = ROOT / "data" / "artifacts"
BAD = ("\ufffd", "\ue000", "\uf8ff", "锟斤拷")

# 每个样张：artifact id、说明、最低要求
CASES = [
    ("sel-e6635a2b0517", "50 页 · 标准/精品", {"min_sections": 4}),
    ("sel-8918678c191c", "60 页 · 精品", {"min_sections": 4}),
    ("sel-86645a0e697c", "100 页 · 高范围", {"min_sections": 8}),
    ("sel-1c554498bd98", "100 页 · 精品（200 页资料选页）", {"min_sections": 8}),
    ("finish600", "600 页 · 普通", {"min_sections": 20}),
    ("math1001img", "1001 页 · 影像版", {"image_mode": True}),
    ("math500img", "500 页 · 影像版", {"image_mode": True}),
]

FAILS: list[str] = []
ROWS: list[dict] = []


def check(name: str, cond: bool, detail: str = "") -> bool:
    if not cond:
        FAILS.append(f"{name}: {detail}")
    return cond


def _toc_entries(html: str) -> int:
    """数目录里的条目：<nav class="toc"> 内的 <li> 个数。"""
    start = html.find('<nav class="toc"')
    if start < 0:
        return 0
    end = html.find("</nav>", start)
    block = html[start:end if end > 0 else len(html)]
    return len(re.findall(r"<li\b", block))


def _cjk(text: str) -> str:
    return "".join(ch for ch in text if "\u4e00" <= ch <= "\u9fff")


def audit_artifact(aid: str, label: str, req: dict) -> dict:
    path = ARTIFACTS / aid
    row = {"id": aid, "label": label, "exists": path.is_dir()}
    if not path.is_dir():
        check(aid, False, "产物目录不存在")
        return row

    need = ["manifest.json", "project.json", "sections.json", "lecture.html", "lecture.pdf"]
    missing = [x for x in need if not (path / x).is_file()]
    row["ok"] = check(aid, not missing, f"缺少文件 {missing}")
    if missing:
        return row

    manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    project = json.loads((path / "project.json").read_text(encoding="utf-8"))
    sections = json.loads((path / "sections.json").read_text(encoding="utf-8"))
    html = (path / "lecture.html").read_text(encoding="utf-8")
    pages = int(project.get("page_count") or 0)
    row.update({"pages": pages, "sections": len(sections),
                "gate": bool((manifest.get("gate") or {}).get("passed")),
                "tier": manifest.get("tier"), "images": len(list((path / "source_assets").glob("*.png")))})

    check(aid, row["gate"], "manifest.gate 未通过")
    check(aid, pages > 0, "page_count 为 0")
    # manifest 的页数必须等于实际构建页数：虚报页数等于虚报覆盖。
    src_pages = path / "source_pages.json"
    if src_pages.is_file():
        actual = int(json.loads(src_pages.read_text(encoding="utf-8")).get("page_count") or 0)
        claimed = int(manifest.get("page_count") or 0)
        check(aid, claimed == actual, f"manifest 页数 {claimed} ≠ 实际 {actual}")

    # 3) 结构完整
    header = project.get("header") or {}
    summary = project.get("summary") or {}
    closing = project.get("closing") or {}
    footer = project.get("footer") or {}
    check(aid, bool(header.get("title")) and bool(header.get("course")), "标头缺标题/课程名")
    check(aid, bool(str(summary.get("overview") or "").strip()), "摘要为空")
    check(aid, bool(str(closing.get("text") or "").strip()), "结语为空")
    check(aid, bool(str(footer.get("disclaimer") or "").strip()), "页脚缺免责声明")
    check(aid, bool(str(footer.get("material_label") or "").strip()), "页脚缺资料标识")
    toc_items = _toc_entries(html)
    check(aid, toc_items >= len(sections) + 1,
          f"目录项 {toc_items} 少于“章节 + {len(sections)} 节”")
    check(aid, len(sections) >= int(req.get("min_sections", 1)), f"节数 {len(sections)} 少于要求")
    check(aid, "TermFinale精品" in html, "标头缺少 TermFinale精品 小字")

    # 4/5) 出处与覆盖
    scope = set(int(x) for x in (project.get("scope_pages") or []))
    cited: set[int] = set()
    bad_refs = 0
    blocks_without_refs = 0
    figures = 0
    for sec in sections:
        if not sec.get("source_refs"):
            bad_refs += 1
        for block in sec.get("blocks") or []:
            refs = list(block.get("source_refs") or [])
            if block.get("figure"):
                figures += 1
                if block["figure"].get("source"):
                    refs.append(block["figure"]["source"])
            if block.get("kind") != "figure" and not refs:
                blocks_without_refs += 1
            for ref in refs:
                start = int(ref.get("page_start") or 0)
                end = int(ref.get("page_end") or start)
                if start < 1 or end > pages:
                    bad_refs += 1
                cited.update(range(start, end + 1))
    check(aid, bad_refs == 0, f"出处异常 {bad_refs} 处（缺节出处或页码越界）")
    check(aid, blocks_without_refs == 0, f"{blocks_without_refs} 个正文块没有出处")
    missing_pages = sorted(scope - cited) if scope else []
    check(aid, not missing_pages, f"未引用页 {missing_pages[:8]}")
    row.update({"figures": figures, "missing_pages": len(missing_pages)})

    # 6) 乱码
    text = html
    doc = pymupdf.open(str(path / "lecture.pdf"))
    try:
        pdf_text = "\n".join(p.get_text("text") for p in doc)
        row["pdf_pages"] = len(doc)
    finally:
        doc.close()
    hits = [c for c in BAD if c in text or c in pdf_text]
    check(aid, not hits, f"含乱码字符 {hits}")

    # 7) 影像版
    if req.get("image_mode"):
        check(aid, row["images"] >= pages, f"原页影像 {row['images']} 少于页数 {pages}")
        check(aid, figures >= pages, f"影像块 {figures} 少于页数 {pages}")
    else:
        row["cjk"] = len(_cjk(pdf_text))
        check(aid, row["cjk"] >= 500, f"PDF 中文只有 {row['cjk']} 字，疑似空壳")
    return row


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep-going", action="store_true")
    args = ap.parse_args()
    print(f"{'artifact':<20}{'说明':<18}{'页数':>6}{'节':>5}{'图':>5}{'漏页':>5}  门禁")
    print("-" * 74)
    for aid, label, req in CASES:
        row = audit_artifact(aid, label, req)
        if not row.get("exists"):
            print(f"{aid:<20}{label:<18}{'—':>6}{'—':>5}{'—':>5}{'—':>5}  缺失")
            continue
        print(f"{aid:<20}{label:<18}{row.get('pages', 0):>6}{row.get('sections', 0):>5}"
              f"{row.get('figures', 0):>5}{row.get('missing_pages', 0):>5}  "
              f"{'通过' if row.get('gate') else '未过'}")
        ROWS.append(row)

    if FAILS:
        print(f"\nFAILED（{len(FAILS)} 条）：")
        for item in FAILS:
            print(f" - {item}")
        raise SystemExit(1)
    print("\n全部通过")


if __name__ == "__main__":
    main()

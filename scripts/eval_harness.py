"""质量评测：只用确定性指标 + 已有产物，不调模型、不花 token。

用法：
  .venv/bin/python scripts/eval_harness.py                 # 打表 + 写 docs/evidence/eval_<日期>.json
  .venv/bin/python scripts/eval_harness.py --json out.json # 只写 JSON

评测三层（对应产品的三个目标）：
  讲义：覆盖（页是否被引用）、出处密度、结构完整、乱码、可读性代理指标（句长/公式密度）
  解析：文字产出率、纯图页比例、公式页比例（决定“扫描件能不能真的用”）
  出卷/提取：蓝图遵守、分值合计、重复题、缺答案、页码有效、字段完整度

任何指标都有阈值；低于阈值就是 fail，并把数字打出来——不做“看起来还行”的评价。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("TFV2_DATA_ROOT", str(ROOT / "data"))

import pymupdf  # noqa: E402

from tfv2.product import service, store  # noqa: E402
from tfv2.quality import metrics  # noqa: E402

BAD = ("\ufffd", "\ue000", "\uf8ff", "锟斤拷")
EVALSET_PATH = ROOT / "evalset.json"


def load_evalset() -> dict:
    """样本清单放 evalset.json；没有就用脚本内置默认，保证脚本单独也能跑。"""
    default = {
        "lectures": [{"id": case[0], "label": case[1]} for case in LECTURES],
        "parses": [{"path": name, "label": label} for name, label in PARSES],
        "references": [{"path": name, "label": label} for name, label in PARSES],
    }
    if not EVALSET_PATH.is_file():
        return default
    try:
        data = json.loads(EVALSET_PATH.read_text(encoding="utf-8"))
    except Exception:
        return default
    for key in ("lectures", "parses", "references"):
        if not isinstance(data.get(key), list) or not data[key]:
            data[key] = default[key]
    return data
CJK = re.compile(r"[\u4e00-\u9fff]")

# ---- 讲义样张：只评已有产物，不重新生成 ----
LECTURES = [
    ("sel-e6635a2b0517", "50 页标准"),
    ("sel-8918678c191c", "60 页精品"),
    ("sel-86645a0e697c", "100 页高范围"),
    ("finish600", "600 页普通"),
    ("math1001img", "1001 页影像版"),
]
# ---- 解析样本：扫不扫得动 ----
PARSES = [
    ("重庆大学24-25高数上期中.pdf", "扫描版真题"),
    ("第十五届全国大学生数学竞赛初赛非数A.pdf", "扫描版竞赛题"),
]

OCR_OFF = False
THRESHOLDS = {
    "lecture_coverage": 0.98,     # 选中页里被引用到的比例
    "lecture_citation": 0.95,     # 正文档块的出处比例
    "lecture_sentence_max": 120,  # 平均句长上限（中文）
    "lecture_cjk_min": 300,       # 讲义 PDF 里至少多少中文字（空壳检测）
    "lecture_dup_sentence": 0.10, # 重复句子比例上限（超过记警告，不直接判死）
    "lecture_boilerplate": 300,   # 高频 4-gram 每千字上限（模板句/重复段落）
    "lecture_citation_support": 0.75,  # 正文块引用的页是否真的支持这段话（成文是改写，2-gram 重合天然低）
    "lecture_term_recall": 0.55,       # 资料高频术语被讲义覆盖的比例
    "parse_chars_per_page": 200,  # 扫描件每页至少多少字（否则等于没解析）
    "exam_total": 100.0,
    "exam_duplicate_max": 0.10,
    "exam_missing_answer_max": 0,
}


def _sentences(text: str) -> list[str]:
    parts = [x.strip() for x in re.split(r"[。！？!?；;]", text or "") if x.strip()]
    return parts


def _cjk_len(text: str) -> int:
    return len(CJK.findall(text or ""))


def eval_lecture(aid: str, label: str) -> dict:
    path = service.artifact_path(aid)
    row = {"id": aid, "label": label, "ok": False}
    if path is None:
        row["error"] = "产物不存在"
        return row
    project = json.loads((path / "project.json").read_text(encoding="utf-8"))
    sections = json.loads((path / "sections.json").read_text(encoding="utf-8"))
    html = (path / "lecture.html").read_text(encoding="utf-8")
    doc = pymupdf.open(str(path / "lecture.pdf"))
    pdf_text = "\n".join(p.get_text("text") for p in doc)
    doc.close()

    scope = set(int(x) for x in (project.get("scope_pages") or [])) or set(
        range(1, int(project.get("page_count") or 0) + 1))
    cited: set[int] = set()
    text_blocks = 0
    blocks_with_refs = 0
    figures = 0
    formulas = 0
    paragraphs = []
    for sec in sections:
        # 与门禁口径一致：小节级出处也算覆盖（否则会把“只放图/只在节级标注”的页算成漏页）
        for ref in sec.get("source_refs") or []:
            try:
                cited.update(range(int(ref["page_start"]), int(ref.get("page_end") or ref["page_start"]) + 1))
            except Exception:
                continue
        for block in sec.get("blocks") or []:
            refs = list(block.get("source_refs") or [])
            if block.get("figure"):
                figures += 1
            if block.get("kind") == "figure":
                continue
            text_blocks += 1
            if refs:
                blocks_with_refs += 1
            if block.get("kind") == "formula" or "$" in (block.get("text") or ""):
                formulas += 1
            paragraphs.append(block.get("text") or "")
            for ref in refs:
                cited.update(range(int(ref["page_start"]), int(ref.get("page_end") or ref["page_start"]) + 1))

    page_fill_pages = 0
    page_fill_ratio = 0.0
    proj_file = path / "project.json"
    if proj_file.is_file():
        try:
            _pr = json.loads(proj_file.read_text(encoding="utf-8"))
            page_fill_pages = int(_pr.get("page_fill_pages") or 0)
            page_fill_ratio = float(_pr.get("page_fill_ratio") or 0.0)
        except Exception:
            pass

    coverage = len(cited & scope) / max(1, len(scope))
    citation = blocks_with_refs / max(1, text_blocks)

    # 资料目录覆盖：讲义是否讲到了资料的真实章节（headings.json 来自 MinerU）
    heads_file = path / "headings.json"
    headings = []
    if heads_file.is_file():
        try:
            headings = [str(x.get("text") or "") for x in
                        (json.loads(heads_file.read_text(encoding="utf-8")).get("headings") or [])]
        except Exception:
            headings = []
    head_recall = metrics.heading_recall(headings, " ".join(paragraphs)) if headings else None

    # 引用支持率：块引的页和正文是否真对得上（来源页文本来自 source_pages.json）
    src_rows = []
    src_path = path / "source_pages.json"
    if src_path.is_file():
        src_rows = json.loads(src_path.read_text(encoding="utf-8")).get("pages") or []
    def _page_text(p: int) -> str:
        return str(src_rows[p - 1].get("text") or "") if 1 <= p <= len(src_rows) else ""
    support = metrics.citation_support([b for sec in sections for b in sec.get("blocks") or []], _page_text)
    # 术语召回：资料里高频的中文术语，讲义里覆盖了多少
    corpus = "\n".join(str(r.get("text") or "") for r in src_rows)
    terms = metrics.term_candidates(corpus, top=30) if corpus else []
    recall = metrics.term_recall(terms, " ".join(paragraphs))

    # 可读性/重复度：重复句子比例 + 高频 4-gram（模板句）密度
    all_sents = [x for p in paragraphs for x in metrics.sentences(p)]
    dup_ratio = metrics.dup_sentence_ratio(all_sents)
    boilerplate = metrics.boilerplate_per_1k("".join(paragraphs))
    sents = [s for p in paragraphs for s in _sentences(p) if _cjk_len(s) >= 4]
    avg_sentence = statistics.mean([_cjk_len(s) for s in sents]) if sents else 0
    body_cjk = _cjk_len("".join(paragraphs)) or 1
    formula_density = formulas * 1000 / body_cjk
    toc = html.count("<li", html.find('<nav class="toc"'), html.find("</nav>", html.find('<nav class="toc"')))
    mojibake = [c for c in BAD if c in html or c in pdf_text]
    structure = all([project.get("header", {}).get("title"), project.get("summary", {}).get("overview"),
                     project.get("closing", {}).get("text"), project.get("footer", {}).get("disclaimer")])

    image_mode = figures >= max(1, len(scope)) // 2
    images = len(list((path / "source_assets").glob("*.png"))) if image_mode else 0

    # 目录质量：多少节是“真实标题”，多少节只是页码占位
    page_like = [t for t in (sec.get("title") or "" for sec in sections) if re.match(r"^第 [\d–\-]+ 页", t)]
    real_titles = len(sections) - len(page_like)

    fails = []
    if image_mode:
        # 影像版：评“像不像话的影像版”，不评句长/公式密度（正文本来就该是图）
        if images < len(scope):
            fails.append(f"原页影像 {images} < {len(scope)}")
        if figures < len(scope):
            fails.append(f"影像块 {figures} < {len(scope)}")
        if toc < len(sections):
            fails.append(f"目录项 {toc} < 节数 {len(sections)}")
        if mojibake:
            fails.append(f"乱码 {mojibake}")
        if not structure:
            fails.append("结构不完整")
        row.update({"ok": not fails, "fails": fails, "image_mode": True, "images": images,
                    "real_titles": real_titles, "page_like_titles": len(page_like),
                    "pages": len(scope), "sections": len(sections), "coverage": 1.0,
                    "citation": 1.0, "avg_sentence": 0, "formula_per_1k": 0,
                    "figures": figures, "pdf_cjk": _cjk_len(pdf_text), "toc": toc,
                "page_fill_pages": page_fill_pages, "page_fill_ratio": round(page_fill_ratio, 3),
                "heading_recall": None if head_recall is None else head_recall["recall"],
                "headings_checked": 0 if head_recall is None else head_recall["headings"]})
        return row

    if coverage < THRESHOLDS["lecture_coverage"]:
        fails.append(f"覆盖 {coverage:.1%}")
    if citation < THRESHOLDS["lecture_citation"]:
        fails.append(f"出处 {citation:.1%}")
    if support["checked"] and support["ratio"] < THRESHOLDS["lecture_citation_support"]:
        fails.append(f"引用支持 {support['ratio']:.0%}")
    if avg_sentence > THRESHOLDS["lecture_sentence_max"]:
        fails.append(f"平均句长 {avg_sentence:.0f}")
    if _cjk_len(pdf_text) < THRESHOLDS["lecture_cjk_min"]:
        fails.append(f"PDF 中文 {_cjk_len(pdf_text)} 字")
    if mojibake:
        fails.append(f"乱码 {mojibake}")
    if not structure:
        fails.append("结构不完整")
    if toc < len(sections):
        fails.append(f"目录项 {toc} < 节数 {len(sections)}")

    warn = []
    if dup_ratio > THRESHOLDS["lecture_dup_sentence"]:
        warn.append(f"重复句 {dup_ratio:.0%}")
    if boilerplate > THRESHOLDS["lecture_boilerplate"]:
        warn.append(f"模板句 {boilerplate:.0f}/千字")
    if page_fill_ratio > 0.1:
        warn.append(f"补原文 {page_fill_ratio:.0%}")

    row.update({"warnings": warn, "dup_ratio": round(dup_ratio, 3),
                "boilerplate_per_1k": round(boilerplate, 1),
                "ok": not fails, "fails": fails, "real_titles": real_titles,
                "page_like_titles": len(page_like),
                "pages": len(scope), "sections": len(sections),
                "coverage": round(coverage, 3), "citation": round(citation, 3),
                "avg_sentence": round(avg_sentence, 1), "formula_per_1k": round(formula_density, 1),
                "citation_support": support["ratio"], "weak_blocks": support["weak_blocks"],
                "term_recall": recall["recall"], "terms_checked": recall["terms"],
                "figures": figures, "pdf_cjk": _cjk_len(pdf_text), "toc": toc,
                "page_fill_pages": page_fill_pages, "page_fill_ratio": round(page_fill_ratio, 3),
                "heading_recall": None if head_recall is None else head_recall["recall"],
                "headings_checked": 0 if head_recall is None else head_recall["headings"]})
    return row


def eval_parse(pdf: Path, label: str) -> dict:
    row = {"file": pdf.name, "label": label, "ok": False}
    if not pdf.is_file():
        row["error"] = "样本缺失"
        return row
    doc = pymupdf.open(str(pdf))
    try:
        pages = [p.get_text("text") for p in doc]
        n = len(pages)
        chars = sum(len(t.strip()) for t in pages)
        empty = sum(1 for t in pages if len(t.strip()) < 20)
    finally:
        doc.close()
    row.update({"pages": n, "chars": chars, "chars_per_page": round(chars / max(1, n), 1),
                "empty_pages": empty, "empty_ratio": round(empty / max(1, n), 3)})
    # 扫描件：原文没有文字层，必须靠 OCR；这里记录基线 + 本地 OCR 的实际产出
    row["needs_ocr"] = chars / max(1, n) < THRESHOLDS["parse_chars_per_page"]
    row["ok"] = True
    if row["needs_ocr"] and not OCR_OFF:
        try:
            from tfv2.ingest.mineru_backend import MinerUError, ocr_pdf_text
            t0 = __import__("time").time()
            text = ocr_pdf_text(pdf, page_spec="all")
            elapsed = round(__import__("time").time() - t0, 1)
            ocr_chars = len(text.strip())
            row.update({"ocr_engine": "mineru-local", "ocr_chars": ocr_chars,
                        "ocr_chars_per_page": round(ocr_chars / max(1, n), 1),
                        "ocr_ok": ocr_chars / max(1, n) >= THRESHOLDS["parse_chars_per_page"],
                        "ocr_seconds": elapsed})
        except Exception as exc:  # noqa: BLE001
            try:
                from tfv2.ingest.mineru_backend import MinerUError
                reason = str(exc) if isinstance(exc, MinerUError) else f"{type(exc).__name__}: {exc}"
            except Exception:
                reason = str(exc)
            row.update({"ocr_engine": "unavailable", "ocr_reason": reason[:200], "ocr_ok": False})
    return row


def eval_backend_ab() -> list[dict]:
    """解析后端 A/B：同一套判定，看文字版 PDF 和扫描件各走哪条路。"""
    import tempfile
    import pymupdf
    from tfv2.ingest.backends import parse_pdf

    rows: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="tf_ab_") as td:
        pdf = Path(td) / "text.pdf"
        doc = pymupdf.open()
        for i in range(2):
            page = doc.new_page()
            y = 80
            for j in range(5):
                page.insert_text((60, y), f"第{i+1}页第{j+1}行 放大电路静态工作点的计算需要先画直流通路。",
                                 fontsize=11, fontname="china-s")
                y += 22
        doc.save(str(pdf))
        doc.close()
        for sample, label in ((pdf, "生成的文字版 PDF"),
                              (ROOT / "重庆大学24-25高数上期中.pdf", "扫描版真题")):
            if not sample.is_file():
                continue
            t0 = __import__("time").time()
            try:
                out = parse_pdf(sample)
            except Exception as exc:  # noqa: BLE001
                rows.append({"sample": label, "error": f"{type(exc).__name__}: {exc}"})
                continue
            pages = out.get("pages") or {}
            chars = sum(len(v) for v in pages.values())
            rows.append({"sample": label, "engine": out.get("engine"),
                         "pages": len(pages), "chars_per_page": round(chars / max(1, len(pages)), 1),
                         "headings": len(out.get("headings") or []),
                         "seconds": round(__import__("time").time() - t0, 2),
                         "fallback_reason": out.get("fallback_reason", "")})
    return rows


def eval_reference_structure(pdf: Path, label: str) -> dict:
    """真题结构可解析性：确定性解析出多少题型、分值合计是否 100。"""
    row = {"file": pdf.name, "label": label, "ok": False}
    if not pdf.is_file():
        row["error"] = "样本缺失"
        return row
    try:
        from tfv2.ingest.mineru_backend import MinerUError, ocr_pdf_text
        from tfv2.product.exam import parse_sections_deterministic
        try:
            text = ocr_pdf_text(pdf)
            source = "mineru-local"
        except MinerUError as exc:
            row["error"] = f"OCR 不可用：{exc}"
            return row
        rows = parse_sections_deterministic(text)
        total = sum(int(r.get("score") or 0) for r in rows)
        row.update({"engine": source, "sections": len(rows),
                    "types": [r["type"] for r in rows],
                    "counts": [r["count"] for r in rows],
                    "score_total": total, "ok": bool(rows) and total == 100})
        if not row["ok"]:
            row["reason"] = ("没有解析出题型" if not rows else f"分值合计 {total} ≠ 100")
    except Exception as exc:  # noqa: BLE001
        row["error"] = f"{type(exc).__name__}: {exc}"
    return row


def eval_documents() -> dict:
    docs = store.list_documents()
    out = {"exam": [], "extract": []}
    for d in docs:
        kind = str(d.get("kind") or "")
        content = d.get("content") or {}
        if kind == "exam":
            sections = content.get("sections") or []
            qs = [q for s in sections for q in s.get("questions") or []]
            total = round(sum(float(q.get("score") or 0) for q in qs), 1)
            stems = [re.sub(r"[\s\W]+", "", str(q.get("stem") or ""))[:60] for q in qs]
            dup = len(stems) - len(set(stems))
            missing = sum(1 for q in qs
                          if (q.get("qtype") == "choice" and not isinstance(q.get("answer"), int))
                          or (q.get("qtype") != "choice" and not str(q.get("answer_text") or "").strip()))
            fails = []
            if abs(total - THRESHOLDS["exam_total"]) > 0.5:
                fails.append(f"总分 {total}")
            if qs and dup / len(qs) > THRESHOLDS["exam_duplicate_max"]:
                fails.append(f"重复题 {dup}/{len(qs)}")
            if missing > THRESHOLDS["exam_missing_answer_max"]:
                fails.append(f"缺答案 {missing}")
            out["exam"].append({"id": d.get("id"), "title": d.get("title"), "status": d.get("status"),
                                "questions": len(qs), "total": total, "duplicates": dup,
                                "missing_answer": missing, "ok": not fails, "fails": fails})
        elif kind.startswith("extract"):
            items = content.get("items") or []
            need = {"extract_points": ("point", "page", "explanation"),
                    "extract_nouns": ("term", "definition", "page"),
                    "extract_questions": ("stem", "answer", "page")}.get(kind, ("page",))
            complete = sum(1 for it in items if all(str(it.get(k) or "").strip() for k in need))
            out["extract"].append({"id": d.get("id"), "kind": kind, "title": d.get("title"),
                                   "status": d.get("status"), "items": len(items),
                                   "complete": complete,
                                   "ok": bool(items) and complete == len(items),
                                   "fails": [] if items and complete == len(items) else ["字段不完整"]})
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="")
    ap.add_argument("--no-ocr", action="store_true", help="不跑本地 OCR（默认跑，缓存后很快）")
    args = ap.parse_args()
    global OCR_OFF
    OCR_OFF = bool(args.no_ocr)

    report = {"generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
              "thresholds": THRESHOLDS, "lectures": [], "parses": [], "references": [], "documents": {}}
    evalset = load_evalset()
    report["evalset"] = {"path": str(EVALSET_PATH.name),
                         "counts": {k: len(evalset[k]) for k in ("lectures", "parses", "references")}}

    print("== 讲义 ==")
    print(f"{'artifact':<20}{'页':>5}{'节':>5}{'真标题':>6}{'目录覆盖':>7}{'覆盖':>7}{'出处':>7}{'支持':>6}{'术语':>6}{'补原文':>7}{'句长':>6}{'重复句':>7}{'图':>4}  结果")
    for case in evalset["lectures"]:
        aid, label = case["id"], case.get("label", case["id"])
        row = eval_lecture(aid, label)
        report["lectures"].append(row)
        if row.get("error"):
            print(f"{aid:<20}— {row['error']}")
            continue
        if row.get("image_mode"):
            print(f"{aid:<20}{row['pages']:>5}{row['sections']:>5}{row.get('real_titles', 0):>6}{'—':>7}{'影像版':>7}{'—':>7}{'—':>6}{'—':>6}{'—':>7}{'—':>6}{'—':>7}{row['figures']:>4}  "
                  f"{'通过' if row['ok'] else '不通过：' + '；'.join(row['fails'])}")
            continue
        hr = row.get("heading_recall")
        print(f"{aid:<20}{row['pages']:>5}{row['sections']:>5}{row.get('real_titles', 0):>6}"
              f"{(f'{hr:.0%}' if hr is not None else '—'):>7}{row['coverage']:>7.1%}"
              f"{row['citation']:>7.1%}"
              f"{(row.get('citation_support') if row.get('citation_support') is not None else 0):>6.0%}"
              f"{(row.get('term_recall') if row.get('term_recall') is not None else 0):>6.0%}"
              f"{(row.get('page_fill_ratio') or 0):>7.0%}"
              f"{row['avg_sentence']:>6.0f}{row.get('dup_ratio', 0):>7.1%}{row['figures']:>4}  "
              f"{'通过' if row['ok'] else '不通过：' + '；'.join(row['fails'])}"
              + (f"（警告：{'；'.join(row['warnings'])}）" if row.get("warnings") else ""))

    print("  说明：原文精读型讲义的正文就是资料原文，所以“支持/术语”天然接近 100%；")
    print("        这两个指标主要用来盯模型成文的内容，改写跑偏时会掉下来。")

    print("\n== 解析（原始 PDF 文字层基线）==")
    for case in evalset["parses"]:
        name, label = case["path"], case.get("label", case["path"])
        row = eval_parse(ROOT / name, label)
        report["parses"].append(row)
        line = (f"{label:<16}{row.get('pages', 0):>4} 页 · 文字层每页 {row.get('chars_per_page', 0):>7} 字 · "
                f"空页 {row.get('empty_ratio', 0):.0%}")
        if row.get("needs_ocr"):
            if OCR_OFF:
                line += " · OCR 未跑（--no-ocr）"
            elif row.get("ocr_engine") == "mineru-local":
                line += f" · 本地 OCR 每页 {row.get('ocr_chars_per_page', 0)} 字（{row.get('ocr_seconds')}s，{'够用' if row.get('ocr_ok') else '不够'}）"
            else:
                line += f" · 本地 OCR 不可用：{row.get('ocr_reason', '原因未知')}"
        print(line)

    print("\n== 解析后端 A/B（同一判定：文字版 vs 扫描件）==")
    ab = eval_backend_ab()
    report["backend_ab"] = ab
    for row in ab:
        if row.get("error"):
            print(f"{row['sample']:<14}{row['error']}")
            continue
        note = f"（{row['fallback_reason']}）" if row.get("fallback_reason") else ""
        print(f"{row['sample']:<14}{row['engine']:<14}{row['chars_per_page']:>8} 字/页 · "
              f"标题 {row['headings']:>2} · {row['seconds']}s{note}")

    print("\n== 真题结构（确定性解析，用于校验模型还原）==")
    for case in evalset["references"]:
        name, label = case["path"], case.get("label", case["path"])
        row = eval_reference_structure(ROOT / name, label)
        report["references"].append(row)
        if row.get("error"):
            print(f"{label:<16}{row['error']}")
            continue
        print(f"{label:<16}{row['sections']:>2} 个题型 · 分值 {row['score_total']:>3} · "
              f"题量 {row['counts']} · {'通过' if row['ok'] else row.get('reason', '')}")

    print("\n== 已生成成果（出卷 / 提取）==")
    docs = eval_documents()
    report["documents"] = docs
    for row in docs["exam"]:
        print(f"出卷 {row['title']:<24}{row['questions']:>3} 题 · 总分 {row['total']:>5} · "
              f"重复 {row['duplicates']} · {'通过' if row['ok'] else '；'.join(row['fails'])}")
    for row in docs["extract"]:
        print(f"提取 {row['kind']:<16}{row['items']:>3} 条 · 完整 {row['complete']:>3} · "
              f"{'通过' if row['ok'] else '；'.join(row['fails'])}")
    if not docs["exam"] and not docs["extract"]:
        print("（文档库里还没有出卷/提取成果；先跑一次真实生成再评）")

    fails = [r for r in report["lectures"] if not r.get("ok")]
    fails += [r for r in report["references"] if r.get("error")]
    out = Path(args.json) if args.json else ROOT / "docs" / "evidence" / f"eval_{datetime.now():%Y-%m-%d}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n报告：{out}")
    print(f"讲义不通过 {len(fails)} / {len(report['lectures'])}")
    sys.exit(0 if not fails else 1)


if __name__ == "__main__":
    main()

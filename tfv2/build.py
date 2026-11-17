"""通用讲义构建：project.json -> Gate -> HTML -> PDF -> 体检/图源/清单。

用法：
  PYTHONPATH=. .venv/bin/python -m tfv2.build path/to/project.json
  ... --no-pdf
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
from pathlib import Path

from pydantic import BaseModel, Field

from tfv2.authoring.assemble import build_lecture_spec
from tfv2.authoring.lecture import _sanitize_visible_text
from tfv2.domain.lecture import (
    LanguagePolicy,
    LectureClosing,
    LectureFooter,
    LectureHeader,
    LectureSection,
    LectureSummary,
)
from tfv2.quality.content_gate import report_markdown as content_report_markdown
from tfv2.quality.content_gate import scan_lecture, scan_pdf_text
from tfv2.quality.figure_report import build_figure_report, report_markdown as figure_report_markdown
from tfv2.quality.coverage_matrix import build_coverage_matrix, save_coverage_matrix
from tfv2.quality.evidence_report import build_evidence_report, save_evidence_report
from tfv2.quality.review import review_and_revise, review_markdown
from tfv2.quality.subject_profiles import capability_gate, capability_matrix, gate_markdown, matrix_markdown
from tfv2.render.formula_asset import collect_formula_assets, formula_report_markdown
from tfv2.quality.layout_gate import layout_report_markdown, validate_layout
from tfv2.quality.language_gate import check_language, report_markdown as language_report_markdown
from tfv2.quality.pdf_gate import validate_pdf
from tfv2.quality.lecture_gate import validate_lecture
from tfv2.retrieval import build_index
from tfv2.render.lecture_html import write_lecture_html
from tfv2.render.pdf import write_pdf

ROOT = Path(__file__).resolve().parents[1]


class Project(BaseModel):
    id: str = Field(min_length=1)
    chapter_title: str = Field(min_length=1)
    header: LectureHeader
    summary: LectureSummary
    closing: LectureClosing
    footer: LectureFooter
    sections_files: list[str] = Field(min_length=1)
    page_count: int = Field(ge=1)
    coverage_percent: float = Field(ge=0, le=100)
    scope_pages: list[int] = Field(default_factory=list)
    overview_pages: list[int] = Field(default_factory=list)
    overview_mode: bool = False
    assets_dir: str | None = None
    source_file: str | None = None
    out_dir: str = Field(min_length=1)
    language_policy: LanguagePolicy | None = None
    constraints: dict = Field(default_factory=dict)


def load_project(path: str | Path) -> Project:
    p = Path(path)
    return Project.model_validate_json(p.read_text(encoding="utf-8"))


def _inject_katex(html_path: Path, root: Path = ROOT) -> None:
    """把 KaTeX 复制进产物自身，屏幕阅读和 file:// PDF 都能加载。

    之前用相对源码目录的路径，打包后 URL 变成
    /Desktop/TermFinale.app/Contents/Frameworks/web/...，浏览器必然 404。
    """
    asset_src = root / "web" / "assets" / "katex"
    asset_dst = html_path.parent / "assets" / "katex"
    if asset_src.is_dir():
        shutil.copytree(asset_src, asset_dst, dirs_exist_ok=True)
        rel = "assets/katex"
    else:
        rel = "/katex"
    html = html_path.read_text(encoding="utf-8")
    inject = (
        f'<link rel="stylesheet" href="{rel}/katex.inline.css">'
        f'<script src="{rel}/katex.min.js"></script>'
        f'<script src="{rel}/mhchem.min.js"></script>'
        f'<script src="{rel}/auto-render.min.js"></script>'
    )
    html = html.replace("<!--TF_HEAD_EXTRA-->", inject)
    html = html.replace(
        "<!--TF_BODY_EXTRA-->",
        "<script>renderMathInElement(document.body,{delimiters:[{left:'$$',right:'$$',display:true},"
        "{left:'$',right:'$',display:false}],throwOnError:false,output:'html'});</script>",
    )
    html_path.write_text(html, encoding="utf-8")


def _pdf_page_count(path: Path) -> int:
    import pymupdf
    d = pymupdf.open(path)
    try:
        return len(d)
    finally:
        d.close()


def _pdf_text(path: Path) -> str:
    import pymupdf
    d = pymupdf.open(path)
    try:
        return "\n".join(page.get_text("text") for page in d)
    finally:
        d.close()


def _pdf_image_count(path: Path) -> int:
    import pymupdf
    d = pymupdf.open(path)
    try:
        return sum(len(page.get_images()) for page in d)
    finally:
        d.close()


def _norm_pdf_text(text: str) -> str:
    import re
    import unicodedata
    text = re.sub(r"\$[^$]*\$", "", text or "")
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "", text)
    return text


def _block_coverage(sections, pdf_text: str) -> dict:
    import re
    corpus = _norm_pdf_text(pdf_text)
    total = 0
    hit = 0
    missing: list[str] = []
    for sec in sections:
        for block in sec.blocks:
            if str(getattr(block.kind, "value", block.kind)) in ("figure", "formula"):
                continue
            if "$" in (block.text or ""):
                continue
            raw = re.sub(r"\$[^$]*\$", "", block.text or "")
            raw = re.sub(r"[\s\u2060]+", "", raw)
            if len(raw) < 16:
                continue
            total += 1
            key = _norm_pdf_text(raw)[:18]
            if key and key in corpus:
                hit += 1
            else:
                missing.append((sec.title or "")[:20])
    return {"total": total, "hit": hit, "missing": missing[:10]}


def _compare_markdown(compare: dict) -> str:
    html = compare.get("html") or {}
    typ = compare.get("typst") or {}
    lines = ["# 讲义输出对比", "", f"- 决策：**{compare.get('decision')}**",
             f"- 原因：{compare.get('reason') or '通过'}", "",
             "| 指标 | HTML/KaTeX | Typst |", "|---|---:|---:|",
             f"| 页数 | {html.get('pages', 0)} | {typ.get('pages', '-')} |",
             f"| 图片数 | {html.get('images', 0)} | {typ.get('images', '-')} |",
             f"| 文本字符 | {html.get('font_chars', 0)} | {typ.get('font_chars', '-')} |",
             f"| 章节命中 | - | {typ.get('titles_hit', '-')} |",
             f"| 正文块命中 | - | {typ.get('block_hit', '-')}/{typ.get('block_total', '-')} |",
             f"| 图注命中 | - | {typ.get('caption_hit', '-')}/{typ.get('caption_total', '-')} |", ""]
    return "\n".join(lines)


_TEX_WORD = {
    "beta": "β", "alpha": "α", "gamma": "γ", "mu": "μ", "pi": "π",
    "parallel": "∥", "cdot": "·", "times": "×", "le": "≤", "ge": "≥",
    "approx": "≈", "infty": "∞", "pm": "±", "sqrt": "√",
}

def _plain_one(t: str) -> str:
    for _ in range(3):
        t = re.sub(r"\\frac\{([^{}]*)\}\{([^{}]*)\}", r"\1/\2", t)
    t = re.sub(r"\\text\{([^{}]*)\}", r"\1", t)
    t = re.sub(r"\\(?:left|right|displaystyle)\b", "", t)
    t = re.sub(r"\\([A-Za-z]+)", lambda m: _TEX_WORD.get(m.group(1), m.group(1)), t)
    t = t.replace("\\{", "{").replace("\\}", "}").replace("\\_", "_")
    return t


def _plain_inline_tex(text: str) -> str:
    """Only clean TeX outside $...$; inline math must reach KaTeX unchanged."""
    parts = re.split(r"(\$\$.*?\$\$|\$[^$]*\$)", text or "", flags=re.S)
    return "".join(p if (i % 2 == 1) else _plain_one(p) for i, p in enumerate(parts))


def build_project(project_path: str | Path, *, pdf: bool = True) -> dict:
    project_path = Path(project_path)
    project = load_project(project_path)
    base = project_path.parent
    out = (base / project.out_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    if project.assets_dir:
        src = (base / project.assets_dir).resolve()
        if not src.is_dir():
            raise FileNotFoundError(f"assets_dir 不存在：{src}")
        shutil.copytree(src, out / "assets", dirs_exist_ok=True)

    sections: list[LectureSection] = []
    for name in project.sections_files:
        data = json.loads((base / name).read_text(encoding="utf-8"))
        sections.extend(LectureSection.model_validate(x) for x in data)

    for sec in sections:
        if sec.title:
            sec.title = _sanitize_visible_text(sec.title)
        if sec.summary:
            sec.summary = _sanitize_visible_text(sec.summary)
        for block in sec.blocks:
            if block.text:
                block.text = _sanitize_visible_text(block.text)
                if block.kind.value != "formula":
                    block.text = _plain_inline_tex(block.text)
            if block.figure and block.figure.caption:
                block.figure.caption = _sanitize_visible_text(block.figure.caption)

    (out / 'retrieval_index.json').write_text(
        build_index(project.id, sections).model_dump_json(indent=2), encoding='utf-8')
    spec = build_lecture_spec(
        chapter_title=project.chapter_title,
        header=project.header,
        summary=project.summary,
        sections=sections,
        closing=project.closing,
        footer=project.footer,
        page_count=project.page_count,
        coverage_percent=project.coverage_percent,
        scope_pages=project.scope_pages,
        overview_mode=bool(project.overview_mode),
        language_policy=project.language_policy,
    )
    report = validate_lecture(spec)
    if not report.passed:
        raise ValueError("讲义 Gate 未通过：" + "；".join(x.message for x in report.issues))
    review_report, review_applied = review_and_revise(spec)
    (out / "review_report.json").write_text(
        json.dumps({"report": review_report, "applied": review_applied}, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "review_report.md").write_text(review_markdown(review_report, review_applied), encoding="utf-8")
    coverage_matrix = build_coverage_matrix(spec)
    save_coverage_matrix(coverage_matrix, out)
    formula_assets = collect_formula_assets(spec)
    (out / "formula_report.json").write_text(
        json.dumps([x.__dict__ for x in formula_assets], ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "formula_report.md").write_text(formula_report_markdown(formula_assets), encoding="utf-8")
    language = None
    if project.source_file:
        from tfv2.ingest.pdf import build_pdf_page_ledger
        from tfv2.ingest.pptx import build_pptx_page_ledger
        src_path = (base / project.source_file).resolve()
        if src_path.suffix.lower() == ".pdf":
            ledger = build_pdf_page_ledger(src_path, material_name=src_path.name)
        else:
            ledger = build_pptx_page_ledger(src_path, material_name=src_path.name)
        language = check_language(spec, ledger)
        (out / "language_report.md").write_text(language_report_markdown(language), encoding="utf-8")
        if not language.passed:
            raise ValueError("语言检查未通过：" + "；".join(x.message for x in language.issues))

    html_path = write_lecture_html(spec, out / "lecture.html")
    _inject_katex(html_path)
    content = scan_lecture(spec)
    result = {
        "id": project.id, "chapter_title": project.chapter_title, "out": str(out),
        "gate": {"passed": True, "issues": []}, "sections": len(sections),
        "coverage_matrix": coverage_matrix,
        "review": review_report,
        "formula_report": {"count": len(formula_assets),
                           "fallback": sum(1 for x in formula_assets if x.status != "ok")},
        "content_gate": content.model_dump(),
    }
    if not content.passed:
        raise ValueError("内容体检未通过：" + "；".join(x.message for x in content.issues))
    pdf_backend = "none"
    html_pdf = out / "lecture_html.pdf"
    if pdf:
        html_pdf, mapping, html_pages = write_pdf(html_path, html_pdf, spec)
        result["pdf_pages"] = html_pages
        result["toc_pages"] = mapping
        pdf_content = scan_pdf_text(html_pdf)
        result["pdf_content_gate"] = pdf_content.model_dump()
        if not pdf_content.passed:
            raise ValueError(
                "PDF 内容体检未通过："
                + "；".join(x.message for x in pdf_content.issues if x.severity == "hard")
            )
        gate = validate_pdf(html_pdf, sections)
        if gate:
            raise ValueError("PDF 硬门禁未通过：" + "；".join(gate))
        layout = validate_layout(html_pdf)
        result["layout_report"] = layout
        (out / "layout_report.json").write_text(
            json.dumps(layout, ensure_ascii=False, indent=2), encoding="utf-8")
        (out / "layout_report.md").write_text(layout_report_markdown(layout), encoding="utf-8")
        if not layout.get("passed", True):
            raise ValueError("PDF 版面硬门禁未通过：" + "；".join(
                x["message"] for x in layout.get("issues") or [] if x.get("severity") == "hard"))
        chosen = html_pdf
        chosen_pages = html_pages
        chosen_backend = "html"
        compare = {
            "html": {"pdf": str(html_pdf), "pages": html_pages,
                     "images": _pdf_image_count(html_pdf),
                     "font_chars": len(_pdf_text(html_pdf))},
            "typst": None, "decision": "html",
        }

        if os.getenv("TERMFINALE_LATEX", "1").strip().lower() not in ("0", "false", "no"):
            try:
                from tfv2.render.latex_lecture import compile_latex, render_latex
                tex = render_latex(spec, out / "lecture.tex", root=out)
                lpdf = out / "lecture_latex.pdf"
                ok, err = compile_latex(tex, lpdf, root=out)
                if ok:
                    ltxt = _pdf_text(lpdf)
                    lpages = _pdf_page_count(lpdf)
                    limgs = _pdf_image_count(lpdf)
                    lcontent = scan_pdf_text(lpdf)
                    lpdf_issues = validate_pdf(lpdf, sections)
                    lcov = _block_coverage(sections, ltxt)
                    titles_hit = sum(1 for sec in sections if sec.title.strip() and _norm_pdf_text(sec.title) in _norm_pdf_text(ltxt))
                    compare["latex"] = {"pdf": str(lpdf), "pages": lpages, "images": limgs,
                                        "titles_hit": titles_hit, "block_hit": lcov["hit"],
                                        "block_total": lcov["total"], "block_missing": lcov["missing"]}
                    if (not lpdf_issues and lcontent.passed and titles_hit == len(sections)
                            and (not lcov["total"] or lcov["hit"] >= int(lcov["total"] * 0.9))
                            and lpages >= max(1, int(html_pages * 0.5))
                            and (not compare["html"]["images"] or limgs >= 1)):
                        chosen, chosen_pages, chosen_backend = lpdf, lpages, "latex"
                        compare["decision"] = "latex"
                        result["pdf_content_gate"] = lcontent.model_dump()
                        result["toc_pages"] = {}
                else:
                    compare["latex_error"] = err[:500]
            except Exception as exc:
                compare["latex_error"] = str(exc)

        formula_fallbacks = [a for a in formula_assets if a.status != "ok"]
        if chosen_backend == "html" and formula_fallbacks and os.getenv("TERMFINALE_TYPST", "").strip().lower() in ("1", "true", "yes"):
            compare["formula_fallback"] = len(formula_fallbacks)
            compare["decision"] = "html"
            compare["reason"] = f"存在 {len(formula_fallbacks)} 条无法原生渲染的公式，Typst 不接管"
            result["typst_error"] = compare["reason"]
        elif chosen_backend == "html" and os.getenv("TERMFINALE_TYPST", "").strip().lower() in ("1", "true", "yes"):
            try:
                from tfv2.render.typst_lecture import compile_typst, render_typst
                typ_path = render_typst(spec, out / "lecture.typ", asset_root=out)
                typ_pdf = out / "lecture_typst.pdf"
                ok, typ_err = compile_typst(typ_path, typ_pdf, root=out)
                result["typst_pdf"] = str(typ_pdf) if ok else None
                result["typst_error"] = "" if ok else typ_err
                if ok and typ_pdf.is_file():
                    typ_text = _pdf_text(typ_pdf)
                    typ_pages = _pdf_page_count(typ_pdf)
                    typ_imgs = _pdf_image_count(typ_pdf)
                    typ_issues = validate_pdf(typ_pdf, sections)
                    typ_content = scan_pdf_text(typ_pdf)
                    typ_layout = validate_layout(typ_pdf)
                    titles_hit = sum(1 for sec in sections if sec.title.strip() and _norm_pdf_text(sec.title) in _norm_pdf_text(typ_text))
                    block_cov = _block_coverage(sections, typ_text)
                    captions = [b.figure.caption for sec in sections for b in sec.blocks if b.figure is not None]
                    caption_hit = sum(1 for c in captions if c and _norm_pdf_text(c)[:16] in _norm_pdf_text(typ_text))
                    html_imgs = compare["html"]["images"]
                    compare["typst"] = {
                        "pdf": str(typ_pdf), "pages": typ_pages, "images": typ_imgs,
                        "font_chars": len(typ_text), "titles_hit": titles_hit,
                        "block_hit": block_cov["hit"], "block_total": block_cov["total"],
                        "block_missing": block_cov["missing"],
                        "caption_hit": caption_hit, "caption_total": len(captions),
                        "issues": typ_issues,
                        "content_hard": [x.code for x in typ_content.issues if x.severity == "hard"],
                        "layout_hard": [x for x in (typ_layout.get("issues") or []) if x.get("severity") == "hard"],
                    }
                    reason = ""
                    if typ_issues:
                        reason = "Typst PDF 硬门禁：" + "；".join(typ_issues)
                    elif not typ_content.passed:
                        reason = "Typst PDF 内容体检未通过"
                    elif not typ_layout.get("passed", True):
                        reason = "Typst 版面硬门禁未通过"
                    elif titles_hit < len(sections):
                        reason = f"Typst 缺少章节标题：{titles_hit}/{len(sections)}"
                    elif block_cov["total"] and block_cov["hit"] < max(1, int(block_cov["total"] * 0.9)):
                        reason = f"Typst 正文块命中不足：{block_cov['hit']}/{block_cov['total']}"
                    elif captions and caption_hit < len(captions):
                        reason = f"Typst 图注命中不足：{caption_hit}/{len(captions)}"
                    elif "资料页码索引" not in _norm_pdf_text(typ_text):
                        reason = "Typst 缺少资料页码索引"
                    elif html_imgs and typ_imgs < min(html_imgs, 1):
                        reason = "Typst 图片数量少于 HTML 版"
                    elif typ_pages < max(1, int(html_pages * 0.5)):
                        reason = "Typst 页数异常偏少"
                    if reason:
                        compare["decision"] = "html"
                        compare["reason"] = reason
                        result["typst_error"] = reason
                    else:
                        chosen = typ_pdf
                        chosen_pages = typ_pages
                        chosen_backend = "typst"
                        compare["decision"] = "typst"
                        result["layout_report"] = typ_layout
                        result["pdf_content_gate"] = typ_content.model_dump()
                        result["toc_pages"] = {}
                else:
                    compare["decision"] = "html"
                    compare["reason"] = typ_err[:500]
            except Exception as exc:
                result["typst_error"] = str(exc)
                compare["decision"] = "html"
                compare["reason"] = str(exc)

        shutil.copyfile(chosen, out / "lecture.pdf")
        result["pdf_pages"] = chosen_pages
        result["pdf_backend"] = chosen_backend
        result["output_compare"] = compare
        (out / "output_compare.json").write_text(json.dumps(compare, ensure_ascii=False, indent=2), encoding="utf-8")
        (out / "output_compare.md").write_text(_compare_markdown(compare), encoding="utf-8")
        pdf_backend = chosen_backend

    figures = build_figure_report(spec, out)
    capability = capability_matrix(spec, formula_assets=formula_assets, figures=figures)
    result["capability_matrix"] = capability
    evidence_rows = build_evidence_report(spec)
    evidence = save_evidence_report(evidence_rows, out)
    result["evidence_report"] = {"summary": evidence, "rows": evidence_rows}
    capability_checks = capability_gate(capability)
    result["capability_gate"] = capability_checks
    (out / "capability_matrix.json").write_text(json.dumps(capability, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "capability_matrix.md").write_text(matrix_markdown(capability), encoding="utf-8")
    (out / "capability_gate.json").write_text(json.dumps(capability_checks, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "capability_gate.md").write_text(gate_markdown(capability_checks), encoding="utf-8")
    (out / "figure_report.json").write_text(
        json.dumps([x.model_dump() for x in figures], ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "figure_report.md").write_text(figure_report_markdown(figures), encoding="utf-8")
    (out / "content_gate.json").write_text(
        json.dumps(result["content_gate"], ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "content_gate.md").write_text(content_report_markdown({"讲义文本": content}), encoding="utf-8")
    fact_coverage = None
    try:
        source_pages_path = base / "source_pages.json"
        if source_pages_path.is_file():
            from tfv2.quality.fact_map import facts_for_pages, map_facts, save_map
            raw = json.loads(source_pages_path.read_text(encoding="utf-8"))
            page_text = {int(p["page"]): (p.get("text") or "") for p in (raw.get("pages") or raw)}
            fact_result = map_facts(facts_for_pages(page_text, list(page_text)), sections)
            save_map(fact_result, out / "fact_map.json")
            fact_coverage = {"total": fact_result["total"], "covered": fact_result["covered"],
                             "coverage": fact_result["coverage"]}
            result["fact_coverage"] = fact_coverage
    except Exception as exc:
        result["fact_map_error"] = str(exc)
    manifest = {
        "artifact": project.id, "chapter": project.chapter_title, "page_count": project.page_count,
        "scope_pages": project.scope_pages, "scope_coverage": (f"{len(project.scope_pages)}/{project.page_count} 页" if project.scope_pages else "全量"),
        "sections": len(sections), "figures": len(figures), "gate": result["gate"],
        "coverage_matrix": result.get("coverage_matrix"),
        "formula_report": result.get("formula_report"),
        "subject_profile": result.get("capability_matrix", {}).get("profile"),
        "capability_matrix": result.get("capability_matrix"),
        "capability_gate": result.get("capability_gate"),
        "evidence": result.get("evidence_report", {}).get("summary"),
        "review": result.get("review"),
        "constraints": project.constraints,
        "content_gate": result["content_gate"],
        "pdf_content_gate": result.get("pdf_content_gate"),
        "pdf_pages": result.get("pdf_pages"), "toc_pages": result.get("toc_pages"),
        "pdf_backend": result.get("pdf_backend"),
        "output_compare": result.get("output_compare"),
        "layout_report": result.get("layout_report"),
        "typst_pdf": result.get("typst_pdf"),
        "typst_error": result.get("typst_error"),
        "language": language.model_dump() if language else None,
        "fact_coverage": fact_coverage,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--no-pdf", action="store_true")
    args = ap.parse_args()
    result = build_project(args.project, pdf=not args.no_pdf)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

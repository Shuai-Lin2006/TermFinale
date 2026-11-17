"""按原文分页构建资料精读版；用于大范围/超大资料，不依赖逐页 LLM 重写。"""
from __future__ import annotations

import json
import re
import shutil
import unicodedata
from pathlib import Path

import pymupdf

from tfv2.build import build_project
from tfv2.domain.page_unit import build_page_unit
from tfv2.product import service



def _clean_text(value: str) -> str:
    out = []
    for ch in str(value or ""):
        code = ord(ch)
        if 0xE000 <= code <= 0xF8FF:
            continue
        if unicodedata.category(ch).startswith("C"):
            continue
        out.append(ch)
    return re.sub(r"\s+", " ", "".join(out)).strip()

PARAGRAPH_DEDUPE_MIN = 60


def paragraph_key(text: str) -> str:
    """段落指纹：去空白后的前 160 字，用于发现跨节重复段落。"""
    norm = re.sub(r"\s+", "", str(text or ""))
    return norm[:160] if len(norm) >= PARAGRAPH_DEDUPE_MIN else ""


def duplicate_paragraph_of(text: str, seen: dict[str, int]) -> int | None:
    key = paragraph_key(text)
    if not key:
        return None
    return seen.get(key)


def register_paragraph(text: str, seen: dict[str, int], page: int) -> None:
    key = paragraph_key(text)
    if key and key not in seen:
        seen[key] = page


DUPLICATE_TEXT_MIN = 24


def duplicate_page_of(text: str, seen: dict[str, int]) -> int | None:
    """这段页文字之前出现过吗？返回第一次出现的原页码；太短的不算重复。"""
    norm = re.sub(r"\s+", "", text or "")
    if len(norm) < DUPLICATE_TEXT_MIN:
        return None
    return seen.get(norm)


def register_page_text(text: str, seen: dict[str, int], page: int) -> None:
    norm = re.sub(r"\s+", "", text or "")
    if len(norm) >= DUPLICATE_TEXT_MIN and norm not in seen:
        seen[norm] = page


def page_should_be_image(text: str, kind: str, *, ocr_used: bool = False,
                        scan_mode: bool = False, text_from_ocr: bool = False) -> bool:
    """这一页讲义里应该放原页影像还是文字。

    扫描/公式页默认影像；OCR 补出来的文字默认只用于检索，
    除非用户明确要“文字版”（text_from_ocr=True）。
    """
    if scan_mode:
        return True
    body = text or ""
    if ocr_used:
        # OCR 页：默认影像；用户要文字版就排文字（除非真的没文字）。
        return not text_from_ocr or len(body.strip()) < 24
    if kind in ("formula", "image"):
        return True
    if len(body) < 24:
        return True
    return False


def _source_pdf(src: Path) -> Path:
    """找到可渲染的 PDF：原始 PDF 在 source/，Office/图片转好的在 source_pdf/。"""
    for folder in ("source", "source_pdf"):
        base = src / folder
        if not base.is_dir():
            continue
        for item in sorted(base.iterdir()):
            if item.is_file() and item.suffix.lower() == ".pdf":
                return item
    raise FileNotFoundError(f"artifact 缺少可渲染的 PDF：{src}")


_PAGE_SUFFIX = re.compile(r"\s*第\s*\d+(?:\s*[–\-—]\s*\d+)?\s*页")


def material_label(src: Path, artifact_id: str, rows: list[dict] | None = None) -> str:
    """资料的人类可读名字：优先 manifest/project 里的标题，绝不把产物 id 当标题。

    产物 id 形如 gen_20261117_075523_b380d7，出现在讲义标题里就是机器语。
    """
    candidates: list[str] = []
    for name, keys in (("manifest.json", ("title", "chapter", "course")),
                       ("project.json", ("chapter_title",))):
        path = src / name
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if name == "project.json":
            candidates.append(str((data.get("header") or {}).get("title") or ""))
        for key in keys:
            candidates.append(str(data.get(key) or ""))
    for row in rows or []:
        candidates.append(str(row.get("material") or ""))
    for raw in candidates:
        text = Path(raw).stem if raw.lower().endswith((".pdf", ".pptx", ".docx", ".doc", ".ppt")) else raw
        text = re.sub(r"\s+", " ", _PAGE_SUFFIX.sub("", text)).strip(" ·-—")
        if text and not re.fullmatch(r"(gen|sel|sk|ref)_[0-9a-f_]+", text):
            return text
    return "资料"


def _project_base(src: Path, all_rows: list[dict], artifact_id: str) -> dict:
    """资料库里的原始资料没有 project.json；这里补一个最小可用的讲义基座。"""
    path = src / "project.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    material = material_label(src, artifact_id, all_rows)
    page_count = max(1, len(all_rows))
    return {
        "id": artifact_id,
        "chapter_title": material,
        "header": {"title": material, "course": material, "persona": "老师",
                   "materials": [], "coverage_scope": f"{page_count} 页", "generated_at": ""},
        "summary": {"overview": f"按原文覆盖资料 {page_count} 页。", "knowledge_map": []},
        "closing": {"persona": "老师", "text": "先按目录读原文，再对照出处回看资料页。"},
        "footer": {"agent_name": "TermFinale", "coverage_percent": 100.0,
                   "material_label": material,
                   "disclaimer": "具体请以实际资料为准，本资料不承担由此产生的法律责任。"},
        "sections_files": ["sections.json"], "page_count": page_count,
        "coverage_percent": 100.0, "scope_pages": list(range(1, page_count + 1)),
        "overview_pages": [], "overview_mode": False,
        "source_file": "source/scoped.pdf", "assets_dir": "source_assets", "out_dir": ".",
        "language_policy": {"ui_lang": "zh", "gen_lang": "简体中文", "source_lang": None,
                            "translation_mode": "none"},
    }


def _section_plan(src: Path, chosen: list[int], group_size: int) -> list[tuple[str, list[int]]]:
    """分节计划：有真实标题就按标题切；没有就按页段切，标题写明页码。

    标题来自 headings.json（MinerU 解析），页码是**父 artifact 的页码**，与 chosen 同一坐标系。
    """
    from tfv2.product import headings as heads

    rows = heads.normalize_headings(heads.load_headings(src))
    if rows:
        chapters = heads.chapters_from_headings(rows, chosen, chunk=group_size)
        plan = [(c["title"], c["pages"]) for c in chapters]
        if plan:
            return plan
    return [(f"第 {g[0]} 页" if len(g) == 1 else f"第 {g[0]}–{g[-1]} 页", g)
            for g in (chosen[i:i + group_size] for i in range(0, len(chosen), group_size))]


def build_source_digest(artifact_id: str, pages: list[int], output_id: str, progress=None, *,
                        scan_mode: bool = False, group_size: int = 10,
                        dpi: int = 110, text_from_ocr: bool = False) -> Path:
    """构建原文精读/影像版讲义。

    scan_mode=True 时每一页都放原页影像（扫描件、公式教材、无可提取文字的页），
    绝不把“原页影像版”这种占位文字当成正文交上去。
    """
    src = service.artifact_path(artifact_id)
    if src is None:
        raise FileNotFoundError("artifact not found")
    raw = json.loads((src / "source_pages.json").read_text(encoding="utf-8"))
    all_rows = raw.get("pages") or raw
    requested = [int(p) for p in pages]
    out_of_range = sorted({p for p in requested if p < 1 or p > len(all_rows)})
    if out_of_range:
        # 静默丢页会把“选了 150 页”做成“只有 100 页”还标成已交付，必须直接拒绝。
        raise ValueError(f"页码超出资料范围（资料共 {len(all_rows)} 页）：{out_of_range[:8]}")
    chosen = sorted(set(requested))
    if not chosen:
        raise ValueError("没有有效页码")
    out = service.artifact_path(output_id) or (src.parent / output_id)
    if out.exists():
        shutil.rmtree(out)
    (out / "source").mkdir(parents=True)
    (out / "source_assets").mkdir()
    if progress:
        progress(10, "裁取资料页")
    sp = _source_pdf(src)
    d = pymupdf.open(str(sp))
    n = pymupdf.open()
    rows = []
    for i, p in enumerate(chosen, 1):
        n.insert_pdf(d, from_page=p - 1, to_page=p - 1)
        row = dict(all_rows[p - 1])
        row["page"] = i
        # 原页码：父 artifact 若已裁切过就沿用它记的值，否则 p 就是原页码。
        row["source_page"] = int(all_rows[p - 1].get("source_page") or p)
        rows.append(row)
    n.save(str(out / "source" / "scoped.pdf"))
    n.close(); d.close()
    (out / "source_pages.json").write_text(json.dumps(
        {"version": 1, "material": artifact_id,
         "origin_material": str(raw.get("origin_material") or raw.get("material") or artifact_id),
         "origin_pages": [int(x["source_page"]) for x in rows],
         "page_count": len(rows), "pages": rows},
        ensure_ascii=False, indent=2), encoding="utf-8")

    render = pymupdf.open(str(out / "source" / "scoped.pdf"))
    try:
        notes = json.loads((src / "page_notes.json").read_text(encoding="utf-8"))
    except Exception:
        notes = {}
    # 每 group_size 页一个章节目录；不出现“第 N 页补讲”
    group_size = max(1, min(50, int(group_size)))
    groups = _section_plan(src, chosen, group_size)
    from tfv2.product import formulas as formula_mod
    formula_map = formula_mod.load_formulas(src)
    sections = []
    # 重复页登记：同一段文字出现多次（同一份资料里重复扫描/重复页）只展开第一次。
    seen_pages: dict[str, int] = {}
    deduped_pages: list[dict] = []
    seen_paragraphs: dict[str, int] = {}
    for gi, (chapter_title, group) in enumerate(groups, 1):
        blocks = []
        for p in group:
            local = chosen.index(p) + 1
            orig = int(rows[local - 1].get("source_page") or p)
            text = _clean_text(str(rows[local - 1].get("text") or ""))
            unit = build_page_unit(p, text)
            ref = {"material": artifact_id, "page_start": local, "page_end": local, "source_page": orig}
            # 扫描/公式/几乎没有文字的页一律保留原页影像：
            # 占位文字（如“原页影像版”）不是正文，不能当成文字页糊过去。
            # OCR 补出来的文字默认也只进检索/提取，讲义仍用原页影像（宁可清楚，不要糊）。
            as_image = page_should_be_image(
                text, unit.kind, ocr_used=bool(rows[local - 1].get("ocr_used")),
                scan_mode=scan_mode, text_from_ocr=text_from_ocr)
            if as_image:
                img = out / "source_assets" / f"p{local}.png"
                pix = render[local - 1].get_pixmap(dpi=max(60, min(200, int(dpi))))
                pix.save(str(img))
                bid = f"g{gi}p{p}img"
                blocks.append({"id": f"g{gi}p{p}note", "kind": "paragraph",
                               "text": f"第 {orig} 页公式/扫描内容见下方原页影像，公式与排版以原书为准。",
                               "source_refs": [ref], "figure": None, "doc_page": local})
                blocks.append({"id": bid, "kind": "figure", "text": f"第 {orig} 页原页影像",
                               "source_refs": [ref], "figure": {
                                   "image_id": f"p{local}", "caption": f"第 {orig} 页原页影像",
                                   "source": ref, "after_block_id": bid, "asset_path": str(img),
                                   "origin": "source", "source_note": "公式/扫描页保留原页"}, "doc_page": local})
            else:
                if not text:
                    text = f"第 {orig} 页为图/表页，内容以原资料为准。"
                norm = re.sub(r"\s+", "", text)
                first_orig = duplicate_page_of(text, seen_pages)
                if first_orig is not None and first_orig != orig:
                    # 不丢页、不伪造：出处仍记本页，只是不重复展开同样的文字。
                    deduped_pages.append({"page": orig, "same_as": first_orig})
                    blocks.append({"id": f"g{gi}p{p}dup", "kind": "paragraph",
                                   "text": f"第 {orig} 页与第 {first_orig} 页内容相同，讲义只保留一处正文；按出处可回看该页。",
                                   "source_refs": [ref], "figure": None, "doc_page": local})
                else:
                    first_para = duplicate_paragraph_of(text, seen_paragraphs)
                    if first_para is not None and first_para != gi:
                        blocks.append({"id": f"g{gi}p{p}dup-para", "kind": "paragraph",
                                       "text": f"这一段与第 {first_para} 节内容重复，讲义只保留一处；按出处可回看原页。",
                                       "source_refs": [ref], "figure": None, "doc_page": local})
                        continue
                    register_paragraph(text, seen_paragraphs, gi)
                    if first_orig is None:
                        register_page_text(text, seen_pages, orig)
                    blocks.append({"id": f"g{gi}p{p}", "kind": "paragraph", "text": text[:3500],
                                   "source_refs": [ref], "figure": None, "doc_page": local})
                    # 公式页：把 OCR/MinerU 的 LaTeX 作为可搜索公式块补进来（过不了 KaTeX 的会跳过）
                    if text_from_ocr or not rows[local - 1].get("ocr_used"):
                        page_formulas = formula_map.get(int(rows[local - 1].get("page") or local), [])
                        if page_formulas:
                            blocks.append({"id": f"g{gi}p{p}formula-note", "kind": "paragraph",
                                           "text": "本页公式由 OCR 识别，可能与原页有出入；需要精确写法时请看原页影像。",
                                           "source_refs": [ref], "figure": None, "doc_page": local})
                        for fb in formula_mod.formula_blocks_for_page(
                                local_page=local, orig_page=orig,
                                formulas=formula_map.get(int(rows[local - 1].get("page") or local), []),
                                material=str(rows[local - 1].get("material") or ""),
                                limit=4):
                            fb["id"] = f"{fb['id']}-g{gi}p{p}"
                            blocks.append(fb)
            note = str(notes.get(str(p)) or "").strip()
            if note:
                blocks.append({"id": f"g{gi}p{p}n", "kind": "paragraph", "text": note,
                               "source_refs": [ref],
                               "figure": None, "doc_page": local})
        first_local = chosen.index(group[0]) + 1
        last_local = chosen.index(group[-1]) + 1
        title_pages = (int(rows[first_local - 1].get("source_page") or group[0]),
                       int(rows[last_local - 1].get("source_page") or group[-1]))
        sections.append({"id": f"src-ch-{gi}",
                         "title": chapter_title, "level": 2,
                         "blocks": blocks,
                         "source_refs": [{"material": artifact_id, "page_start": first_local,
                                          "page_end": last_local,
                                          "source_page": int(rows[first_local - 1].get("source_page") or group[0])}],
                         "summary": "本段按原文页组织。",
                         "objectives": ["读懂本段原文"], "key_terms": ["原文要点"],
                         "self_test": ["合上讲义复述本段"], "visual_hint": "none"})
    (out / "sections.json").write_text(json.dumps(sections, ensure_ascii=False, indent=2), encoding="utf-8")
    pr = _project_base(src, all_rows, artifact_id)
    pr.update({"id": output_id, "chapter_title": f"资料精读 第{chosen[0]}–{chosen[-1]}页",
               "page_count": len(chosen), "scope_pages": list(range(1, len(chosen) + 1)),
               "source_file": "source/scoped.pdf", "sections_files": ["sections.json"],
               "overview_mode": len(chosen) > 150, "coverage_percent": 90.0 if len(chosen) > 150 else 100.0})
    material = material_label(src, artifact_id, rows)
    if isinstance(raw, dict) and str(raw.get("origin_material") or "").strip():
        material = Path(str(raw["origin_material"])).stem
    course = material
    # 本 artifact 的每一页对应的原始页码；缺了它下游就只能拿裁切后的页码冒充出处。
    pr["page_map"] = [int(x.get("source_page") or x.get("page") or 0) for x in rows]
    if deduped_pages:
        pr["deduped_pages"] = deduped_pages[:500]
        pr["dedupe_note"] = f"{len(deduped_pages)} 页与前面的页正文相同，只保留一处展开，出处仍记本页。"
    pr["origin_material"] = material
    pr["chapter_title"] = f"{course} 第{chosen[0]}–{chosen[-1]}页"
    pr["header"] = {**pr.get("header", {}), "title": f"{course} 第{chosen[0]}–{chosen[-1]}页",
                    "course": course, "section_label": f"第{chosen[0]}–{chosen[-1]}页",
                    "coverage_scope": f"{len(chosen)}页"}
    pr["summary"] = {"overview": f"本讲义按原文覆盖资料第{chosen[0]}–{chosen[-1]}页，共 {len(chosen)} 页；每页保留原文和页码，便于核对。",
                     "knowledge_map": [s["title"] for s in sections]}
    pr["closing"] = {"persona": "老师", "text": "先把每页原文读一遍，再按目录把相邻页串成知识链；遇到公式先核对条件，遇到图表先看坐标和标注。合上讲义后按目录复述，再独立做例题。"}
    (out / "project.json").write_text(json.dumps(pr, ensure_ascii=False, indent=2), encoding="utf-8")
    if progress:
        progress(40, "排版 / 生成 PDF")
    build_project(out / "project.json", pdf=True)
    if progress:
        progress(95, "构建完成")
    return out / "lecture.pdf"

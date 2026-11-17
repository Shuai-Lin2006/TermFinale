"""实验性讲义生成：资料 -> 页账本 -> 按页分段成文 -> Gate -> PDF。

这不是“教材大纲 + 逐章精写”的最终形态；它只做一件可验证的事：
每一段都绑定资料页，生成后必须过 Gate 才进讲义库，没过就报错，
不把失败包装成“生成完成”。生成物没有语义审计，所以在 UI 里最多是
“待复核”，不会被标成“可读”。
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Callable

from core.platform_utils import find_soffice
from tfv2.authoring.lecture import AuthoringError, author_section, author_section_meta, author_section_titles, author_wrapup, fallback_wrapup, normalize_lecture_sections, _fallback_unique_title
from tfv2.build import build_project
from tfv2.curriculum.outline import OutlineError, build_outline
from tfv2.curriculum.teaching_plan import plan_with_llm
from tfv2.domain.page import PageImage, PageQuality
from tfv2.domain.lecture import (
    BlockKind,
    FigureRef,
    LanguagePolicy,
    LectureBlock,
    LectureClosing,
    LectureFooter,
    LectureHeader,
    LectureSummary,
    SourceRef,
)
from tfv2.ingest.pdf import build_pdf_page_ledger
from tfv2.ingest.structure import build_source_structure
from tfv2.ingest.pptx import build_pptx_page_ledger
from tfv2.llm.client import DeepSeekClient, LLMError
from tfv2.product import exclusions, service, source_pages
from tfv2.product.requirements import interpret_requirements, requirement_focus, requirement_prompt

ROOT = Path(__file__).resolve().parents[2]
from tfv2.product.data_paths import ARTIFACT_ROOT, UPLOAD_ROOT
_EXAM_STRONG = ("试卷", "答题", "题号", "得分", "满分")
_EXAM_WEAK = ("期中", "期末", "考试", "姓名", "学号")


def looks_like_exam(text: str) -> bool:
    """判断是不是试卷/答题纸：按结构判断，避免教材里提到“期中/姓名”就被误杀。

    真试卷同时有“题号/得分/答题/满分”这类版式词，且常有“考试时间…分钟”。
    """
    body = str(text or "")
    strong = sum(1 for w in _EXAM_STRONG if w in body)
    if len(body.strip()) < 80:
        # 短文本（封面/幻灯片）只有强特征足够多才算试卷
        return strong >= 3
    weak = sum(1 for w in _EXAM_WEAK if w in body)
    timed = bool(re.search(r"考试\s*(?:时间|方式|科目).{0,24}(?:分钟|闭卷|开卷)", body))
    return strong >= 2 or (strong >= 1 and weak >= 2) or (timed and strong >= 1)
_PROGRESS = Callable[[int, str], None]


class GenerateError(RuntimeError):
    pass


def _fail(out: Path, message: str) -> None:
    # A checkpointed lecture must survive failure so it can be resumed.
    if not (out / "lecture_checkpoint.json").is_file():
        shutil.rmtree(out, ignore_errors=True)
    raise GenerateError(message)


def _deliver_draft(out: Path, aid: str, *, title: str, page_count: int, sections, error: str):
    """Keep a best-effort lecture instead of deleting the whole artifact."""
    try:
        from tfv2.build import write_pdf
        from tfv2.render.lecture_html import write_lecture_html
        html = out / "lecture.html"
        if not html.is_file():
            spec = _project_spec_if_possible(out)
            if spec is None:
                return None
            write_lecture_html(spec, html)
        html_pdf = out / "lecture_html.pdf"
        final_pdf = out / "lecture.pdf"
        if not final_pdf.is_file():
            if html_pdf.is_file():
                shutil.copyfile(html_pdf, final_pdf)
            else:
                try:
                    spec = _project_spec_if_possible(out)
                    if spec is not None:
                        write_pdf(html, html_pdf, spec)
                        shutil.copyfile(html_pdf, final_pdf)
                except Exception:
                    pass
        manifest_path = out / "manifest.json"
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            manifest = {}
        manifest.update({
            "artifact": aid, "chapter": title, "page_count": page_count,
            "pdf_pages": _draft_page_count(out / "lecture.pdf"),
            "sections": len(sections or []),
            "figures": sum(1 for sec in (sections or []) for b in sec.blocks if b.figure is not None),
            "gate": {"passed": False, "issues": [{"code": "draft", "message": error}]},
            "draft": True, "delivery_warning": error,
        })
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        view = service.get_artifact(aid)
        if view is None:
            return None
        return {"id": aid, "artifact": view, "pages": page_count, "sections": len(sections or []),
                "coverage_percent": 0, "draft": True, "quality_warnings": [error]}
    except Exception:
        return None


def _project_spec_if_possible(out: Path):
    try:
        from tfv2.authoring.assemble import build_lecture_spec
        from tfv2.build import load_project
        from tfv2.domain.lecture import LectureSection
        project = load_project(out / "project.json")
        sections = []
        for name in project.sections_files:
            raw = json.loads((out / name).read_text(encoding="utf-8"))
            sections.extend(LectureSection.model_validate(x) for x in raw)
        return build_lecture_spec(
            chapter_title=project.chapter_title, header=project.header,
            summary=project.summary, sections=sections, closing=project.closing,
            footer=project.footer, page_count=project.page_count,
            coverage_percent=project.coverage_percent, scope_pages=project.scope_pages,
            language_policy=project.language_policy,
        )
    except Exception:
        return None


def _draft_page_count(path: Path) -> int:
    try:
        import pymupdf
        d = pymupdf.open(path)
        try:
            return len(d)
        finally:
            d.close()
    except Exception:
        return 0


def _new_id() -> str:
    return "gen_" + datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]




_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


def _image_to_pdf(source: Path, out_dir: Path) -> Path:
    """图片输入：OCR 文字写进不可见文本层，保留原图；生成 PDF 以复用页账本/Gate。"""
    from core.parser import _ocr_image_file
    import pymupdf
    from PIL import Image

    text = _ocr_image_file(str(source))
    if not (text or "").strip():
        raise GenerateError("图片 OCR 没有识别出文字；请换清晰截图或先转 PDF")
    with Image.open(source) as im:
        w, h = im.size
    # A4 纵向，图片按比例缩放
    page_w, page_h = 595, 842
    scale = min((page_w - 48) / max(1, w), (page_h - 48) / max(1, h))
    rect = pymupdf.Rect(24, 24, 24 + w * scale, 24 + h * scale)
    doc = pymupdf.open()
    page = doc.new_page(width=page_w, height=page_h)
    page.insert_image(rect, filename=str(source))
    # 不可见文本层：供页账本/语言检查/检索使用，不遮挡原图
    try:
        page.insert_text((24, 30), text[:6000], fontsize=4, fontname="china-s", render_mode=3)
    except Exception:
        try:
            page.insert_text((24, 30), text[:6000], fontsize=4, render_mode=3)
        except Exception:
            pass
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf = out_dir / f"{source.stem}_ocr.pdf"
    doc.save(str(pdf))
    doc.close()
    return pdf

def _convert_docx(source: Path, out_dir: Path) -> Path:
    exe = find_soffice()
    if not exe:
        raise GenerateError("PPT/PPTX/DOCX 需要本机安装 LibreOffice（soffice）才能转 PDF")
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            [exe, "--headless", "--convert-to", "pdf", "--outdir", str(out_dir), str(source)],
            check=False, capture_output=True, text=True, timeout=180,
        )
    except Exception as exc:
        raise GenerateError(f"DOCX 转 PDF 失败：{exc}") from exc
    pdf = out_dir / f"{source.stem}.pdf"
    if not pdf.is_file():
        raise GenerateError("Office 转 PDF 失败：没有生成 PDF")
    return pdf


def _ledger(source: Path, image_dir: Path):
    if source.suffix.lower() == ".pdf":
        return build_pdf_page_ledger(source, material_name=source.name, image_dir=image_dir)
    if source.suffix.lower() == ".pptx":
        return build_pptx_page_ledger(source, material_name=source.name, image_dir=image_dir)
    raise GenerateError("目前实验管线只支持 PDF / PPTX；DOCX/图片/扫描件还要走后继管线")


def _section_pages(default: int = 4) -> int:
    try:
        return max(2, min(8, int(os.getenv("TERMFINALE_SECTION_PAGES", str(default)))))
    except Exception:
        return default


def _chunks(page_count: int, size: int = 5) -> list[list[int]]:
    size = _section_pages(size)
    return [list(range(i, min(i + size, page_count + 1))) for i in range(1, page_count + 1, size)]


def _plan(ledger) -> tuple[list[tuple[str, list[int]]], bool]:
    """优先用资料真实大纲；大纲不可用才按页切。每段最多 4 页。"""
    try:
        outline = build_outline(ledger)
    except OutlineError:
        outline = None
    plan: list[tuple[str, list[int]]] = []
    if outline is not None:
        for sec in outline.sections:
            for sub in sec.subsections:
                pages = list(sub.pages)
                size = _section_pages(4)
                for i in range(0, len(pages), size):
                    group = pages[i:i + size]
                    label = f"{sub.title}（第 {group[0]}–{group[-1]} 页）"
                    plan.append((label, group))
        if plan:
            return plan, True
    return [(f"核心内容（第 {p[0]}–{p[-1]} 页）", p) for p in _chunks(ledger.page_count)], False


def _excluded_terms(requirements: dict, excluded: str) -> list[str]:
    terms: list[str] = []
    for item in (requirements or {}).get("must_not") or []:
        label = str(item.get("label") or "").strip()
        if label:
            terms.append(label)
    for part in re.split(r"[\n,，;；、]+", excluded or ""):
        part = part.strip()
        if len(part) >= 2:
            terms.append(part)
    generic = {"不考", "不用", "不需要", "跳过", "删除", "无"}
    return list(dict.fromkeys(t for t in terms if t and t not in generic))


def _filter_plan(plan, page_text_by_no: dict[int, str], terms: list[str]):
    """Remove sections covered by the user's “not tested” instruction.

    Matching the label alone is not enough: an outline may name a chapter
    "第三章" while the excluded term is a topic inside it. We also look at the
    source page text, then exclude the whole section's pages.
    """
    if not terms:
        return plan, set()
    kept = []
    excluded_pages: set[int] = set()
    for label, pages in plan:
        text = (str(label) + "\n" + "\n".join(page_text_by_no.get(p, "") for p in pages)).lower()
        hit = any(term.lower() in text for term in terms)
        if hit:
            excluded_pages.update(pages)
            continue
        kept.append((label, pages))
    return kept, excluded_pages


def _cited_pages(section) -> set[int]:
    out: set[int] = set()
    for block in section.blocks:
        for ref in block.source_refs:
            out.update(range(ref.page_start, (ref.page_end or ref.page_start) + 1))
    return out




def _usable_image(path: str | None) -> bool:
    if not path:
        return False
    p = Path(path)
    if not p.is_file() or p.stat().st_size < 6000:
        return False
    try:
        from PIL import Image
        with Image.open(p) as im:
            w, h = im.size
    except Exception:
        return False
    if w < 160 or h < 110:
        return False
    if not (0.25 <= (w / max(1, h)) <= 4.0):
        return False
    return True


def _image_hash(path: str) -> str:
    import hashlib
    try:
        return hashlib.md5(Path(path).read_bytes()).hexdigest()
    except Exception:
        return ""


_VISION_CACHE: dict[str, str] | None = None
_VISION_DEADLINE = 0.0


def _vision_cache_path() -> Path:
    return ARTIFACT_ROOT.parent / "vision_cache.json"


def _load_vision_cache() -> dict[str, str]:
    global _VISION_CACHE
    if _VISION_CACHE is None:
        try:
            _VISION_CACHE = json.loads(_vision_cache_path().read_text(encoding="utf-8"))
        except Exception:
            _VISION_CACHE = {}
    return _VISION_CACHE


def _call_with_timeout(fn, timeout: float, *args, **kwargs):
    """Run a blocking vision call without letting a slow provider freeze the
    entire lecture. The worker is daemonized; on timeout we return None and
    continue with the deterministic fallback / no figure.
    """
    box: dict = {}

    def runner():
        try:
            box["value"] = fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001
            box["error"] = exc

    t = threading.Thread(target=runner, daemon=True)
    t.start()
    t.join(max(1.0, float(timeout)))
    if t.is_alive():
        return None
    if "error" in box:
        raise box["error"]
    return box.get("value")


def _stage(out: Path, name: str) -> None:
    import json as _json
    try:
        out.mkdir(parents=True, exist_ok=True)
        rec = {"stage": name, "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
        with (out / "stage_log.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(_json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"[stage] {name}", flush=True)
    except Exception:
        pass


def _vision_caption(path: str) -> str:
    import os
    if os.getenv("TERMFINALE_SKIP_FIGURE_VISION") == "1":
        return ""
    if _VISION_DEADLINE and time.monotonic() > _VISION_DEADLINE:
        return ""
    h = _image_hash(path)
    # Version the cache key: older generic caption prompts returned decorative
    # blobs as captions. Do not reuse those results for teaching figures.
    key = f"teaching-v1:{h}" if h else ""
    cache = _load_vision_cache()
    if key and key in cache:
        return cache[key]
    try:
        from core.ai_vision import analyze_teaching_figure
        cap = (_call_with_timeout(analyze_teaching_figure, 15, path) or "").strip()
    except Exception:
        return ""
    cap = cap.replace("图注：", "").strip()
    if not cap or cap == "无" or len(cap) < 4:
        return ""
    cap = cap[:80]
    if key:
        cache[key] = cap
        try:
            _vision_cache_path().write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
    return cap






def _ocr_low_text(ledger, source: Path) -> None:
    """扫描 PDF：文本层为空/过短的页走 OCR 回填，避免整页被当成无字页。"""
    if source.suffix.lower() != ".pdf":
        return
    low = [p for p in ledger.pages if len((p.text or "").strip()) < 20]
    if not low:
        return
    # 先用本地 MinerU（离线、有缓存），比逐页调云端 OCR 稳且不花 token。
    local_text: dict[int, str] = {}
    try:
        from tfv2.ingest.mineru_backend import ocr_pdf_pages
        local_text, _engine = ocr_pdf_pages(source)
    except Exception:
        local_text = {}
    cloud_fails = 0
    try:
        import pymupdf
        from core.parser import _ocr_page
        doc = pymupdf.open(str(source))
    except Exception:
        doc = None
    try:
        for page in low:
            text = str(local_text.get(page.page_no) or "").strip()
            if not text and doc is not None and cloud_fails < 2:
                try:
                    text = _ocr_page(doc[page.page_no - 1]) or ""
                except Exception:
                    cloud_fails += 1
                    continue
            if text.strip():
                page.text = text.strip()
                page.quality = PageQuality.OCR
                page.ocr_used = True
    finally:
        if doc is not None:
            doc.close()

def _pptx_diagram_pages(source: Path) -> set[int]:
    """Domain-neutral diagram hint: slides with several vector shapes/charts, not text-only decks."""
    try:
        from pptx import Presentation
        from pptx.enum.shapes import MSO_SHAPE_TYPE
        prs = Presentation(str(source))
    except Exception:
        return set()
    out: set[int] = set()

    def score(shapes) -> int:
        n = 0
        for shape in shapes:
            try:
                if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
                    n += score(shape.shapes)
                    continue
                if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                    continue
                if getattr(shape, "has_chart", False):
                    n += 3
                elif getattr(shape, "has_table", False):
                    n += 2
                elif str(shape.shape_type).startswith("EMBEDDED_OLE_OBJECT"):
                    n += 2
                elif shape.shape_type in (MSO_SHAPE_TYPE.AUTO_SHAPE, MSO_SHAPE_TYPE.FREEFORM,
                                          MSO_SHAPE_TYPE.LINE):
                    n += 1
            except Exception:
                continue
        return n

    for idx, slide in enumerate(prs.slides, start=1):
        try:
            if score(slide.shapes) >= 8:
                out.add(idx)
        except Exception:
            continue
    return out



def _contact_sheet(paths: list[str], out_path: Path) -> Path:
    from PIL import Image, ImageDraw, ImageFont
    cols = 3
    rows = max(1, (len(paths) + cols - 1) // cols)
    tw, th = 400, 300
    im = Image.new("RGB", (tw * cols, th * rows), "white")
    d = ImageDraw.Draw(im)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 24)
    except Exception:
        font = ImageFont.load_default()
    for i, path in enumerate(paths):
        x, y = (i % cols) * tw, (i // cols) * th
        try:
            pic = Image.open(path).convert("RGB")
            pic.thumbnail((tw - 16, th - 42), Image.LANCZOS)
            im.paste(pic, (x + 8, y + 34))
        except Exception:
            pass
        d.rectangle((x + 2, y + 2, x + tw - 2, y + th - 2), outline="#888", width=2)
        d.text((x + 10, y + 6), str(i + 1), font=font, fill="#b00020")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    im.save(out_path)
    return out_path


def _classify_slide_batch(paths: list[str]) -> dict[str, str]:
    """One domain-neutral vision call for a 3x3 contact sheet."""
    import base64
    import tempfile
    from core.ai_vision import client
    from core.config import vision_model
    from PIL import Image
    with tempfile.TemporaryDirectory() as td:
        sheet = _contact_sheet(paths, Path(td) / "sheet.png")
        b64 = base64.b64encode(sheet.read_bytes()).decode()
        prompt = (
            "这是一张3x3的PPT页面缩略图，编号1-9。判断每一张是否是值得放进大学讲义的"
            "只保留真正的教学图示：图形、流程、结构、地图、图表、实验装置、电路/解剖/几何等视觉表达，"
            "而且图示必须占据页面主体、标签文字清晰可读。"
            "以下一律 ok=false：封面、目录、章节分隔页、纯文字页、纯公式页、填空题、占位页、空白模板页；"
            "含大量方框/乱码/缺字占位符的页面；图示只占页面一小块、主体仍是文字或装饰的页面。"
            "caption 只描述图中真实可见的内容，不推测、不编造。若是，caption 不超过30字；若否，caption空。"
            '只输出JSON：{"items":[{"n":1,"ok":true,"caption":"..."}]}'
        )
        resp = client.chat.completions.create(
            model=vision_model(),
            messages=[{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                {"type": "text", "text": prompt},
            ]}],
            temperature=0.1,
        )
        raw = resp.choices[0].message.content or ""
    m = re.search(r"\{.*\}", raw, flags=re.S)
    try:
        data = json.loads(m.group(0) if m else raw)
    except Exception:
        data = {}
    by_n = {}
    for item in data.get("items") or []:
        try:
            n = int(item.get("n"))
            if item.get("ok") and str(item.get("caption") or "").strip():
                by_n[n] = str(item["caption"]).strip()[:40]
        except Exception:
            continue
    return {path: by_n.get(i + 1, "") for i, path in enumerate(paths)}


def _clamp_page_refs(sections, page_count: int) -> None:
    """A scoped generation must never cite a page outside the sliced PDF."""
    for sec in sections:
        refs = []
        for ref in sec.source_refs or []:
            start = min(max(1, int(ref.page_start)), page_count)
            end = min(max(start, int(ref.page_end or start)), page_count)
            ref.page_start, ref.page_end = start, end
            refs.append(ref)
        sec.source_refs = refs
        for block in sec.blocks:
            refs = []
            for ref in block.source_refs or []:
                start = min(max(1, int(ref.page_start)), page_count)
                end = min(max(start, int(ref.page_end or start)), page_count)
                ref.page_start, ref.page_end = start, end
                refs.append(ref)
            block.source_refs = refs


def _fallback_section_meta(sections, gen_lang: str = "zh") -> None:
    """Long books often skip the meta author call; never ship sections without goals."""
    en = gen_lang == "en"
    for sec in sections:
        title = (sec.title or "").strip()
        if not sec.objectives:
            sec.objectives = (
                [f"Understand the core idea of {title}", f"Use {title} to solve one exercise"]
                if en else [f"理解「{title}」的核心概念", f"能用「{title}」完成一道基础练习"]
            )
        if not sec.key_terms:
            terms = [x.strip() for x in re.split(r"[与和及、,，/]", title) if len(x.strip()) >= 2]
            sec.key_terms = (terms[:3] or [title]) if not en else (terms[:3] or [title])
        if not sec.self_test:
            sec.self_test = (
                [f"What is the key conclusion of {title}?", "Can you solve one example without notes?"]
                if en else [f"「{title}」最重要的结论是什么？", "能否不看讲义独立完成一道例题？"]
            )


def _attach_evidence_quotes(sections, page_by_no) -> None:
    """Attach a short source quote to block references when possible."""
    import re as _re
    for sec in sections:
        for block in sec.blocks:
            if block.kind == BlockKind.FIGURE:
                continue
            for ref in block.source_refs or []:
                if ref.quote:
                    continue
                raw = (page_by_no.get(ref.page_start).text or "") if page_by_no.get(ref.page_start) else ""
                raw = _re.sub(r"\s+", " ", raw).strip()
                if not raw:
                    continue
                def _meaningful(x: str) -> bool:
                    return len(_re.findall(r"[\u4e00-\u9fffA-Za-z0-9]", x or "")) >= 8
                sentences = [x.strip() for x in _re.split(r"(?<=[。！？.!?])", raw) if _meaningful(x)]
                if not sentences:
                    continue
                target = block.text or ""
                toks = set(_re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z]{2,}", target))
                scored = []
                for sentence in sentences:
                    overlap = len(toks & set(_re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z]{2,}", sentence)))
                    if overlap > 0:
                        scored.append((overlap, len(sentence), sentence))
                if not scored:
                    continue
                scored.sort(key=lambda x: (x[0], -x[1]), reverse=True)
                best = scored[0][2]
                if _meaningful(best) and len(best) >= 12:
                    ref.quote = best[:160]


def _apply_docling_text(ledger, structure: dict) -> None:
    """Use Docling's block order/bbox text as the page ledger when available."""
    if not structure or structure.get("provider") != "docling":
        return
    by_page = {int(x.get("page") or 0): x for x in (structure.get("pages") or [])}
    for page in ledger.pages:
        item = by_page.get(page.page_no) or {}
        blocks = [b for b in (item.get("blocks") or []) if str(b.get("text") or "").strip()]
        def key(b):
            bb = b.get("bbox") or [0, 0, 0, 0]
            return (round(float(bb[1]), 1), round(float(bb[0]), 1))
        text = "\n".join(str(b.get("text") or "").strip() for b in sorted(blocks, key=key))
        tables = [t for t in (item.get("tables") or []) if str(t.get("text") or "").strip()]
        if tables:
            from tfv2.render import table_structure
            def tkey(t):
                bb = t.get("bbox") or [0, 0, 0, 0]
                return (round(float(bb[1]), 1), round(float(bb[0]), 1))
            pieces = []
            for t in sorted(tables, key=tkey):
                raw = str(t.get("text") or "").strip()
                q = table_structure.table_quality(raw)
                pieces.append(table_structure.normalize_table(raw) if q.get("ok") else raw)
            table_text = "\n".join(pieces)
            text = (text + "\n[表格]\n" + table_text) if text.strip() else ("[表格]\n" + table_text)
        if text.strip():
            page.text = text
            page.quality = PageQuality.TEXT


def _add_structure_vector_figures(ledger, structure: dict) -> None:
    """Attach one clustered vector diagram per page only when the page has no
    usable bitmap content image. The normal screenshot/VLM filters still apply.
    """
    by_page = {int(x.get("page") or 0): x for x in (structure.get("pages") or [])}
    added = 0
    for page in ledger.pages:
        item = by_page.get(page.page_no) or {}
        pw = float(item.get("width") or 0); ph = float(item.get("height") or 0)
        # Ignore full-page slide background images and tiny logos when deciding
        # whether this page already has a real bitmap content figure.
        has_content_picture = False
        if pw > 0 and ph > 0:
            for pic in item.get("pictures") or []:
                bb = pic.get("bbox") or []
                if len(bb) != 4:
                    continue
                ratio = max(0.0, (bb[2] - bb[0]) * (bb[3] - bb[1]) / (pw * ph))
                if 0.02 <= ratio <= 0.55:
                    has_content_picture = True
                    break
        if has_content_picture:
            continue
        if added >= 6:
            break
        regions = item.get("vector_regions") or []
        for region in regions[:1]:
            path = region.get("asset_path")
            if not path or not Path(str(path)).is_file():
                continue
            page.images.append(PageImage(
                image_id=f"vector_{page.page_no}",
                kind="screenshot",
                asset_path=str(path),
                discarded_reason=None,
            ))
            added += 1
            break


def _add_docling_picture_figures(ledger, structure: dict, pdf_path: Path, image_dir: Path) -> None:
    """Crop Docling-detected picture bboxes into real source figures."""
    if not structure or structure.get("provider") != "docling":
        return
    import pymupdf
    try:
        doc = pymupdf.open(pdf_path)
    except Exception:
        return
    added = 0
    try:
        by_page = {int(x.get("page") or 0): x for x in structure.get("pages") or []}
        for page in ledger.pages:
            if added >= 12:
                break
            item = by_page.get(page.page_no) or {}
            w = float(item.get("width") or 0); h = float(item.get("height") or 0)
            if page.page_no > len(doc) or w <= 0 or h <= 0:
                continue
            pics = [p for p in (item.get("pictures") or []) if len(p.get("bbox") or []) == 4]
            for i, pic in enumerate(pics[:4]):
                x0, y0, x1, y1 = [float(x) for x in pic["bbox"]]
                area = max(0.0, (x1 - x0) * (y1 - y0) / (w * h))
                if not (0.015 <= area <= 0.55):
                    continue
                clip = pymupdf.Rect(max(0, x0), max(0, y0), min(w, x1), min(h, y1))
                if clip.width < 30 or clip.height < 20:
                    continue
                target = image_dir / f"docling_p{page.page_no}_{i}.png"
                try:
                    pix = doc[page.page_no - 1].get_pixmap(clip=clip, dpi=150, alpha=False)
                    pix.save(target)
                except Exception:
                    continue
                page.images.append(PageImage(
                    image_id=f"docling_{page.page_no}_{i}", kind="content",
                    asset_path=str(target), discarded_reason=None,
                    bbox=[round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)],
                ))
                added += 1
    finally:
        doc.close()


def _preclassify_slide_figures(ledger) -> None:
    """Cache a domain-neutral vision decision for every rendered page/screenshot."""
    if _VISION_DEADLINE and time.monotonic() > _VISION_DEADLINE:
        return
    paths = []
    for page in ledger.pages:
        for img in page.images:
            if img.image_id.startswith("vector_"):
                continue  # lazy: classify only if the section actually needs it
            if img.kind == "screenshot" and img.asset_path and Path(img.asset_path).is_file():
                paths.append(str(img.asset_path))
    if not paths:
        return
    cache = _load_vision_cache()
    todo = []
    for p in paths:
        h = _image_hash(p)
        key = f"slide:{h}" if h else ""
        if key and key in cache:
            _SLIDE_CLASSIFY_CACHE[p] = cache[key]
        else:
            todo.append(p)
    from concurrent.futures import ThreadPoolExecutor
    batches = [todo[i:i + 9] for i in range(0, len(todo), 9)]
    def _run(batch):
        try:
            return _classify_slide_batch(batch)
        except Exception:
            return {}
    with ThreadPoolExecutor(max_workers=min(4, max(1, len(batches)))) as pool:
        decisions = list(pool.map(_run, batches))
    for decision in decisions:
        for p, caption in decision.items():
            _SLIDE_CLASSIFY_CACHE[p] = caption
            h = _image_hash(p)
            if h:
                cache[f"slide:{h}"] = caption
    try:
        _vision_cache_path().write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _slide_caption(path: str, section_title: str = "") -> str:
    if not path:
        return ""
    if path not in _SLIDE_CLASSIFY_CACHE:
        return ""
    cap = _SLIDE_CLASSIFY_CACHE.get(path, "").strip()
    return cap[:80]


def _add_pptx_slide_renders(ledger, source: Path, image_dir: Path) -> None:
    """PPTX diagrams are often vector shapes, not embedded pictures.
    Render slides without a usable content picture via LibreOffice, so circuit/vector
    diagrams can become real source figures instead of disappearing."""
    if source.suffix.lower() != ".pptx":
        return
    exe = find_soffice()
    if not exe:
        return
    try:
        import pymupdf
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            subprocess.run([exe, "--headless", "--convert-to", "pdf", "--outdir", str(td), str(source)],
                           check=False, capture_output=True, text=True, timeout=240)
            pdf = next(td.glob("*.pdf"), None)
            if pdf is None:
                return
            doc = pymupdf.open(str(pdf))
            diagram_pages = _pptx_diagram_pages(source)
            try:
                for page in ledger.pages:
                    if page.page_no not in diagram_pages:
                        continue
                    if any(_usable_image(img.asset_path) for img in page.images):
                        continue
                    try:
                        pix = doc[page.page_no - 1].get_pixmap(dpi=125)
                        path = image_dir / f"slide_scan_{page.page_no:03d}.png"
                        pix.save(str(path))
                        page.images.append(PageImage(
                            image_id=f"slide_scan_{page.page_no:03d}", kind="screenshot",
                            asset_path=str(path), discarded_reason=None,
                        ))
                    except Exception:
                        continue
            finally:
                doc.close()
    except Exception:
        return


def _doclayout_python() -> str:
    import shutil
    import subprocess
    candidates = [
        os.getenv("TERMFINALE_DOCLAYOUT_PYTHON", "").strip(),
        "/private/tmp/docling_venv/bin/python",
        str(Path.home() / "Library/Application Support/TermFinale/docling/venv/bin/python"),
    ]
    for candidate in candidates:
        if not candidate or not Path(candidate).is_file():
            continue
        try:
            probe = subprocess.run([candidate, "-c", "import doclayout_yolo"], capture_output=True, timeout=20)
            if probe.returncode == 0:
                return candidate
        except Exception:
            continue
    return ""


def _latex_ok(latex: str) -> bool:
    """Reject pix2tex hallucinations on dirty crops.

    Clean formula LaTeX contains a structural operator; hallucinated output on
    text lines is full of Big/stackrel/bigotimes/array scaffolding.
    """
    if not latex or len(latex) > 220:
        return False
    bad = ("\\Big", "\\stackrel", "\\bigotimes", "\\begin{array}",
           "\\underbrace", "\\otimes", "\\mathrm")
    if any(marker in latex for marker in bad):
        return False
    good = ("\\frac", "\\int", "\\sum", "\\sqrt", "\\lim", "^", "_", "=",
            "\\alpha", "\\beta", "\\gamma", "\\pi", "\\le", "\\ge", "\\neq",
            "\\to", "\\cdot", "\\times", "\\pm", "\\infty")
    return any(marker in latex for marker in good)


_MATH_LINE = re.compile(
    r"[\u222b\u221a\u2211\u220f\u2202\u2207\u03c0\u03b8\u03c6\u03bb\u03bc\u03c3\u03a9\u221e"
    r"\u00b1\u00d7\u00f7\u2248\u2260\u2264\u2265\u2192\u03f4]"
    r"|\b(arctan|arcsin|arccos|sinh?|cosh?|tanh?|log|ln|lim|dx|dy|dt|\frac)\b"
)


def _mfd_python() -> str:
    import subprocess
    candidates = [
        os.getenv("TERMFINALE_MFD_PYTHON", "").strip(),
        str(Path.home() / "Library/Application Support/TermFinale/docling/venv/bin/python"),
        "/private/tmp/docling_venv/bin/python",
    ]
    for candidate in candidates:
        if not candidate or not Path(candidate).is_file():
            continue
        try:
            probe = subprocess.run([candidate, "-c", "import ultralytics"], capture_output=True, timeout=20)
            if probe.returncode == 0:
                return candidate
        except Exception:
            continue
    return ""


def _formula_python() -> str:
    import subprocess
    candidates = [
        os.getenv("TERMFINALE_FORMULA_PYTHON", "").strip(),
        str(Path.home() / "Library/Application Support/TermFinale/docling/venv/bin/python"),
        "/private/tmp/docling_venv/bin/python",
    ]
    for candidate in candidates:
        if not candidate or not Path(candidate).is_file():
            continue
        try:
            probe = subprocess.run([candidate, "-c", "import pix2tex"], capture_output=True, timeout=20)
            if probe.returncode == 0:
                return candidate
        except Exception:
            continue
    return ""


def _formula_ocr_text_spans(ledger, source: Path, image_dir: Path) -> None:
    """Fallback when MinerU MFD is unavailable: crop PDF text spans that look
    like formulas, run pix2tex, and keep the crop if OCR is unreliable."""
    python = _formula_python()
    script = ROOT / "tools" / "formula_ocr.py"
    if not python or not script.is_file():
        return
    try:
        import pymupdf
        from PIL import Image
        doc = pymupdf.open(str(source))
    except Exception:
        return
    crops: list[tuple[int, str]] = []
    try:
        for page in ledger.pages:
            if not _MATH_LINE.search(page.text or ""):
                continue
            try:
                pdf_page = doc[page.page_no - 1]
                pix = pdf_page.get_pixmap(dpi=200)
                page_img = image_dir / f"formula_page_{page.page_no:03d}.png"
                pix.save(str(page_img))
                scale = 200 / 72
                with Image.open(page_img) as im:
                    width, height = im.size
                    idx = 0
                    for block in pdf_page.get_text("dict").get("blocks", []):
                        for line in block.get("lines", []):
                            spans = line.get("spans") or []
                            text = "".join(str(s.get("text") or "") for s in spans).strip()
                            if not text or not (_MATH_LINE.search(text) or ("=" in text and re.search(r"[\^_/]", text))):
                                continue
                            x0, y0, x1, y1 = line.get("bbox") or [0, 0, 0, 0]
                            box = (max(0, int(x0 * scale) - 8), max(0, int(y0 * scale) - 8),
                                   min(width, int(x1 * scale) + 8), min(height, int(y1 * scale) + 8))
                            if box[2] - box[0] < 40 or box[3] - box[1] < 18:
                                continue
                            idx += 1
                            out_img = image_dir / f"formula_{page.page_no:03d}_{idx}.png"
                            im.crop(box).save(out_img)
                            crops.append((page.page_no, str(out_img)))
            except Exception:
                continue
        if not crops:
            return
        proc = subprocess.run([python, str(script), *[f for _, f in crops]],
                              capture_output=True, text=True, timeout=300)
        if proc.returncode != 0:
            return
        items = json.loads(proc.stdout or "{}").get("items") or []
        for (page_no, fpath), ocr in zip(crops, items):
            page = next((pg for pg in ledger.pages if pg.page_no == page_no), None)
            if page is None:
                continue
            latex = str(ocr.get("latex") or "").replace("\textstyle", "").strip()
            if not _latex_ok(latex):
                try:
                    from core.ai_vision import read_formula_latex
                    latex = read_formula_latex(fpath).replace("\textstyle", "").strip()
                except Exception:
                    latex = ""
            if _latex_ok(latex):
                page.text = ((page.text or "").rstrip() + "\n[公式OCR] $" + latex + "$")
            else:
                page.images.append(PageImage(
                    image_id=f"formula_{page_no:03d}_{Path(fpath).stem.split('_')[-1]}", kind="content",
                    asset_path=fpath, caption=f"第 {page_no} 页公式（OCR 未通过，保留原图）",
                    bbox=[0, 0, 0, 0],
                ))
    finally:
        try:
            doc.close()
        except Exception:
            pass


def _add_formula_ocr(ledger, source: Path, image_dir: Path) -> None:
    """MinerU MFD detects formula regions; pix2tex converts them to LaTeX.

    The LaTeX is appended to the page text as "[公式OCR] $...$" so the section
    writer sees the real formula instead of scattered PDF glyph fragments.
    """
    if os.getenv("TFV2_FORMULA_OCR", "1") == "0":
        return
    if source.suffix.lower() != ".pdf":
        return
    detect_script = ROOT / "tools" / "formula_detect.py"
    ocr_script = ROOT / "tools" / "formula_ocr.py"
    python = _mfd_python() or _doclayout_python()
    if not python:
        _formula_ocr_text_spans(ledger, source, image_dir)
        return
    if not detect_script.is_file() or not ocr_script.is_file():
        _formula_ocr_text_spans(ledger, source, image_dir)
        return
    try:
        import pymupdf
        from PIL import Image
        doc = pymupdf.open(str(source))
    except Exception:
        return
    try:
        render_items: list[tuple[int, str]] = []
        for page in ledger.pages:
            try:
                pdf_page = doc[page.page_no - 1]
                text = page.text or ""
                if len(text) >= 60 and not _MATH_LINE.search(text):
                    continue
                pix = pdf_page.get_pixmap(dpi=150)
                path = image_dir / f"mfd_page_{page.page_no:03d}.png"
                pix.save(str(path))
                render_items.append((page.page_no, str(path)))
            except Exception:
                continue
        if not render_items:
            return
        if os.getenv("TFV2_FORMULA_MFD", "1") == "0":
            return
        proc = subprocess.run(
            [python, str(detect_script), *[f for _, f in render_items]],
            capture_output=True, text=True, timeout=240,
        )
        if proc.returncode != 0:
            return
        data = json.loads(proc.stdout or "{}")
        crops: list[tuple[int, str]] = []
        for item in data.get("images") or []:
            path = Path(str(item.get("path") or ""))
            try:
                page_no = int(path.stem.rsplit("_", 1)[-1])
            except Exception:
                continue
            try:
                with Image.open(path) as im:
                    width, height = im.size
            except Exception:
                continue
            idx = 0
            for box in item.get("boxes") or []:
                cls = str(box.get("cls") or "")
                conf = float(box.get("conf") or 0)
                min_conf = 0.40 if cls == "isolated" else 0.70
                if conf < min_conf:
                    continue
                try:
                    x0, y0, x1, y1 = [float(x) for x in box["xyxy"]]
                except Exception:
                    continue
                pad = 6
                crop_box = (max(0, int(x0) - pad), max(0, int(y0) - pad),
                            min(width, int(x1) + pad), min(height, int(y1) + pad))
                if crop_box[2] - crop_box[0] < 30 or crop_box[3] - crop_box[1] < 16:
                    continue
                idx += 1
                out_img = image_dir / f"formula_{page_no:03d}_{idx}.png"
                try:
                    with Image.open(path) as im:
                        im.crop(crop_box).save(out_img)
                    crops.append((page_no, str(out_img)))
                except Exception:
                    continue
        if not crops:
            return
        ocr_timeout = float(os.getenv("TERMFINALE_FORMULA_OCR_TIMEOUT", "60"))
        try:
            proc = subprocess.run(
                [python, str(ocr_script), *[f for _, f in crops]],
                capture_output=True, text=True, timeout=ocr_timeout,
            )
        except subprocess.TimeoutExpired:
            # Budget exceeded: keep formula crops as images instead of hanging.
            for idx, (page_no, fpath) in enumerate(crops, start=1):
                page = next((pg for pg in ledger.pages if pg.page_no == page_no), None)
                if page is not None:
                    page.images.append(PageImage(
                        image_id=f"formula_{page_no:03d}_{idx}", kind="content",
                        asset_path=fpath, caption=f"第 {page_no} 页公式（公式 OCR 超预算，保留原图）",
                        bbox=[0, 0, 0, 0]))
            return
        if proc.returncode != 0:
            return
        items = json.loads(proc.stdout or "{}").get("items") or []
        for idx, ((page_no, fpath), ocr) in enumerate(zip(crops, items), start=1):
            page = next((pg for pg in ledger.pages if pg.page_no == page_no), None)
            if page is None:
                continue
            latex = str(ocr.get("latex") or "").replace("\textstyle", "").strip()
            if _latex_ok(latex) and ("[公式OCR] $" + latex[:40] + "$") not in (page.text or ""):
                page.text = ((page.text or "").rstrip() + "\n[公式OCR] $" + latex + "$")
                continue
            # OCR failed: keep the original formula block as an image so the
            # rendered formula is never garbled. The figure placer treats
            # formula_* crops like layout crops.
            title = ""
            for line in (page.text or "").splitlines():
                line = line.strip()
                if len(line) >= 2 and not re.fullmatch(r"\d+", line):
                    title = line[:36]
                    break
            page.images.append(PageImage(
                image_id=f"formula_{page_no:03d}_{idx}", kind="content",
                asset_path=fpath, caption=(title or f"第 {page_no} 页公式") + f"（公式，资料第 {page_no} 页）",
                bbox=[0, 0, 0, 0],
            ))
    finally:
        try:
            doc.close()
        except Exception:
            pass


def _add_doclayout_figures(ledger, source: Path, image_dir: Path) -> None:
    """Use DocLayout-YOLO to crop real figures/tables from PDF pages.

    Runs in the optional docling venv (torch lives there), not in the app
    process. The crop is attached to the page ledger with a page-title caption;
    the normal figure pipeline then places it after the matching paragraph.
    """
    if os.getenv("TFV2_DOCLAYOUT", "1") == "0":
        return
    suffix = source.suffix.lower()
    if suffix not in (".pdf", ".pptx"):
        return
    python = _doclayout_python()
    script = ROOT / "tools" / "doclayout_detect.py"
    if not python or not script.is_file():
        return
    temp_dir = None
    try:
        import pymupdf
        from PIL import Image
        if suffix == ".pptx":
            exe = find_soffice()
            if not exe:
                return
            temp_dir = tempfile.TemporaryDirectory()
            subprocess.run([exe, "--headless", "--convert-to", "pdf", "--outdir", temp_dir.name, str(source)],
                           check=False, capture_output=True, text=True, timeout=240)
            pdf = next(Path(temp_dir.name).glob("*.pdf"), None)
            if pdf is None:
                return
            doc = pymupdf.open(str(pdf))
        else:
            doc = pymupdf.open(str(source))
    except Exception:
        return
    try:
        page_paths: list[Path] = []
        for page in ledger.pages:
            try:
                pix = doc[page.page_no - 1].get_pixmap(dpi=150)
                path = image_dir / f"layout_page_{page.page_no:03d}.png"
                pix.save(str(path))
                page_paths.append(path)
            except Exception:
                page_paths.append(Path())
        valid = [str(p) for p in page_paths if p and p.is_file()]
        if not valid:
            return
        proc = subprocess.run([python, str(script), *valid], capture_output=True, text=True, timeout=240)
        if proc.returncode != 0:
            return
        data = json.loads(proc.stdout or "{}")
    except Exception:
        return
    finally:
        try:
            doc.close()
        except Exception:
            pass
        if temp_dir is not None:
            try:
                temp_dir.cleanup()
            except Exception:
                pass
    caption_budget = 4
    for item in data.get("images") or []:
        path = Path(str(item.get("path") or ""))
        try:
            page_no = int(path.stem.rsplit("_", 1)[-1])
        except Exception:
            continue
        page = next((p for p in ledger.pages if p.page_no == page_no), None)
        if page is None:
            continue
        boxes = [b for b in item.get("boxes") or []
                 if b.get("cls") in ("figure", "table") and float(b.get("conf") or 0) >= 0.25]
        if not boxes:
            continue
        try:
            with Image.open(path) as im:
                width, height = im.size
        except Exception:
            continue
        title = ""
        for line in (page.text or "").splitlines():
            line = line.strip()
            if len(line) >= 2 and not re.fullmatch(r"\d+", line):
                title = line[:36]
                break
        for idx, box in enumerate(boxes[:3], start=1):
            try:
                x0, y0, x1, y1 = [float(x) for x in box["xyxy"]]
            except Exception:
                continue
            # Skip tiny boxes and near-full-page boxes that are just slide frames.
            area = max(0.0, x1 - x0) * max(0.0, y1 - y0)
            if area < 0.04 * width * height or area > 0.96 * width * height:
                continue
            pad = 8
            crop_box = (max(0, int(x0) - pad), max(0, int(y0) - pad),
                        min(width, int(x1) + pad), min(height, int(y1) + pad))
            if crop_box[2] - crop_box[0] < 80 or crop_box[3] - crop_box[1] < 80:
                continue
            out_img = image_dir / f"layout_{page_no:03d}_{idx}.png"
            try:
                with Image.open(path) as im:
                    im.crop(crop_box).save(out_img)
            except Exception:
                continue
            vlm_caption = ""
            if caption_budget > 0 and os.getenv("TFV2_FIGURE_CAPTION", "1") != "0":
                global _VISION_DEADLINE
                old_deadline = _VISION_DEADLINE
                try:
                    _VISION_DEADLINE = time.monotonic() + 50
                    vlm_caption = _vision_caption(str(out_img))
                finally:
                    _VISION_DEADLINE = old_deadline
                caption_budget -= 1
            caption = (vlm_caption or title or f"第 {page_no} 页图示") + f"（资料第 {page_no} 页）"
            page.images.append(PageImage(
                image_id=f"layout_{page_no:03d}_{idx}", kind="content",
                asset_path=str(out_img), caption=caption,
                bbox=[float(x) for x in crop_box],
            ))
        formula_crops: list[tuple[int, str]] = []
        for box in [b for b in item.get("boxes") or []
                    if b.get("cls") == "isolate_formula" and float(b.get("conf") or 0) >= 0.25][:6]:
            try:
                x0, y0, x1, y1 = [float(x) for x in box["xyxy"]]
            except Exception:
                continue
            crop_box = (max(0, int(x0) - 6), max(0, int(y0) - 6),
                        min(width, int(x1) + 6), min(height, int(y1) + 6))
            if crop_box[2] - crop_box[0] < 30 or crop_box[3] - crop_box[1] < 18:
                continue
            out_img = image_dir / f"formula_{page_no:03d}_{len(formula_crops) + 1}.png"
            try:
                with Image.open(path) as im:
                    im.crop(crop_box).save(out_img)
                formula_crops.append((page_no, str(out_img)))
            except Exception:
                continue
        if formula_crops and os.getenv("TFV2_FORMULA_OCR", "1") != "0":
            try:
                formula_script = ROOT / "tools" / "formula_ocr.py"
                if formula_script.is_file():
                    proc = subprocess.run(
                        [python, str(formula_script), *[f for _, f in formula_crops]],
                        capture_output=True, text=True, timeout=120,
                    )
                    ocr_items = (json.loads(proc.stdout or "{}") if proc.returncode == 0 else {}).get("items") or []
                    for (page_no, fpath), ocr in zip(formula_crops, ocr_items):
                        latex = str(ocr.get("latex") or "").replace("\textstyle", "").strip()[:300]
                        if not latex or latex.startswith("\begin{document}"):
                            continue
                        page = next((p for p in ledger.pages if p.page_no == page_no), None)
                        if page is None:
                            continue
                        page.text = ((page.text or "").rstrip() + "\n[公式OCR] $" + latex + "$")
            except Exception:
                pass


def _add_page_scans(ledger, source: Path, image_dir: Path) -> None:
    """无文本层且没有可抽图的页：渲染整页图，作为“整页扫描”参与覆盖；不是冒充内容图。"""
    if source.suffix.lower() != ".pdf":
        return
    try:
        import pymupdf
        doc = pymupdf.open(str(source))
    except Exception:
        return
    try:
        for page in ledger.pages:
            if len((page.text or "").strip()) >= 20:
                continue
            if any(_usable_image(img.asset_path) for img in page.images):
                continue
            try:
                pix = doc[page.page_no - 1].get_pixmap(dpi=140)
                path = image_dir / f"page_scan_{page.page_no:03d}.png"
                pix.save(str(path))
                page.images.append(PageImage(
                    image_id=f"page_scan_{page.page_no:03d}", kind="screenshot",
                    asset_path=str(path), discarded_reason=None,
                ))
            except Exception:
                continue
    finally:
        doc.close()

_EDGE_CACHE: dict[str, float] = {}
_SLIDE_CLASSIFY_CACHE: dict[str, str] = {}


def _image_is_flat(path: str) -> bool:
    """Reject a background colour wash/paper texture, not a line diagram."""
    try:
        from PIL import Image, ImageFilter, ImageStat
        import numpy as np
        with Image.open(path) as im:
            g = im.convert("L")
            g.thumbnail((512, 512), Image.LANCZOS)
            std = float(ImageStat.Stat(g).stddev[0])
            edge = g.filter(ImageFilter.GaussianBlur(2)).filter(ImageFilter.FIND_EDGES)
            density = float((np.array(edge) > 30).mean())
            return std < 12 and density < 0.02
    except Exception:
        return False


def _image_edge_density(path: str) -> float:
    if not path:
        return 0.0
    if path in _EDGE_CACHE:
        return _EDGE_CACHE[path]
    try:
        from PIL import Image, ImageFilter
        import numpy as np
        with Image.open(path) as im:
            g = im.convert("L")
            if max(g.size) > 1200:
                g.thumbnail((1200, 1200), Image.LANCZOS)
            edge = g.filter(ImageFilter.FIND_EDGES)
            value = float((np.array(edge) > 30).mean())
    except Exception:
        value = 0.0
    _EDGE_CACHE[path] = value
    return value


def _figure_page_ok(page, asset_path: str = "") -> bool:
    """Reject cover/agenda/title slides; keep pages that actually teach something."""
    text = re.sub(r"\s+", " ", page.text or "").strip()
    if page.page_no <= 2:
        return False
    if not text or len(text) < 18:
        return False
    if re.search(r"(目录|学习目标|课程安排|本章内容|本章小结|谢谢|Thanks|CONTENTS|Agenda)", text[:260], flags=re.I):
        return False
    # Filled blank/placeholder slides (□□, ( ), 1. 2. with no content) are not figures.
    if text.count("□") >= 3 or text.count("�") >= 1:
        return False
    if len(re.findall(r"\(\s*\)|（\s*）", text)) >= 2 and len(text) < 300:
        return False
    # A bare chapter/section outline page: 3.1 / 3.2 / ... with little prose.
    if len(text) < 140 and re.match(r"^\s*(\d+(?:\.\d+)*|第[一二三四五六七八九十]+[章节])\s", text):
        return False
    # Domain-neutral blank/template detector: a rendered slide without enough
    # edge structure is a cover/section divider, not a teaching diagram.
    if asset_path and _image_edge_density(asset_path) < 0.022:
        return False
    return True


def _trim_picture(path: str) -> str:
    """Trim uniform paper borders from a source picture; keep file on failure."""
    try:
        from PIL import Image, ImageChops
        src = Path(path)
        with Image.open(src) as im:
            rgb = im.convert("RGB")
            bg = Image.new("RGB", rgb.size, (255, 255, 255))
            diff = ImageChops.difference(rgb, bg).convert("L").point(lambda p: 255 if p > 12 else 0)
            box = diff.getbbox()
            if not box:
                return path
            w, h = rgb.size
            if (box[2] - box[0]) > w * 0.94 and (box[3] - box[1]) > h * 0.94:
                return path
            pad = 6
            box = (max(0, box[0] - pad), max(0, box[1] - pad),
                   min(w, box[2] + pad), min(h, box[3] + pad))
            out = src.with_name(src.stem + "_trim" + src.suffix)
            rgb.crop(box).save(out)
            return str(out)
    except Exception:
        return path


def _figure_supports(path: str, section, caption: str) -> bool:
    """VLM check with a section-specific cache; fail open on service errors."""
    if _VISION_DEADLINE and time.monotonic() > _VISION_DEADLINE:
        # Accuracy first: an unverified figure is not attached. A missing figure
        # is visible; a wrong figure silently teaches the wrong thing.
        return False
    import hashlib
    h = _image_hash(path)
    context = " ".join([
        section.title or "", section.summary or "",
        " ".join(b.text or "" for b in section.blocks[:2]),
    ])[:900]
    if len(context.strip()) < 24:
        return True
    key = "relevance-v1:" + (h or path) + ":" + hashlib.sha1(context.encode("utf-8")).hexdigest()[:12]
    cache = _load_vision_cache()
    if key in cache:
        return cache[key] == "yes"
    try:
        from core.ai_vision import verify_teaching_figure
        ok = bool(_call_with_timeout(verify_teaching_figure, 15, path,
                                     section_title=section.title or "",
                                     context=context, caption=caption))
    except Exception:
        return False
    cache[key] = "yes" if ok else "no"
    try:
        _vision_cache_path().write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    return ok


def _figure_caption_like(text: str) -> bool:
    return bool(re.search(r"(图\s*\d|如图|电路图|波形图|特性曲线|示意图|框图|流程图)", text or ""))


def _auto_figures(section, ledger, pages: list[int], *, max_figures: int = 2):
    """从资料页抽图：视觉识别、去重、去 logo，图注写清第几页；只挂真正有内容的图。"""
    import os
    if os.getenv("TERMFINALE_SKIP_FIGURE_VISION") == "1":
        return []
    if max_figures <= 0:
        return []
    by_no = {p.page_no: p for p in ledger.pages}
    seen_count: dict[str, int] = {}
    for p in ledger.pages:
        for img in p.images:
            if img.asset_path:
                h = _image_hash(img.asset_path)
                if h:
                    seen_count[h] = seen_count.get(h, 0) + 1
    picked: list[tuple[int, str, str, list[float] | None]] = []
    for p in pages:
        page = by_no.get(p)
        if page is None:
            continue
        candidates = []
        for img in page.images:
            if not _usable_image(img.asset_path):
                continue
            # Reject near-flat colour washes/background images. A legitimate
            # diagram/photo has edge structure; a painted rectangle does not.
            if _image_edge_density(img.asset_path) < 0.012 or _image_is_flat(img.asset_path):
                continue
            h = _image_hash(img.asset_path)
            if h and seen_count.get(h, 0) > 2:  # 页眉 logo/背景重复图，丢掉
                continue
            candidates.append(img)
        if not candidates:
            continue
        candidates.sort(key=lambda x: (x.kind == "screenshot", -Path(x.asset_path).stat().st_size))
        candidates = candidates[:3]
        for img in candidates:
            layout_caption = False
            generic_caption = False
            if img.image_id.startswith("layout_"):
                if img.caption and _figure_caption_like(img.caption):
                    caption = img.caption
                    layout_caption = True
                else:
                    caption = f"资料第 {p} 页图示（图注待核对）"
                    generic_caption = True
            elif img.image_id.startswith("formula_") and img.caption and _figure_caption_like(img.caption):
                caption = img.caption
                layout_caption = True
            elif img.kind == "screenshot":
                caption = _slide_caption(img.asset_path, section.title)
                if not caption and img.image_id.startswith("vector_") and not (_VISION_DEADLINE and time.monotonic() > _VISION_DEADLINE):
                    try:
                        _call_with_timeout(_classify_slide_batch, 25, [img.asset_path])
                    except Exception:
                        pass
                    caption = _slide_caption(img.asset_path, section.title)
                # Vector-diagram pages often have very little extractable text;
                # allow them when the vision classifier gave a concrete caption
                # and the crop has real edge structure. Covers/agendas still lack
                # a caption and are rejected.
                if not _figure_page_ok(page, img.asset_path):
                    if not caption or _image_edge_density(img.asset_path) < 0.04:
                        continue
            else:
                caption = _vision_caption(img.asset_path)
            if not caption and img.image_id.startswith("layout_"):
                # Local fallback: keep a real layout crop even when the vision
                # caption service times out. The caption says it is unverified.
                if _image_edge_density(img.asset_path) >= 0.012 and not _image_is_flat(img.asset_path):
                    caption = f"资料第 {p} 页图示（图注待核对）"
                    generic_caption = True
            if not caption:
                # A page screenshot with a generic caption is not a teaching
                # figure. Keep it behind an explicit opt-in flag until the
                # layout/crop + caption pipeline can prove relevance.
                if os.getenv("TFV2_FIGURE_FALLBACK", "0") != "1":
                    continue
                if not _image_is_flat(img.asset_path):
                    caption = f"资料第 {p} 页图示：{section.title}"
                    generic_caption = True
                else:
                    continue
            if generic_caption and p <= 2:
                continue
            # A figure should share some vocabulary with the section it is
            # attached to. Page overlap alone is not enough (e.g. a decorative
            # photo on a concept page).
            cap_tokens = _tokens(caption)
            section_text = " ".join([
                section.title or "", section.summary or "",
                " ".join(b.text or "" for b in section.blocks[:6]),
            ])
            sec_tokens = _tokens(section_text)
            if not generic_caption and len(section_text.strip()) >= 24 and cap_tokens and sec_tokens and not (cap_tokens & sec_tokens):
                continue
            if generic_caption and img.image_id.startswith("docling_"):
                # A page-wide/background crop without a real vision caption is
                # not a teaching figure. Skip rather than attach a wrong image.
                continue
            layout_verified = img.image_id.startswith("layout_") and bool(img.caption)
            if not generic_caption and not layout_verified and not _figure_supports(img.asset_path, section, caption):
                continue
            picked.append((p, _trim_picture(img.asset_path), caption, getattr(img, "bbox", None)))
            break
        if len(picked) >= max_figures:
            break
    blocks = []
    for page_no, path, caption, bbox in picked:
        bid = f"{section.id}-fig-{page_no}"
        blocks.append(LectureBlock(
            id=bid,
            kind=BlockKind.FIGURE,
            text="",
            source_refs=[],
            figure=FigureRef(
                image_id=f"auto-{section.id}-{page_no}",
                caption=f"{caption}（资料原图，第 {page_no} 页）",
                source=SourceRef(material=ledger.material, page_start=page_no, page_end=page_no),
                after_block_id=bid,
                asset_path=f"assets/{Path(path).name}",
                origin="source",
                source_note=("DocLayout-YOLO 版面裁剪；图注为页标题/自动图注，发布前需人工核对图文对应。" if "layout_" in Path(path).name else ("视觉服务未确认图注；按页/节自动挂图，发布前必须人工核对图文对应。" if generic_caption else "视觉模型识别为教学内容图并生成图注；发布前仍需人工确认图文对应。")),
                bbox=bbox,
            ),
        ))
    return blocks




def _closing_text(persona: str, title: str, days_left: int | None, target_score: int | None, pages: int, gen_lang: str = "zh") -> str:
    day = f"还剩 {days_left} 天" if days_left is not None else "按你的节奏来"
    score = f"目标 {target_score} 分" if target_score is not None else "把该拿的分拿到"
    texts = {
        "老师": f"最后想说：这门课不是靠把 {pages} 页材料背下来，而是靠把每一节的“为什么”串起来。{day}，{score}，不需要一次做完所有事；今天先弄懂一节，明天再做一节，读完立刻合上讲义，自己复述一遍、做一道题。能讲清楚、能做对，才是真的会。你不需要很厉害才开始，开始了才会慢慢厉害。",
        "温柔小姐姐": f"别急，{pages} 页听起来很多，但我们已经把它拆成一节一节了。{day}，{score}，你只要今天读一小节、做一道题，就已经在往前走了。卡住的时候不用自责，回到出处那一页，慢慢看一遍就好。你已经愿意坐下来学了，这本身就很了不起；剩下的，我们一节一节来。",
        "学术AI": f"结语：本讲义覆盖《{title}》共 {pages} 页，目标是在 {day} 内建立可迁移的解题框架。{score}。建议以“定义—条件—推导—例题—易错”为闭环，每节读完后不看答案复述一次；若某一步无法复述，回到对应页码核对，而不是记忆结论。理解结构比堆积结论更有效。",
        "阳光小哥哥": f"兄弟/姐妹，{pages} 页看着吓人，其实拆开就是一节一节的小怪。{day}，{score}，别想着一口吃成胖子：今天先拿下这一节，做对一道题，给自己记一笔。错了就回原文页看一眼，不丢人；真正丢人的是明明不会还假装看懂。走，先把这一节干掉！",
        "暴力极客": f"直接说：{pages} 页不是让你背的，是让你拆的。{day}，{score}。每节只干三件事：搞懂定义、跟一遍例题、合上讲义自己做一遍。卡住就回出处页，不要靠感觉。别磨叽，也别自我感动；今天推进一节，明天再推进一节，进度是做题做出来的，不是看视频看出来的。",
    }
    if gen_lang == "en":
        en = {
            "老师": f"One last thing: this course is not about memorizing {pages} pages; it is about connecting the why of each section. With {day} left and a target of {score}, you do not need to do everything today. Understand one section, do one problem, then explain it without looking. If you can explain it and solve it, you own it. You do not need to be great to start; you become great by starting.",
            "温柔小姐姐": f"Take it easy. {pages} pages sound like a lot, but we have split them into small sections. With {day} left and a target of {score}, one section and one problem today is already progress. If you get stuck, go back to the cited page and read it slowly. You have already chosen to sit down and learn, and that matters. We will take it one section at a time.",
            "学术AI": f"Closing: this lecture covers {pages} pages of {title}. The goal is a transferable problem-solving framework within {day}. Use the loop definition → conditions → derivation → example → pitfalls, and recall each section without looking at the answer. If a step cannot be recalled, return to the cited page instead of memorizing the conclusion.",
            "阳光小哥哥": f"Hey, {pages} pages look scary, but they are just small sections. With {day} left and a target of {score}, take one section today, solve one problem, and log the win. If you miss it, go back to the source page; that is normal. Do not pretend to understand; just take the next section down.",
            "暴力极客": f"Straight talk: {pages} pages are not for memorizing, they are for dismantling. With {day} left and a target of {score}, each section has three jobs: understand the definition, follow one example, then close the book and do it yourself. Stuck? Go back to the cited page. Progress comes from problems solved, not videos watched.",
        }
        return en.get(persona, en["老师"])
    return _tr(texts.get(persona, texts["老师"]), gen_lang)



def _terms(raw: str) -> list[str]:
    return [x.strip() for x in re.split(r"[\n,，、;；]+", raw or "") if x.strip()]


_GENERIC_CONSTRAINTS = {
    "全都是重点", "全是重点", "全部都是重点", "全部是重点", "全考", "全都考",
    "全部考", "全都要", "全部要", "无", "没有", "没有重点", "无重点", "无特别重点",
}


def _is_generic_constraint(term: str) -> bool:
    t = re.sub(r"[\s，,。；;、:：]+", "", term or "")
    if not t:
        return True
    if t in _GENERIC_CONSTRAINTS:
        return True
    return any(t.startswith(x) and len(t) <= len(x) + 3 for x in ("全都是重点", "全是重点", "全考", "全部都是重点"))


def _weighted_terms(raw: str) -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    for token in _terms(raw):
        parts = re.split(r"[=＝:：]", token, maxsplit=1)
        term = parts[0].strip()
        weight = 3
        if len(parts) == 2:
            try:
                weight = max(1, min(5, int(re.sub(r"[^0-9]", "", parts[1]) or 3)))
            except Exception:
                weight = 3
        if term and not _is_generic_constraint(term):
            out.append((term, weight))
    return out


def _section_text(section) -> str:
    return "\n".join([section.title] + [b.text for b in section.blocks if b.text])


def _check_constraints(sections, key_points: str, excluded: str) -> None:
    keys = [t for t, _ in _weighted_terms(key_points)]
    if keys:
        missing = [k for k in keys if not any(k in _section_text(sec) for sec in sections)]
        if missing:
            raise GenerateError("重点没有落到正文：" + "、".join(missing) + "；请调整重点词或重试")
    bans = [x for x in _terms(excluded) if not _is_generic_constraint(x)]
    if bans:
        hits = [b for b in bans if any(b in _section_text(sec) for sec in sections)]
        if hits:
            raise GenerateError("明确不考的内容仍出现在正文：" + "、".join(hits) + "；请重试或改写资料范围")





def _tokens(text: str) -> set[str]:
    out: set[str] = set()
    for word in re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]+", text or ""):
        if re.fullmatch(r"[\u4e00-\u9fff]+", word):
            if len(word) == 1:
                out.add(word)
            else:
                out.update(word[i:i + 2] for i in range(len(word) - 1))
        else:
            out.add(word.lower())
    return out



_DIGITS = "零一二三四五六七八九"


def _cn_num(n: int) -> str:
    if n <= 10:
        return "十" if n == 10 else _DIGITS[n]
    if n < 20:
        return "十" + _DIGITS[n - 10]
    if n < 100:
        return _DIGITS[n // 10] + "十" + (_DIGITS[n % 10] if n % 10 else "")
    return str(n)




GEN_LANG_LABEL = {"zh": "简体中文", "hant": "繁體中文", "en": "English"}


def _tr(text: str, gen_lang: str) -> str:
    if gen_lang != "hant":
        return text
    try:
        from opencc import OpenCC
        return OpenCC("s2twp").convert(text)
    except Exception:
        return text

def _make_knowledge_map(title: str, sections, out: Path, gen_lang: str = "zh") -> Path | None:
    """Draw a clean chapter structure map from the real outline (no subject keywords)."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        names = [(sec.title or "").strip() for sec in sections if (sec.title or "").strip()][:16]
        if not names:
            return None
        def fnt(sz):
            candidates = [
                ("/System/Library/Fonts/STHeiti Medium.ttc", 1),
                ("/System/Library/Fonts/STHeiti Light.ttc", 1),
                ("/System/Library/Fonts/Supplemental/Songti.ttc", 1),
                ("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", 0),
            ]
            for path, index in candidates:
                try:
                    return ImageFont.truetype(path, sz, index=index)
                except Exception:
                    continue
            return ImageFont.load_default()
        rows = (len(names) + 1) // 2
        w, h = 1500, max(660, 250 + rows * 82)
        im = Image.new("RGB", (w, h), "#fbfaf4")
        d = ImageDraw.Draw(im)
        title_font, node_font, small = fnt(42), fnt(27), fnt(18)
        d.text((70, 42), title[:60], font=title_font, fill="#20332d")
        d.text((70, 94), "章节知识地图 · 系统根据本讲义目录生成" if gen_lang != "en" else "Chapter map · generated from this lecture outline", font=small, fill="#7b857c")
        d.line((70, 132, w - 70, 132), fill="#cbd5c8", width=2)
        for i, name in enumerate(names):
            col, row = i % 2, i // 2
            x, y = 76 + col * 704, 180 + row * 82
            d.rounded_rectangle((x, y, x + 638, y + 60), radius=14, outline="#9bb3a1", fill="#ffffff", width=2)
            d.rounded_rectangle((x + 12, y + 12, x + 54, y + 48), radius=8, fill="#e7f0df")
            d.text((x + 21, y + 17), f"{i+1:02d}", font=small, fill="#36503d")
            d.text((x + 70, y + 15), name[:36], font=node_font, fill="#26352d")
        p = out / "assets" / "generated_knowledge_map.png"
        p.parent.mkdir(parents=True, exist_ok=True)
        im.save(p)
        return p
    except Exception:
        return None


def _chapter_label(title: str, gen_lang: str = "zh") -> str:
    if gen_lang == "en":
        return title.strip() if title.strip().lower().startswith("chapter") else "Chapter 1: " + title.strip()
    if re.match(r"^第[一二三四五六七八九十百0-9]+章", title.strip()):
        return _tr(title.strip(), gen_lang)
    return _tr("第一章 " + title.strip(), gen_lang)


def _section_label(label: str, index: int, gen_lang: str = "zh") -> str:
    text = re.sub(r"^第[一二三四五六七八九十百0-9.]+节\s*", "", label.strip())
    text = re.sub(r"^[0-9]+(?:\.[0-9]+)*\s*", "", text)
    text = text.strip() or ("Course content" if gen_lang == "en" else "教材内容")
    if gen_lang == "en":
        text = (text.replace("正文", "Content").replace("补充内容", "Supplementary content")
                .replace("核心内容", "Core content").replace("教材内容", "Course content"))
        text = re.sub(r"（第\s*([0-9]+(?:[–\-][0-9]+)?)\s*页）", r"(pp. \1)", text)
        return f"Section {index}: {text}"
    return _tr(f"第{_cn_num(index)}节 {text}", gen_lang)



def _fallback_title(section, index: int, label: str = "") -> str:
    """只在模型没给出合格短标题时使用；绝不再拿正文第一句充当标题。"""
    text = re.sub(r"（第\s*[0-9]+(?:[–\-][0-9]+)?\s*页）", "", label or "").strip()
    text = re.sub(r"^第[一二三四五六七八九十百0-9.]+节\s*", "", text).strip()
    text = re.sub(r"^(正文|核心内容|补充内容|教材内容|课程内容)$", "", text).strip()
    text = text.strip(" ：:，,。；;")
    if 2 <= len(text) <= 24 and not re.search(r"[。；;！？?]", text):
        return text
    return f"知识点 {index}"

def _fallback_figures(section, ledger, pages: list[int]):
    """Last-resort source image attachment.

    The strict vision matcher is deliberately conservative, but returning zero
    figures from a slide deck that clearly contains diagrams is a product
    failure. This fallback only takes a large, non-flat, non-decorative image
    from a low-text page and labels it as unverified, so the user can still see
    and check the source figure.
    """
    by_no = {p.page_no: p for p in ledger.pages}
    for page_no in pages:
        page = by_no.get(page_no)
        if page is None or not page.images:
            continue
        if page.page_no <= 2:
            continue
        if len((page.text or "").strip()) > 300:
            continue
        if re.search(r"(目录|学习目标|课程安排|谢谢|Thanks|CONTENTS|Agenda)", (page.text or "")[:200], flags=re.I):
            continue
        candidates = []
        for img in page.images:
            path = img.asset_path
            if not path or not _usable_image(path):
                continue
            try:
                size = Path(path).stat().st_size
            except OSError:
                continue
            if size < 20000:
                continue
            if _image_edge_density(path) < 0.04 or _image_is_flat(path):
                continue
            candidates.append((size, path))
        if not candidates:
            continue
        candidates.sort(reverse=True)
        path = _trim_picture(candidates[0][1])
        caption = _slide_caption(path, section.title) or f"资料第 {page_no} 页图示：{section.title}"
        block_id = f"{section.id}-fallback-{page_no}"
        return [LectureBlock(
            id=block_id, kind=BlockKind.FIGURE, text="", source_refs=[],
            figure=FigureRef(
                image_id=f"fallback-{section.id}-{page_no}",
                caption=f"{caption}（资料原图，第 {page_no} 页；自动抽取，需人工核对图文对应）",
                source=SourceRef(material=ledger.material, page_start=page_no, page_end=page_no),
                after_block_id=block_id,
                asset_path=f"assets/{Path(path).name}",
                origin="source",
                source_note="视觉语义匹配未确认时的保底抽取；请人工核对是否属于本节。",
            ),
        )]
    return []


def _attach_figures(section, ledger, pages: list[int]):
    figs = _auto_figures(section, ledger, pages)
    if not figs and os.getenv("TFV2_FIGURE_FALLBACK", "0") == "1":
        figs = _fallback_figures(section, ledger, pages)
    figs = sorted(figs, key=lambda f: f.figure.source.page_start)
    for fig in figs:
        page_no = fig.figure.source.page_start
        cap_tokens = _tokens(fig.figure.caption)
        candidates = []
        for j, block in enumerate(section.blocks):
            if block.kind in (BlockKind.PARAGRAPH, BlockKind.CLAIM,
                              BlockKind.FORMULA, BlockKind.EXAMPLE) and any(
                    ref.page_start <= page_no <= ref.page_end for ref in block.source_refs):
                candidates.append((len(cap_tokens & _tokens(block.text)), j))
        if candidates:
            # 语义最接近的一段优先；同分时取靠后（通常更贴近该页讲解）
            pos = max(candidates, key=lambda x: (x[0], x[1]))[1] + 1
        else:
            # No lexical match: put the figure after the first paragraph that
            # cites this page (not at the very end of the section).
            pos = next((j + 1 for j, b in enumerate(section.blocks)
                        if b.kind == BlockKind.PARAGRAPH
                        and any(ref.page_start <= page_no <= (ref.page_end or ref.page_start)
                                for ref in b.source_refs)), len(section.blocks))
        section.blocks.insert(pos, fig)
    return section

def _dedupe_titles(sections, gen_lang: str = "zh") -> None:
    seen: set[str] = set()
    for index, section in enumerate(sections, start=1):
        base = (section.title or "").strip() or ("Chapter" if gen_lang == "en" else "核心考点")
        if base in seen:
            base = _fallback_unique_title(section, index, seen, gen_lang)
        section.title = base
        seen.add(base)


def _hant_sections(sections) -> None:
    """OpenCC 把模型漏掉的简体正文统一转成繁體；公式/英文不受影响。"""
    try:
        from opencc import OpenCC
        cc = OpenCC("s2twp")
    except Exception:
        return
    for section in sections:
        try:
            section.title = cc.convert(section.title)
            if section.summary:
                section.summary = cc.convert(section.summary)
            section.objectives = [cc.convert(x) for x in (section.objectives or [])]
            section.key_terms = [cc.convert(x) for x in (section.key_terms or [])]
            section.self_test = [cc.convert(x) for x in (section.self_test or [])]
            for block in section.blocks:
                if block.text:
                    block.text = cc.convert(block.text)
        except Exception:
            continue


def _add_ai_figure(section, *, ledger, out: Path, index: int) -> bool:
    if getattr(section, "visual_hint", "none") != "concept":
        return False
    try:
        from tfv2.render import imagegen
        concept = re.sub(r"^第[一二三四五六七八九十百0-9.]+节\s*", "", section.title or "").strip()
        prompt = (
            f"Minimal editorial illustration for a university lecture section about: {concept}. "
            "One clear educational visual metaphor, clean vector-like shapes, restrained ink/teal palette, "
            "white paper background, generous whitespace, no text, no letters, no numbers, no labels, "
            "no diagram annotations, no UI. It is decorative only and must not pretend to be a precise "
            "circuit/math/medical diagram."
        )
        art = imagegen.generate(prompt, size="1024x768")
        asset_dir = out / "assets"; asset_dir.mkdir(parents=True, exist_ok=True)
        dst = asset_dir / f"ai_sec_{index}.png"
        shutil.copyfile(art["path"], dst)
        after = next((b for b in section.blocks if b.kind != BlockKind.FIGURE), section.blocks[0])
        section.blocks.append(LectureBlock(
            id=f"ai-fig-{section.id}-{index}", kind=BlockKind.FIGURE, text="", source_refs=[],
            figure=FigureRef(
                image_id=f"ai-{section.id}-{index}",
                caption="AI 生成的示意装饰图（非精确知识图，需人工判断）",
                source=SourceRef(material=ledger.material, page_start=1, page_end=1),
                after_block_id=after.id, asset_path=f"assets/ai_sec_{index}.png",
                origin="schematic",
                source_note="由图位意图判定为 concept 后生成；不含文字/数值，不承担知识表达。",
            ),
        ))
        return True
    except Exception:
        return False


def _augment_structure_tables(data: dict, pdf_path: Path, out: Path) -> None:
    """Docling sometimes misses rasterized tables. Ask vision only for pages
    that have pictures but no table, and accept only a valid pipe table."""
    import os
    if os.getenv("TERMFINALE_SKIP_TABLE_VISION") == "1":
        return
    from tfv2.render import table_structure
    pages = [p for p in data.get("pages") or [] if not (p.get("tables") or []) and (p.get("pictures") or [])]
    if not pages:
        return
    try:
        import pymupdf
        from core.ai_vision import read_table_markdown
        doc = pymupdf.open(str(pdf_path))
    except Exception:
        return
    target = out / "table_pages"
    target.mkdir(parents=True, exist_ok=True)
    try:
        for page in pages[:8]:
            try:
                pno = int(page.get("page") or 0)
                if not 1 <= pno <= len(doc):
                    continue
                img = target / f"page_{pno:03d}.png"
                doc[pno - 1].get_pixmap(dpi=160).save(str(img))
                text = read_table_markdown(str(img))
                if not text or not table_structure.table_quality(text).get("ok"):
                    continue
                page.setdefault("tables", []).append({
                    "kind": "table", "text": table_structure.normalize_table(text),
                    "bbox": [0, 0, 0, 0], "source": "vision_fallback",
                })
            except Exception:
                continue
    finally:
        try:
            doc.close()
        except Exception:
            pass


def _docling_needed(pdf_path: Path) -> bool:
    """Only pay Docling when the PDF has tables or low-text (scanned) pages."""
    try:
        import pymupdf
        doc = pymupdf.open(str(pdf_path))
    except Exception:
        return False
    try:
        for page in doc:
            try:
                if page.find_tables().tables:
                    return True
            except Exception:
                pass
            if len(page.get_text("text") or "") < 20 and page.get_images(full=True):
                return True
        return False
    finally:
        doc.close()


def _structure_with_optional_docling(pdf_path: Path, out: Path, image_dir: Path) -> dict:
    """Use an external Docling environment when explicitly configured."""
    if os.getenv("TERMFINALE_SKIP_DOCLING") == "1":
        return build_source_structure(pdf_path, out / "structure", image_dir=image_dir)
    py = os.getenv("TERMFINALE_DOCLING_PYTHON", "").strip()
    if not py:
        candidate = Path.home() / "Library/Application Support/TermFinale/docling/venv/bin/python"
        if candidate.is_file():
            py = str(candidate)
    if py and Path(py).is_file():
        target = out / "structure_docling"
        cmd = [py, str(ROOT / "tools" / "docling_structure.py"), str(pdf_path), str(target)]
        env = dict(os.environ)
        env.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
        persistent_cache = Path.home() / "Library/Application Support/TermFinale/docling/hf_cache"
        if persistent_cache.is_dir():
            env.setdefault("HF_HOME", str(persistent_cache))
        try:
            subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=600, env=env)
            data = json.loads((target / "structure.json").read_text(encoding="utf-8"))
            if data.get("pages"):
                _augment_structure_tables(data, pdf_path, out)
                return data
        except Exception:
            pass
    return build_source_structure(pdf_path, out / "structure", image_dir=image_dir)




def _fill_missing_pages(candidate, pages: list[int], page_by_no: dict, ledger, index: int) -> list[int]:
    """把模型漏掉的页补成资料原文块，返回「本次补了哪些页」。

    根因：模型经常只引用一部分页；以前第二次还漏就整节失败，重跑一次要再花一整节的 token，
    用户还拿不到东西。资料页本身就有正文，补进去既保真又不编造。
    """
    # 小节级出处是硬要求：模型偶尔整节不给 section.source_refs，这里补上资料页，
    # 否则补完正文仍会被门禁判“节缺出处”。
    if not candidate.source_refs:
        candidate.source_refs = [SourceRef(material=ledger.material, page_start=p, page_end=p)
                                 for p in sorted(set(pages))]
    cited = _cited_pages(candidate)
    filled: list[int] = []
    for pno in sorted(set(pages) - cited):
        page = page_by_no.get(pno)
        raw = (page.text or "").strip() if page is not None else ""
        if raw:
            block_id = f"source-fill-{index}-{pno}"
            if any(b.text.startswith(f"资料补充（第 {pno} 页）") for b in candidate.blocks):
                continue
            candidate.blocks.append(LectureBlock(
                id=block_id, kind=BlockKind.PARAGRAPH,
                text=f"资料补充（第 {pno} 页）：{raw[:1800]}",
                source_refs=[SourceRef(material=ledger.material, page_start=pno, page_end=pno)],
            ))
            filled.append(pno)
        else:
            block_id = f"blank-{index}-{pno}"
            if any(b.id == block_id for b in candidate.blocks):
                continue
            candidate.blocks.append(LectureBlock(
                id=block_id, kind=BlockKind.PARAGRAPH,
                text="本页为空白页或图片页，原资料没有可提取的正文内容。",
                source_refs=[SourceRef(material=ledger.material, page_start=pno, page_end=pno)],
            ))
            filled.append(pno)
    return sorted(filled)


def _accept_issue(candidate, rel: list[tuple[str, int]], attempt: int) -> str:
    """这一稿能不能收；返回问题原因，空串表示可以收。

    高权重重点只出现一次：第一次要求重写，第二次不再因此判死（否则一节白跑）。
    """
    if attempt == 0:
        once = [t for t, w in rel if w >= 4 and _section_text(candidate).count(t) < 2]
        if once:
            return "高权重重点只出现一次，未展开：" + "、".join(once)
    return ""


def _source_fallback_section(ledger, page_by_no: dict, index: int, label: str,
                             pages: list[int], reason: str):
    """某一段模型写不出来时，用资料原文兜底：有原文排原文，没有就写明空白/图片页。"""
    from tfv2.domain.lecture import BlockKind, LectureBlock, LectureSection, SourceRef

    blocks = []
    for pno in pages:
        page = page_by_no.get(pno)
        raw = (page.text or "").strip() if page is not None else ""
        if raw:
            blocks.append(LectureBlock(
                id=f"src-fb-{index}-{pno}", kind=BlockKind.PARAGRAPH,
                text=f"资料原文（第 {pno} 页）：{raw[:1800]}",
                source_refs=[SourceRef(material=ledger.material, page_start=pno, page_end=pno)],
            ))
        else:
            blocks.append(LectureBlock(
                id=f"blank-fb-{index}-{pno}", kind=BlockKind.PARAGRAPH,
                text=f"第 {pno} 页是空白页或纯图片，没有可提取的文字。",
                source_refs=[SourceRef(material=ledger.material, page_start=pno, page_end=pno)],
            ))
    refs = [SourceRef(material=ledger.material, page_start=p, page_end=p) for p in pages]
    return LectureSection(id=f"sec-{index}", title=label or f"第 {index} 节",
                          blocks=blocks, source_refs=refs,
                          summary=f"这一节改为原文页组织：{reason}"[:200])

def generate_lecture(
    source_path: str | Path,
    *,
    title: str,
    course: str = "",
    target_score: int | None = 80,
    days_left: int | None = 7,
    foundation: str = "基础较弱",
    persona: str = "老师",
    key_points: str = "",
    excluded: str = "",
    custom_prompt: str = "",
    gen_lang: str = "zh",
    illustrations: bool = False,
    progress: _PROGRESS | None = None,
    resume_dir: Path | None = None,
    checkpoint_path: Path | None = None,
) -> dict:
    source = Path(source_path)
    if not source.is_file():
        raise GenerateError("上传文件不存在")
    if source.stat().st_size > 200 * 1024 * 1024:
        raise GenerateError("文件超过 200MB，暂不支持")
    title = (title or "").strip() or source.stem
    course = (course or "").strip() or title
    # Keep learner-facing metrics bounded even when called outside the UI.
    target_score = max(60, min(100, int(target_score or 80)))
    days_left = max(1, min(30, int(days_left or 7)))
    global _VISION_DEADLINE
    _VISION_DEADLINE = time.monotonic() + 75
    resume_data: dict = {}
    if resume_dir is not None:
        out = Path(resume_dir)
        if not out.is_dir():
            raise GenerateError("续跑目录不存在")
        aid = out.name
        ck_file = Path(checkpoint_path) if checkpoint_path else out / "lecture_checkpoint.json"
        if not ck_file.is_file():
            raise GenerateError("没有找到讲义续跑检查点")
        try:
            resume_data = json.loads(ck_file.read_text(encoding="utf-8"))
        except Exception as exc:
            raise GenerateError(f"续跑检查点损坏：{exc}") from exc
        source = Path(str(resume_data.get("source") or source))
        if not source.is_file():
            raise GenerateError("续跑原资料不存在")
        copied = next((out / "source").glob("*"), None)
        if copied is None:
            raise GenerateError("续跑目录缺少已保存的原资料")
    else:
        aid = _new_id()
        out = ARTIFACT_ROOT / aid
        out.mkdir(parents=True, exist_ok=False)
        (out / "source").mkdir()
        copied = out / "source" / source.name
        try:
            shutil.copy2(source, copied)
        except Exception as exc:
            _fail(out, f"保存资料失败：{exc}")
    _stage(out, "artifact_created")
    image_dir = out / "source_assets"
    image_dir.mkdir(exist_ok=True)
    if progress:
        progress(5, "读取资料 / 建立页账本")
    ledger_source = copied
    build_source = f"source/{copied.name}"
    if copied.suffix.lower() in _IMAGE_EXTS:
        if progress:
            progress(6, "图片 OCR / 建立页账本")
        try:
            ledger_source = _image_to_pdf(copied, out / "source")
        except GenerateError as exc:
            _fail(out, str(exc))
        except Exception as exc:
            _fail(out, f"图片 OCR 失败：{exc}")
        build_source = str(ledger_source.relative_to(out))
    elif copied.suffix.lower() in (".docx", ".doc", ".ppt"):
        if progress:
            progress(6, "Office 转 PDF / 建立页账本")
        try:
            ledger_source = _convert_docx(copied, out / "source")
        except GenerateError as exc:
            _fail(out, str(exc))
        build_source = str(ledger_source.relative_to(out))
    try:
        _stage(out, "ledger_base_start")
        ledger = _ledger(ledger_source, image_dir)
        _stage(out, "ledger_base_ready")
        _ocr_low_text(ledger, ledger_source)
        _stage(out, "ocr_ready")
        _add_page_scans(ledger, ledger_source, image_dir)
        _add_pptx_slide_renders(ledger, ledger_source, image_dir)
        _stage(out, "scans_ready")
        try:
            if os.getenv("TERMFINALE_ADAPTIVE_PARSE", "1") == "1" and not _docling_needed(Path(ledger_source)):
                structure = build_source_structure(Path(ledger_source), out / "structure", image_dir=image_dir)
                _stage(out, "structure_skipped_text")
            else:
                structure = _structure_with_optional_docling(Path(ledger_source), out, image_dir)
            _stage(out, "structure_ready")
            _apply_docling_text(ledger, structure)
            _add_structure_vector_figures(ledger, structure)
            _add_docling_picture_figures(ledger, structure, Path(ledger_source), image_dir)
        except Exception:
            pass
        try:
            text_rich = sum(1 for p in ledger.pages if len((p.text or "").strip()) >= 400) >= max(1, ledger.page_count) * 0.8
            if os.getenv("TERMFINALE_SKIP_LAYOUT") == "1" or (text_rich and os.getenv("TERMFINALE_LAYOUT_TEXT_RICH", "1") != "0"):
                # 文字层已经很密的 PDF，版面检测收益低、每次要 10s+
                _stage(out, "layout_skipped_text_rich" if text_rich else "layout_skipped")
            else:
                _add_doclayout_figures(ledger, Path(ledger_source), image_dir)
                _stage(out, "layout_ready")
        except Exception:
            pass
        try:
            if os.getenv("TERMFINALE_SKIP_FORMULA_OCR") == "1":
                _stage(out, "formula_skipped")
            else:
                _add_formula_ocr(ledger, Path(ledger_source), image_dir)
                _stage(out, "formula_ready")
        except Exception:
            pass
        _preclassify_slide_figures(ledger)
        try:
            source_pages.save_source_pages(out, ledger)
        except Exception:
            pass
    except Exception as exc:
        _fail(out, f"资料解析失败：{exc}")

    _stage(out, "ledger_ready")
    head_text = "\n".join((p.text or "") for p in ledger.pages[:2])
    if looks_like_exam(head_text):
        _fail(out, "这份资料看起来是试卷/答题纸，不是教材或课件；讲义生成暂不支持。请用教材、课件或讲义资料。")

    page_count = ledger.page_count
    _stage(out, "plan_start")
    plan, outline_used = _plan(ledger)
    covered = {p for _, ps in plan for p in ps}
    missing_pages = [p for p in range(1, page_count + 1) if p not in covered]
    if missing_pages:
        for i in range(0, len(missing_pages), 8):
            group = missing_pages[i:i + 8]
            plan.append((f"补充内容（第 {group[0]}–{group[-1]} 页）", group))
    if len(plan) > 30:
        # 大纲过碎（>30 段）不能直接失败：单份资料 ≤159 页优先保证全文覆盖，回退 8 页/段。
        plan = [(f"核心内容（第 {p[0]}–{p[-1]} 页）", p) for p in _chunks(page_count, 8)]
        outline_used = False
    if len(plan) > 30:
        _fail(out, f"{page_count} 页会切成 {len(plan)} 段，超过实验管线上限；请先按章节拆分资料")
    saved_plan = resume_data.get("plan") if isinstance(resume_data.get("plan"), list) else None
    if saved_plan:
        plan = [(str(x[0]), [int(p) for p in x[1]]) for x in saved_plan if isinstance(x, list) and len(x) == 2]
        outline_used = True

    _stage(out, "plan_ready")
    try:
        provider = os.getenv("TERMFINALE_SECTION_PROVIDER", "deepseek").strip().lower()
        if provider == "qwen":
            from tfv2.llm.qwen_text import QwenTextClient
            client = QwenTextClient(model=os.getenv("TERMFINALE_QWEN_TEXT_MODEL", "qwen-max"))
        else:
            client = DeepSeekClient()
    except Exception as exc:
        _fail(out, f"模型客户端不可用：{exc}")
    if not (key_points.strip() or excluded.strip() or custom_prompt.strip()):
        # 用户没提任何要求时，这一次模型调用是纯开销（实测 20–30s），直接跳过
        requirements = {"must_cover": [], "must_not": [], "instructions": [], "language": gen_lang}
    else:
        requirements = interpret_requirements(
            client, key_points=key_points, excluded=excluded, custom_prompt=custom_prompt,
            title=title, course=course, target_score=target_score, days_left=days_left,
            foundation=foundation, persona=persona, gen_lang=gen_lang,
        )
    _stage(out, "requirements_start")
    page_text_by_no = {p.page_no: (p.text or "") for p in ledger.pages}
    page_by_no = {p.page_no: p for p in ledger.pages}
    plan_index = [{"id": label, "title": label, "pages": pages} for label, pages in plan]
    parsed_exclusions = exclusions.specs_from_requirements(requirements, excluded, custom_prompt)
    matched_exclusions = exclusions.match_specs(
        parsed_exclusions["specs"],
        exclusions.build_index(page_text_by_no, plan_index),
    )
    active_specs = [s for s in matched_exclusions if not s.get("needs_confirm")]
    pending_specs = [s for s in matched_exclusions if s.get("needs_confirm")]
    exclusion_note = exclusions.exclusion_prompt(active_specs)
    if exclusion_note:
        requirements.setdefault("instructions", []).append(exclusion_note)
    # Plan the teaching units before writing sections. The planner is strictly
    # validated for complete page coverage; on any failure we keep the
    # deterministic outline/page plan above.
    try:
        if not saved_plan:
            if progress:
                progress(8, "根据考点规划章节结构")
            planned = plan_with_llm(client, ledger, plan, requirements=requirements, gen_lang=gen_lang)
            if planned and planned != plan:
                plan = planned
                outline_used = True
    except Exception:
        pass
    excluded_page_set = {
        p
        for spec in active_specs
        if spec.get("scope") in ("page", "section", "section_limit")
        for p in (spec.get("matched") or {}).get("pages") or []
    }
    if excluded_page_set:
        plan = [(label, [p for p in pages if p not in excluded_page_set]) for label, pages in plan]
        plan = [(label, pages) for label, pages in plan if pages]
        if not plan:
            _fail(out, "用户标记为不考的范围覆盖了全部资料，无法生成讲义")
    req_prompt = requirement_prompt(requirements)
    weighted = [(x["label"], x["weight"]) for x in requirements.get("must_cover", [])]
    _stage(out, "requirements_ready")
    sections: list = []
    chapter_title = _chapter_label(title, gen_lang)
    _concise_env = os.getenv("TERMFINALE_CONCISE_SECTIONS", "").strip()
    # 短资料默认“简洁初稿 + 逐点补讲”：实测到同样 5/8 覆盖比完整成文快 35%；
    # 长资料保持完整成文，避免为了速度牺牲深度。
    concise_mode = (_concise_env == "1") if _concise_env in ("0", "1") else (page_count <= 12)

    def author_one(index: int, label: str, pages: list[int]):
        display_label = _section_label(label, index, gen_lang)
        section = None
        last = ""
        fallback_client = None
        try:
            from tfv2.llm.qwen_text import QwenTextClient
            if isinstance(client, QwenTextClient):
                fallback_client = DeepSeekClient(model="deepseek-flash")
            else:
                fallback_client = QwenTextClient()
        except Exception:
            fallback_client = None
        force_qwen = os.getenv("TERMFINALE_FORCE_QWEN") == "1"
        for attempt in range(2):
            note = (
                "这一段是资料的第 " + "、".join(map(str, pages)) + " 页。"
                "每个 block 的 source_pages 必须从这些页码里取；整段必须让每一页至少出现在一个 block 的 source_pages 中。"
                "资料没有例题就不要硬编；不要写页码 P.x；公式用 $...$ 或 $$...$$。"
                "讲解要按“零基础也能看懂”的教材写法：先给直观解释，再给定义/公式，再给一个可跟做的例子；不要只列结论。"
            )
            if req_prompt:
                note += "\n用户需求（已由需求理解 Agent 结构化，必须按语义执行）：\n" + req_prompt
            if exclusion_note:
                note += "\n" + exclusion_note
            if concise_mode:
                note += " 本节正文控制在 1200 字以内：讲清主线与关键定义即可，细节留给后续补讲。"
            rel = [(t, w) for t, w in weighted if t in label or t in " ".join(page_text_by_no.get(p, "") for p in pages)]
            if rel:
                note += " 本节重点权重（1–5）：" + "、".join(f"{t}={w}" for t, w in rel) + "。"
                if any(w >= 4 for _, w in rel):
                    note += " 权重≥4 的重点必须至少两处展开（正文+例题/易错/小结），只提一次不算落实。"
            if attempt:
                note += " 上次有页面没有被引用；这次必须补上这些页的内容或明确说明。"
                if last:
                    note += " 上次内容问题：" + last + "。这次删掉空话、重复句和无具体步骤的假例题；资料少就写短，不要为凑字数加段。"
            try:
                choose_qwen = (fallback_client is not None and (attempt > 0 or force_qwen))
                candidate = author_section(
                    fallback_client if choose_qwen else client,
                    ledger, chapter_title=chapter_title, section_title=display_label,
                    pages=pages, target_score=target_score, days_left=days_left,
                    foundation=({"基础较弱": "Weak foundation", "基础一般": "Average foundation", "基础较好": "Strong foundation"}.get(foundation, foundation) if gen_lang == "en" else foundation),
                    persona=persona, extra_note=note, gen_lang=gen_lang, clamp_pages=True,
                )
            except (AuthoringError, LLMError) as exc:
                last = str(exc)
                section = None
                continue
            issue = _accept_issue(candidate, rel, attempt)
            if issue:
                last = issue
                section = None
                continue
            if attempt == 0:
                try:
                    from tfv2.quality import padding
                    pad_issues = padding.audit_section(candidate)
                except Exception:
                    pad_issues = []
                if pad_issues:
                    last = "内容可能有凑数/重复/空例题：" + "；".join(pad_issues[:3])
                    section = None
                    continue
            filled_pages = _fill_missing_pages(candidate, pages, page_by_no, ledger, index)
            if filled_pages:
                page_fill_stats[index] = {"label": label, "filled": filled_pages}
            missing = sorted(set(pages) - _cited_pages(candidate))
            if not missing:
                if candidate.title in ("正文", "核心内容", "补充内容", "教材内容", "课程内容"):
                    candidate.title = _fallback_title(candidate, index, label)
                return candidate
            last = "页面没有被任何 block 引用：" + "、".join(map(str, missing))
            section = None
        raise GenerateError(f"{label} 生成失败：{last}")

    from concurrent.futures import ThreadPoolExecutor, as_completed
    from tfv2.domain.lecture import LectureSection

    def _save_checkpoint(done: dict[int, object]) -> None:
        payload = {
            "source": str(source), "aid": aid,
            "params": {"title": title, "course": course, "target_score": target_score,
                       "days_left": days_left, "foundation": foundation, "persona": persona,
                       "key_points": key_points, "excluded": excluded,
                       "custom_prompt": custom_prompt, "gen_lang": gen_lang,
                       "illustrations": illustrations},
            "plan": [[label, pages] for label, pages in plan],
            "sections": {str(k): v.model_dump(mode="json") for k, v in sorted(done.items())},
        }
        try:
            (out / "lecture_checkpoint.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            if checkpoint_path is not None:
                Path(checkpoint_path).parent.mkdir(parents=True, exist_ok=True)
                Path(checkpoint_path).write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    resume_sections: dict[int, object] = {}
    for key, value in (resume_data.get("sections") or {}).items():
        try:
            resume_sections[int(key)] = LectureSection.model_validate(value)
        except Exception:
            continue
    fallback_sections: dict[int, dict] = {}
    page_fill_stats: dict[int, dict] = {}
    ordered: dict[int, object] = dict(resume_sections)
    todo = [(i, label, pages) for i, (label, pages) in enumerate(plan, start=1) if i not in ordered]
    _save_checkpoint(ordered)
    _stage(out, "sections_start")
    with ThreadPoolExecutor(max_workers=max(1, min(3, len(todo) or 1))) as pool:
        futures = {pool.submit(author_one, i, label, pages): (i, label) for i, label, pages in todo}
        for i, (label, pages) in enumerate(plan, start=1):
            if progress:
                progress(10 + int(75 * (i - 1) / len(plan)), f"生成第 {i}/{len(plan)} 段：{_section_label(label, i, gen_lang)}")
        for future in as_completed(futures):
            idx, label = futures[future]
            try:
                ordered[idx] = future.result()
                _save_checkpoint(ordered)
            except Exception as exc:
                # 单段失败不再拖垮整份讲义：用资料原文兜底，并把原因记进 project。
                from tfv2.product.errors import friendly_reason
                reason = friendly_reason(exc, limit=160)
                try:
                    ordered[idx] = _source_fallback_section(ledger, page_by_no, idx, label, pages, reason)
                    fallback_sections[idx] = {"index": idx, "label": label,
                                              "pages": list(pages), "reason": reason}
                    _save_checkpoint(ordered)
                except Exception:
                    _fail(out, str(exc))
    if len(ordered) != len(plan):
        _fail(out, f"续跑缺少 {len(plan) - len(ordered)} 节，检查点已保留")
    sections = [ordered[i] for i in sorted(ordered)]
    _stage(out, "sections_ready")
    filtered_sections = []
    filtered_plan = []
    removed_blocks_total = 0
    for index, (section, (label, pages)) in enumerate(zip(sections, plan), start=1):
        candidate = _attach_figures(section.model_copy(deep=True), ledger, pages)
        missing = sorted(set(pages) - _cited_pages(candidate))
        if missing:
            for pno in missing:
                page = page_by_no.get(pno)
                raw = (page.text or "").strip() if page is not None else ""
                if raw:
                    candidate.blocks.append(LectureBlock(
                        id=f"source-fallback-post-{index}-{pno}", kind=BlockKind.PARAGRAPH,
                        text=f"资料补充（第 {pno} 页）：{raw[:1800]}",
                        source_refs=[SourceRef(material=ledger.material, page_start=pno, page_end=pno)],
                    ))
        kept_blocks, removed_blocks = exclusions.filter_blocks(
            candidate.blocks, active_specs, excluded_page_set
        )
        candidate.blocks = kept_blocks
        removed_blocks_total += removed_blocks
        if not candidate.blocks:
            continue
        filtered_sections.append(candidate)
        filtered_plan.append((label, pages))
        if illustrations and not any(b.kind == BlockKind.FIGURE for b in candidate.blocks):
            try:
                from tfv2.render import imagegen
                concept = re.sub(r"^第[一二三四五六七八九十百0-9.]+节\s*", "", candidate.title or "").strip()
                prompt = (
                    f"Minimal educational concept illustration for a university lecture section about: {concept}. "
                    "One clear visual metaphor that helps a student grasp the core idea, clean vector-like shapes, "
                    "restrained ink/teal palette, white paper background, generous whitespace, no text, no letters, "
                    "no numbers, no labels, no diagram annotations, no UI. It is a conceptual aid only and must not "
                    "pretend to be a precise circuit/math/medical/chemical diagram."
                )
                art = imagegen.generate(prompt, size="1024x768")
                asset_dir = out / "assets"
                asset_dir.mkdir(parents=True, exist_ok=True)
                dst = asset_dir / f"ai_sec_{index}.png"
                shutil.copyfile(art["path"], dst)
                after = next((b for b in candidate.blocks if b.kind != BlockKind.FIGURE), candidate.blocks[0])
                candidate.blocks.append(LectureBlock(
                    id=f"ai-fig-{candidate.id}-{index}", kind=BlockKind.FIGURE, text="", source_refs=[],
                    figure=FigureRef(
                        image_id=f"ai-{candidate.id}-{index}",
                        caption="AI 概念示意图（辅助理解，非资料图、非精确知识图）",
                        source=SourceRef(material=ledger.material, page_start=pages[0], page_end=pages[0]),
                        after_block_id=after.id, asset_path=f"assets/ai_sec_{index}.png",
                        origin="schematic",
                        source_note="按小节主题生成的装饰示意图；不含文字/数值，不承担知识表达，不能当作精确题图。",
                    ),
                ))
            except Exception:
                pass
    sections = filtered_sections
    plan = filtered_plan
    if not sections:
        _fail(out, "用户排除后没有剩余可讲内容，请放宽排除范围")
    exclusion_report = exclusions.report(
        active_specs,
        ambiguous=parsed_exclusions.get("ambiguous") or [],
        removed_blocks=removed_blocks_total,
    )
    exclusion_report["pending_confirmation"] = pending_specs
    exclusion_report["ignored"] = parsed_exclusions.get("ignored") or []
    try:
        (out / "exclusion_report.json").write_text(
            json.dumps(exclusion_report, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    if gen_lang == "hant":
        _hant_sections(sections)
    if progress:
        progress(87, "根据考点整理章节标题与目录")
    try:
        new_titles = author_section_titles(
            client, chapter_title=chapter_title, sections=sections,
            requirements=requirements, gen_lang=gen_lang,
        )
        if new_titles:
            for sec, section_title in zip(sections, new_titles):
                sec.title = section_title
    except Exception:
        pass
    _dedupe_titles(sections, gen_lang)
    try:
        meta = author_section_meta(client, chapter_title=chapter_title, sections=sections, gen_lang=gen_lang)
        if meta:
            for sec, item in zip(sections, meta):
                sec.objectives = item["objectives"]
                sec.key_terms = item["key_terms"]
                sec.self_test = item.get("self_test") or []
                sec.visual_hint = item.get("visual_hint") or "none"
    except Exception:
        pass
    _fallback_section_meta(sections, gen_lang)
    _clamp_page_refs(sections, page_count)
    if gen_lang == "hant":
        _hant_sections(sections)

    if illustrations:
        for index, sec in enumerate(sections, start=1):
            if sec.visual_hint == "concept" and not any(b.kind == BlockKind.FIGURE for b in sec.blocks):
                _add_ai_figure(sec, ledger=ledger, out=out, index=index)

    # 用户要求已由需求理解 Agent 结构化并进入每一段 prompt；
    # 不再用字符串包含做“重点是否原样出现”的硬校验。
    _stage(out, "render_start")
    if progress:
        progress(88, "装配讲义 / 跑 Gate / 生成 PDF")
    (out / "sections.json").write_text(
        json.dumps([s.model_dump(mode="json") for s in sections], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    covered_pages = sorted({p for _, ps in plan for p in ps if 1 <= p <= page_count})
    normalize_lecture_sections(sections, gen_lang)
    try:
        from tfv2.authoring.normalize import dedupe_section_sentences, sanitize_section_math
        for _sec in sections:
            sanitize_section_math(_sec)
            dedupe_section_sentences(_sec)
    except Exception:
        pass
    # 依据不足的节：一次有界重写（只在该节块数够、支持率低时触发，控制成本）
    grounding_retries: list[dict] = []
    try:
        from tfv2.quality import metrics as _qm

        def _support_of(sec) -> dict:
            blocks = [{"id": b.id, "kind": b.kind.value if hasattr(b.kind, "value") else str(b.kind),
                       "text": b.text,
                       "source_refs": [{"page_start": r.page_start, "page_end": r.page_end}
                                       for r in sec.source_refs]} for b in sec.blocks]
            return _qm.citation_support(blocks, lambda p: page_text_by_no.get(p, ""))

        for idx, sec in enumerate(list(sections)):
            sup = _support_of(sec)
            if not sup.get("checked") or sup["checked"] < 3 or sup["ratio"] >= 0.7:
                continue
            # 必须用本节的计划页（不是模型自报的出处）：重写稿常常只引一两页，
            # 用自报页会把这一节的覆盖范围越改越小。
            pages = sorted(set(plan[idx][1])) if idx < len(plan) else sorted(
                {p for r in sec.source_refs for p in range(r.page_start, r.page_end + 1)})
            if not pages:
                continue
            try:
                better = author_section(
                    client, ledger, chapter_title=chapter_title, section_title=sec.title,
                    pages=pages, target_score=target_score, days_left=days_left,
                    foundation=foundation, persona=persona,
                    extra_note=(req_prompt + "\n上一次写作里有些说法在引用页找不到依据。"
                                "请只写资料页里明确讲到的内容，每个结论都要能在引用页找到出处；不要补充资料外的推断。"),
                    gen_lang=gen_lang, clamp_pages=True,
                )
                sanitize_section_math(better)
                dedupe_section_sentences(better)
                new_sup = _support_of(better)
                if (new_sup.get("ratio") or 0) > sup["ratio"]:
                    # 重写稿不能丢页：并回原小节出处，再把缺的页补成资料原文
                    for pno in pages:
                        ref = SourceRef(material=ledger.material, page_start=pno, page_end=pno)
                        if ref not in better.source_refs:
                            better.source_refs.append(ref)
                    _fill_missing_pages(better, pages, page_by_no, ledger, idx + 1)
                    sections[idx] = better
                    grounding_retries.append({"index": idx + 1, "before": sup["ratio"],
                                              "after": new_sup.get("ratio")})
            except Exception:
                continue
    except Exception:
        pass
    _attach_evidence_quotes(sections, page_by_no)
    # 最后再收口一次：证据引用等后续步骤可能又引入 TeX
    try:
        for _sec in sections:
            sanitize_section_math(_sec)
            dedupe_section_sentences(_sec)
    except Exception:
        pass
    # normalize() can sanitize escaped line breaks and recap titles; persist the
    # final section model so build_project reads exactly what will be rendered.
    (out / "sections.json").write_text(
        json.dumps([s.model_dump(mode="json") for s in sections], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    kmap = _make_knowledge_map(title, sections, out, gen_lang)
    if kmap and sections:
        try:
            from tfv2.domain.lecture import FigureRef
            cap = "章知识地图（系统根据本讲义目录生成，非资料原图）" if gen_lang != "en" else "Chapter knowledge map (generated from this outline; not a source figure)"
            sections[0].blocks.insert(0, LectureBlock(
                id=f"generated-map-{aid}", kind=BlockKind.FIGURE, text="", source_refs=[],
                figure=FigureRef(
                    image_id=f"generated-map-{aid}", caption=cap,
                    source=SourceRef(material=copied.name, page_start=1, page_end=1),
                    after_block_id=f"generated-map-{aid}", asset_path="assets/generated_knowledge_map.png",
                    origin="schematic",
                    source_note="由讲义目录自动绘制的章节结构图；用于导航，不冒充资料原图。",
                ),
            ))
        except Exception:
            pass
    coverage_percent = round(100 * len(covered_pages) / max(1, page_count), 1)
    header = LectureHeader(
        title=title, course=course,
        section_label=("Full material (" + str(page_count) + " pages)") if gen_lang == "en" else _tr(f"全量（{page_count} 页）", gen_lang),
        materials=[], target_score=target_score, days_left=days_left,
        foundation=({"基础较弱": "Weak foundation", "基础一般": "Average foundation", "基础较好": "Strong foundation"}.get(foundation, foundation) if gen_lang == "en" else foundation), persona=persona,
        coverage_scope=("Pages " + str(page_count)) if gen_lang == "en" else _tr(f"{page_count} 页", gen_lang),
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )
    focus = requirement_focus(requirements)
    wrap = author_wrapup(
        client, title=title, course=course, sections=sections, persona=persona,
        foundation=foundation, target_score=target_score, days_left=days_left, gen_lang=gen_lang,
    )
    fallback = fallback_wrapup(sections, title, persona, gen_lang)
    def _clean_points(items):
        out = []
        for raw in items or []:
            text = str(raw or "").strip().lstrip("-•· ").strip()
            text = text.replace("…", "").replace("...", "").strip(" ，,。；;：:")
            text = re.sub(r"^\d+[.、]\s*", "", text)
            if 3 <= len(text) <= 28 and text not in out:
                out.append(text)
        return out[:8]
    overview = (wrap.overview or fallback.overview).strip()
    overview = re.sub(r"[；;]\s*$", "", overview)
    points = _clean_points(wrap.knowledge_map) or fallback.knowledge_map
    closing_text = (wrap.closing or fallback.closing).strip()
    if len(closing_text) < 300 or len(re.findall(r"[。.!！?？]", closing_text)) < 5:
        closing_text = fallback.closing
    if gen_lang == "en":
        summary = LectureSummary(overview=overview[:1800], knowledge_map=points,
                                 exam_focus=focus,
                                 how_to_use="Read the summary and contents, then each section: intuition → example → practice. Check the source page when a step is unclear.")
    else:
        summary = LectureSummary(
            overview=_tr(overview[:1800], gen_lang),
            knowledge_map=[_tr(x, gen_lang) for x in points],
            exam_focus=focus,
            how_to_use=_tr("先读摘要和目录，再按节读；每节先看直观解释，再跟例题做一遍；最后用练习/错题本检查是否真的会做。", gen_lang),
        )
    closing = LectureClosing(
        persona=persona,
        text=closing_text,
    )
    footer = LectureFooter(
        agent_name="TermFinale", coverage_percent=coverage_percent, material_label=copied.name,
        disclaimer=("For study reference only; always check the original material. This material assumes no legal liability."
                    if gen_lang == "en" else _tr("具体请以实际资料为准，本资料不承担由此产生的法律责任。", gen_lang)),
    )
    project = {
        "id": aid, "chapter_title": chapter_title, "header": header.model_dump(mode="json"),
        "summary": summary.model_dump(mode="json"), "closing": closing.model_dump(mode="json"),
        "footer": footer.model_dump(mode="json"), "sections_files": ["sections.json"],
        "page_count": page_count, "coverage_percent": coverage_percent,
        "scope_pages": covered_pages,
        "overview_pages": [],
        "constraints": {"key_points": key_points, "excluded": excluded, "custom_prompt": custom_prompt,
                         "requirements": requirements, "exclusions": exclusion_report},
        "source_file": build_source, "assets_dir": "source_assets",
        "structure_file": "structure/structure.json",
        "out_dir": ".", "language_policy": LanguagePolicy(
            ui_lang="zh", gen_lang=GEN_LANG_LABEL.get(gen_lang, "简体中文"),
            source_lang=None, translation_mode="none",
        ).model_dump(mode="json"),
    }
    if gen_lang == "hant":
        try:
            from opencc import OpenCC
            cc = OpenCC("s2twp")
            project["chapter_title"] = cc.convert(project.get("chapter_title") or "")
            for key in ("course", "section_label", "coverage_scope", "foundation", "persona"):
                if project["header"].get(key):
                    project["header"][key] = cc.convert(project["header"][key])
            for key in ("materials",):
                if isinstance(project["header"].get(key), list):
                    project["header"][key] = [cc.convert(x) for x in project["header"][key]]
            for key in ("overview", "how_to_use", "exam_focus"):
                val = project["summary"].get(key)
                if isinstance(val, str):
                    project["summary"][key] = cc.convert(val)
                elif isinstance(val, list):
                    project["summary"][key] = [cc.convert(x) for x in val]
            project["closing"]["text"] = cc.convert(project["closing"].get("text") or "")
            project["footer"]["disclaimer"] = cc.convert(project["footer"].get("disclaimer") or "")
            project["footer"]["material_label"] = cc.convert(project["footer"].get("material_label") or "")
        except Exception:
            pass
    if grounding_retries:
        project["grounding_retries"] = grounding_retries
    if page_fill_stats:
        # 模型漏页、用资料原文补的比例：这是“为什么失败”的数据，不是失败原因文案。
        filled_total = sum(len(v["filled"]) for v in page_fill_stats.values())
        project["page_fill"] = [page_fill_stats[k] for k in sorted(page_fill_stats)]
        project["page_fill_pages"] = filled_total
        project["page_fill_ratio"] = round(filled_total / max(1, len(covered_pages or [])), 3)
    if fallback_sections:
        # 哪些节是“原文页兜底”的，必须能查得到，不能混成正常成文。
        project["fallback_sections"] = [fallback_sections[k] for k in sorted(fallback_sections)]
        try:
            (out / "fallback_sections.json").write_text(
                json.dumps({"sections": project["fallback_sections"]}, ensure_ascii=False, indent=2),
                encoding="utf-8")
        except Exception:
            pass
    (out / "project.json").write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        build_project(out / "project.json", pdf=True)
    except Exception:
        raise
    # 简洁初稿后自动逐点补讲（只对短资料；失败不影响交付）
    try:
        _auto = os.getenv("TERMFINALE_AUTO_TOPUP", "1").strip() not in ("0", "false", "no")
        man = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
        if _auto and page_count <= 12 and (man.get("gate") or {}).get("passed") and not (out / "coverage_audit.json").is_file():
            from tfv2.product.topup import topup_artifact
            _stage(out, "topup_start")
            if progress:
                progress(94, "逐点补讲（把漏掉的知识点补上）")
            topup_artifact(aid, artifact_path=out)
            _stage(out, "topup_ready")
    except Exception as exc:  # noqa: BLE001
        try:
            _stage(out, f"topup_skipped:{type(exc).__name__}")
        except Exception:
            pass
    except Exception as exc:
        draft = _deliver_draft(out, aid, title=title, page_count=page_count,
                               sections=sections, error=f"Gate/PDF 未通过：{exc}")
        if draft is not None:
            if progress:
                progress(100, "已生成带警告草稿：Gate/PDF 未完全通过")
            return draft
        shutil.rmtree(out, ignore_errors=True)
        raise GenerateError(f"Gate/PDF 未通过，且无法生成可读草稿：{exc}") from exc
    try:
        from tfv2.quality import padding, trust
        payload = [x.model_dump(mode="json") for x in sections]
        evidence = trust.audit_evidence(payload, page_text_by_no)
        semantic = trust.audit_coverage(payload, page_count, page_text_by_no)
        pad = padding.audit_lecture(payload)
        (out / "padding_report.json").write_text(json.dumps(pad, ensure_ascii=False, indent=2), encoding="utf-8")
        (out / "trust_report.json").write_text(json.dumps({
            "evidence": evidence, "coverage": semantic,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        manifest_path = out / "manifest.json"
        if manifest_path.is_file():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["trust"] = {
                "evidence_passed": evidence.get("passed"),
                "verified_ratio": evidence.get("verified_ratio"),
                "page_ratio": semantic.get("page_ratio"),
                "semantic_ratio": semantic.get("semantic_ratio"),
            }
            manifest["padding"] = {
                "passed": pad.get("passed"),
                "sections_with_issues": pad.get("sections_with_issues"),
                "issues": pad.get("issues", [])[:20],
            }
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    try:
        from tfv2.product import coverage
        page_ledger = coverage.scan_pdf(ledger_source)
        lecture_doc = {"kind": "lecture",
                       "content": {"sections": [s.model_dump(mode="json") for s in sections]}}
        module = coverage.module_coverage(lecture_doc, page_count)
        coverage.write_report(out, page_ledger, [module])
    except Exception:
        pass
    if progress:
        progress(100, "完成：Gate 通过，等待逐页复核")
    view = service.get_artifact(aid)
    return {"id": aid, "artifact": view, "pages": page_count, "sections": len(sections),
            "outline_used": outline_used, "coverage_percent": coverage_percent}

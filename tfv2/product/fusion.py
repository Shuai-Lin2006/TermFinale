"""多资料自然融合：统一主题与章节、章级过渡、同名概念去重、保留各自出处。

与“合订本”不同，这里不按资料顺序拼页，而是：

1. 先把每份资料切成真实章节（有标题就用标题，没有就按页段），
2. 再按章节主题把不同资料的同一主题合成一章（统一章节），
3. 章内跨资料时写一句过渡，并落在该资料那一页上（章级过渡），
4. 同名内容只有第一次出现时保留正文，后出现的近似段落在提纯后再对照（去重），
5. 每个 block 都带 (资料名, 原资料页码) 的出处，页码不因裁切而失真，
6. 失败有原因：每一节的成文方式（authoring / digest）和失败原因写进 fusion_report.json，
   任何一节被降级都必须在报告里能找到原因，不静默。
"""
from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pymupdf

from tfv2.authoring.normalize import correct_block_kinds, sanitize_math
from tfv2.build import build_project
from tfv2.domain.lecture import (
    BlockKind,
    LanguagePolicy,
    LectureBlock,
    LectureClosing,
    LectureFooter,
    LectureHeader,
    LectureSection,
    LectureSummary,
    SourceRef,
)
from tfv2.domain.page import Page, PageLedger, PageQuality
from tfv2.domain.page_unit import build_page_unit, clean_text
from tfv2.product import service


# ---------------------------------------------------------------- 基础结构


@dataclass
class MaterialSpan:
    """一章里属于某一份资料的一段页。"""

    artifact_id: str
    label: str
    pages: list[int]              # artifact 页码空间
    source_pages: list[int]       # 原始资料页码

    def global_pages(self, offsets: dict[str, int]) -> list[int]:
        off = offsets.get(self.artifact_id, 0)
        return [off + p for p in self.pages]


@dataclass
class Chapter:
    """融合后的一章：可能来自多份资料。"""

    title: str
    spans: list[MaterialSpan] = field(default_factory=list)
    key: str = ""
    deduped: list[dict] = field(default_factory=list)
    # 标题是“第 a–b 页（原文页段）”这类结构性兜底时，不能按标题跨资料合并：
    # 两份扫描件都有“第 1–6 页”，那是页码不是主题。
    structural: bool = False

    @property
    def materials(self) -> list[str]:
        out: list[str] = []
        for s in self.spans:
            if s.label not in out:
                out.append(s.label)
        return out


@dataclass
class Material:
    artifact_id: str
    label: str
    pages: list[int]
    rows: list[dict]
    headings: list[dict] = field(default_factory=list)

    @property
    def source_pages(self) -> list[int]:
        return [int(r.get("source_page") or r.get("page") or 0) for r in self.rows]

    def page_of(self, local_page: int) -> int:
        for row in self.rows:
            if int(row.get("page") or 0) == int(local_page):
                return int(row.get("source_page") or local_page)
        return int(local_page)


# ---------------------------------------------------------------- 标题与章节


_CHAPTER_RE = re.compile(r"^第\s*([一二三四五六七八九十百零\d]+)\s*([章节篇])\s*(.+)$")
# OCR 出来的节标题经常没有空格："1.3.4三极管的特性曲线"。
_SECTION_RE = re.compile(r"^(\d+(?:\.\d+){1,3})\s*([^\d\s].{0,38})$")
_FORMULAISH = re.compile(r"[=≈≤≥<>∫∑√±×÷∆△/%]|。|，|；|,|;")
_HEAD_RE = re.compile(r"^([一二三四五六七八九十]+)\s*[、.]\s*(.+)$")
_GENERIC_SUFFIX = ("概述", "简介", "总述", "小结", "总结", "引入", "导引", "习题", "复习")
_GENERIC_TITLES = {"概述", "绪论", "引言", "前言", "简介", "导论", "总论", "本章小结", "总结"}
_CN_DIGITS = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


def _cn_number(raw: str) -> int | None:
    if raw.isdigit():
        return int(raw)
    if raw == "十":
        return 10
    m = re.fullmatch(r"([一二三四五六七八九]?)十([一二三四五六七八九]?)", raw)
    if m:
        return _CN_DIGITS.get(m.group(1), 1) * 10 + _CN_DIGITS.get(m.group(2), 0)
    if raw in _CN_DIGITS:
        return _CN_DIGITS[raw]
    return None


def norm_title(text: str) -> str:
    """章节标题归一：去掉编号、序号、标点和空白，用来判断“是不是同一章”。"""
    t = str(text or "").strip()
    t = _CHAPTER_RE.sub(r"\3", t)
    t = re.sub(r"^\d+(?:\.\d+)*\s*", "", t)
    t = re.sub(r"^[一二三四五六七八九十]+\s*[、.]\s*", "", t)
    t = re.sub(r"[（(]\s*续\s*[)）]|续$", "", t)
    t = re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", t).lower()
    return t


def parse_order(title: str) -> tuple[int, int]:
    """返回 (章号, 节号) 用于排序；没有编号的排到最后。"""
    t = str(title or "")
    m = _CHAPTER_RE.match(t)
    if m:
        n = _cn_number(m.group(1))
        return (n if n is not None else 9998, 0)
    m = _SECTION_RE.match(t)
    if m:
        parts = [int(x) for x in m.group(1).split(".")]
        return (parts[0], parts[1] if len(parts) > 1 else 0)
    return (9999, 0)


def _looks_like_heading(line: str) -> bool:
    if not line or len(line) > 42:
        return False
    if _CHAPTER_RE.match(line) or _HEAD_RE.match(line):
        return True
    m = _SECTION_RE.match(line)
    if not m:
        return False
    if _FORMULAISH.search(line):
        return False
    title = clean_text(m.group(2))
    if len(title) < 2:
        return False
    # OCR 里 “0.1 mA” “1.5 V” 这种单位/数值行不是标题：标题要么有中文，要么足够长。
    if not re.search(r"[\u4e00-\u9fff]", title) and len(title) < 8:
        return False
    return True


def _heading_of_page(text: str) -> str:
    for raw in (text or "").splitlines():
        line = raw.strip()
        if _looks_like_heading(line):
            return clean_text(line)
    return ""


def chapters_of_material(material: Material, *, chunk: int = 8) -> list[Chapter]:
    """把一份资料切成章节；用真实标题，标题缺失时按页段兜底。"""
    ordered = sorted(material.rows, key=lambda r: int(r.get("page") or 0))
    if not ordered:
        return []
    starts: list[tuple[int, str]] = []
    # 优先用 MinerU 解析出的真实标题（扫描件/教材都能拿到层级），没有再用正则猜。
    if material.headings:
        seen_pages: set[int] = set()
        for h in material.headings:
            page = int(h.get("page") or 0)
            if page < 1 or page in seen_pages:
                continue
            if page not in {int(r.get("page") or 0) for r in ordered}:
                continue
            starts.append((page, str(h.get("text") or "")))
            seen_pages.add(page)
    if not starts:
        for row in ordered:
            title = _heading_of_page(str(row.get("text") or ""))
            if title:
                starts.append((int(row.get("page") or 0), title))
    chapters: list[Chapter] = []
    if not starts:
        # 没有可识别标题：按页段兜底，标题必须暴露“这是页段”，不能伪装成知识点。
        for i in range(0, len(ordered), chunk):
            group = ordered[i:i + chunk]
            first = int(group[0].get("page") or 1)
            last = int(group[-1].get("page") or first)
            span = MaterialSpan(
                artifact_id=material.artifact_id, label=material.label,
                pages=[int(r.get("page")) for r in group],
                source_pages=[int(r.get("source_page") or r.get("page")) for r in group],
            )
            title = (f"第 {span.source_pages[0]} 页起（原文页段）" if first == last
                     else f"第 {span.source_pages[0]}–{span.source_pages[-1]} 页（原文页段）")
            chapters.append(Chapter(title=title, key=f"pagerange-{material.artifact_id}-{first}",
                                    spans=[span], structural=True))
        return chapters

    first_page = int(ordered[0].get("page") or 1)
    head_pages: list[dict] = []
    if starts[0][0] > first_page:
        head_pages = [r for r in ordered if int(r.get("page")) < starts[0][0]]
    groups: list[tuple[str, list[dict]]] = []
    if head_pages:
        groups.append((f"开篇（第 {int(head_pages[0].get('page'))} 页起）", head_pages))
    bounds = [s[0] for s in starts] + [10 ** 9]
    for idx, (start_page, title) in enumerate(starts):
        hi = bounds[idx + 1]
        pages = [r for r in ordered if start_page <= int(r.get("page")) < hi]
        groups.append((title, pages))
    seen: set[str] = set()
    for title, rows in groups:
        if not rows:
            continue
        span = MaterialSpan(
            artifact_id=material.artifact_id, label=material.label,
            pages=[int(r.get("page")) for r in rows],
            source_pages=[int(r.get("source_page") or r.get("page")) for r in rows],
        )
        key = norm_title(title) or f"seg-{span.pages[0]}"
        # 同一份资料里重复出现的标题必须分开，不能靠 key 覆盖掉页。
        if key in seen:
            key = f"{key}-{span.pages[0]}"
        seen.add(key)
        chapters.append(Chapter(title=title, key=key, spans=[span]))
    return chapters


def _compatible(a: Chapter, b: Chapter) -> bool:
    """两章能否合成一章（同名/同编号/主题词相同/原标题是泛称后缀）。"""
    if a.structural or b.structural:
        return bool(a.key) and a.key == b.key and a.spans[0].artifact_id == b.spans[0].artifact_id
    if a.key and a.key == b.key:
        return True
    na, nb = norm_title(a.title), norm_title(b.title)
    if not na or not nb:
        return False
    if na == nb:
        return True
    short, long_ = (na, nb) if len(na) <= len(nb) else (nb, na)
    if len(short) >= 2 and long_.startswith(short):
        rest = long_[len(short):]
        if rest in _GENERIC_SUFFIX or any(rest.startswith(x) for x in _GENERIC_SUFFIX):
            return True
    # 编号相同只说明层级对得上，还得看主题是不是同一件事：
    # “第一章 极限”与“第一章 线性空间”必须分开，不能按章号硬合。
    oa, ob = parse_order(a.title), parse_order(b.title)
    if oa[0] < 9999 and oa[0] == ob[0] and oa[1] == ob[1]:
        if similarity(a.title, b.title) >= 0.5:
            return True
        # 只有“概述/绪论”这类没有主题信息的标题，才允许仅凭章号合并。
        if na in _GENERIC_TITLES or nb in _GENERIC_TITLES:
            return True
    return False


def _short_label(label: str, limit: int = 18) -> str:
    stem = Path(label).stem
    return stem if len(stem) <= limit else stem[:limit] + "…"


def unique_titles(chapters: list[Chapter]) -> list[Chapter]:
    """同一份讲义里不允许两节同名。

    重名说明这两章确实不是同一主题（否则早被 fuse_chapters 合并了），
    所以两边都要带上资料名/页段，而不是给后一个加 (2)。
    """
    counts: dict[str, int] = {}
    for ch in chapters:
        key = norm_title(ch.title) or ch.title.strip()
        counts[key] = counts.get(key, 0) + 1
    seen: set[str] = set()
    for ch in chapters:
        base = ch.title.strip() or "本节"
        key = norm_title(base) or base
        if counts.get(key, 1) <= 1 and key not in seen:
            ch.title = base
            seen.add(key)
            continue
        span = ch.spans[0] if ch.spans else None
        label = _short_label(span.label) if span else ""
        pages = ""
        if span is not None and span.source_pages:
            pages = (f"第 {span.source_pages[0]} 页" if len(span.source_pages) == 1
                     else f"第 {span.source_pages[0]}–{span.source_pages[-1]} 页")
        suffix = "，".join(x for x in (label, pages) if x)
        candidate = f"{base}（{suffix}）" if suffix else f"{base}（{len(chapters)}）"
        n = 2
        while norm_title(candidate) in seen:
            candidate = f"{base}（{suffix} #{n}）" if suffix else f"{base}（{n}）"
            n += 1
        ch.title = candidate
        seen.add(norm_title(candidate))
    return chapters


def fuse_chapters(per_material: list[list[Chapter]]) -> list[Chapter]:
    """把各资料的章节合成统一章节表：同主题合并，其余保持资料顺序。"""
    fused: list[Chapter] = []
    for chapters in per_material:
        for ch in chapters:
            target = None
            for cand in fused:
                if _compatible(cand, ch):
                    target = cand
                    break
            if target is None:
                fused.append(Chapter(title=ch.title, key=ch.key, spans=list(ch.spans),
                                     structural=ch.structural))
            else:
                target.spans.extend(ch.spans)
                # 合并后标题取更具体的那个（更长的），避免统一成泛称。
                if len(ch.title) > len(target.title):
                    target.title = ch.title
    return fused


# ---------------------------------------------------------------- 去重


def _tokens(text: str) -> set[str]:
    cleaned = re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", clean_text(text or "")).lower()
    if len(cleaned) < 3:
        return {cleaned} if cleaned else set()
    return {cleaned[i:i + 2] for i in range(0, len(cleaned) - 1)}


def similarity(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


DUPLICATE_THRESHOLD = 0.82
DUPLICATE_MIN_CHARS = 120


class DedupeRegistry:
    """一次融合任务内的去重登记表。

    必须是实例级的：并发跑两份融合时，模块级共享表会把 A 资料的内容判成 B 资料的重复。
    """

    def __init__(self) -> None:
        self.rows: list[dict] = []

    def register(self, text: str, chapter_title: str, page: int) -> None:
        self.rows.append({"text": text, "chapter": chapter_title, "page": page})

    def find(self, text: str, threshold: float = DUPLICATE_THRESHOLD) -> dict | None:
        if len(clean_text(text)) < DUPLICATE_MIN_CHARS:
            return None
        best = None
        for row in self.rows:
            score = similarity(text, row["text"])
            if score >= threshold and (best is None or score > best["similarity"]):
                best = {"chapter": row["chapter"], "page": row["page"], "similarity": round(score, 3)}
        return best


_DEFAULT_REGISTRY = DedupeRegistry()   # 只为单测和一次性脚本保留


def reset_registry() -> None:
    _DEFAULT_REGISTRY.rows.clear()


def register_text(text: str, chapter_title: str, page: int) -> None:
    _DEFAULT_REGISTRY.register(text, chapter_title, page)


def find_duplicate(text: str, threshold: float = DUPLICATE_THRESHOLD) -> dict | None:
    return _DEFAULT_REGISTRY.find(text, threshold)


# ---------------------------------------------------------------- 页宇宙


@dataclass
class Universe:
    ledger: PageLedger
    materials: list[Material]
    offsets: dict[str, int]          # artifact_id -> 全局页偏移
    origin: list[dict]               # 全局页 -> {artifact_id,label,local_page,source_page}
    pdf: Path

    @property
    def page_count(self) -> int:
        return self.ledger.page_count

    def origin_of(self, global_page: int) -> dict:
        return self.origin[global_page - 1]


def _read_material(artifact_id: str, pages: list[int] | None, label: str = "") -> Material:
    path = service.artifact_path(artifact_id)
    if path is None:
        raise FileNotFoundError(f"资料不存在：{artifact_id}")
    raw = json.loads((path / "source_pages.json").read_text(encoding="utf-8"))
    all_rows = raw.get("pages") or raw
    if not all_rows:
        raise ValueError(f"资料没有页内容：{artifact_id}")
    chosen = sorted({int(p) for p in (pages or []) if 1 <= int(p) <= len(all_rows)})
    if not chosen:
        raise ValueError(f"{artifact_id}：没有有效页码")
    rows = []
    for p in chosen:
        row = dict(all_rows[p - 1])
        row["page"] = p
        row["source_page"] = int(all_rows[p - 1].get("source_page") or p)
        row["text"] = str(row.get("text") or "")
        rows.append(row)
    name = label or str(raw.get("origin_material") or raw.get("material") or artifact_id)
    from tfv2.product import headings as headings_mod
    heads = headings_mod.normalize_headings(headings_mod.load_headings(path))
    return Material(artifact_id=artifact_id, label=name, pages=chosen, rows=rows, headings=heads)


def build_universe(materials: list[dict], out: Path) -> Universe:
    """按用户给定顺序把资料排成一条全局页轴（页不重排，重排的是章节）。"""
    loaded = [_read_material(str(m["artifact_id"]), m.get("pages"), str(m.get("label") or "")) for m in materials]
    # 两份资料可能是同一本书的不同范围，展示名会重名；出处必须能区分是谁。
    seen: dict[str, int] = {}
    for mat in loaded:
        if mat.label in seen:
            seen[mat.label] += 1
            mat.label = f"{mat.label}（第 {seen[mat.label]} 份）"
        else:
            seen[mat.label] = 1
    offsets: dict[str, int] = {}
    origin: list[dict] = []
    page_rows: list[dict] = []
    combined = pymupdf.open()
    cursor = 0
    try:
        for mat in loaded:
            base = service.artifact_path(mat.artifact_id)
            src_pdf = next((p for p in (base / "source").glob("*.pdf")), None) if base else None
            doc = pymupdf.open(str(src_pdf)) if src_pdf else None
            offsets[mat.artifact_id] = cursor
            try:
                for row in mat.rows:
                    local = int(row["page"])
                    cursor += 1
                    origin.append({"artifact_id": mat.artifact_id, "label": mat.label,
                                   "local_page": local, "source_page": int(row["source_page"]),
                                   "global_page": cursor})
                    page_rows.append(row)
                    if doc is not None:
                        combined.insert_pdf(doc, from_page=local - 1, to_page=local - 1)
            finally:
                if doc is not None:
                    doc.close()
        if len(combined) != cursor:
            raise ValueError("资料缺少可用的 PDF 源页，无法建立统一页轴")
        out.mkdir(parents=True, exist_ok=True)
        (out / "source").mkdir(exist_ok=True)
        pdf = out / "source" / "fused.pdf"
        combined.save(str(pdf))
    finally:
        combined.close()

    pages = []
    for item, row in zip(origin, page_rows):
        text = clean_text(str(row.get("text") or ""))
        quality = PageQuality.OCR if text else PageQuality.IMAGE_ONLY
        pages.append(Page(material="fused", page_no=item["global_page"], text=text, quality=quality))
    ledger = PageLedger(material="fused", page_count=len(pages), pages=pages,
                        source_hash="fusion-" + str(len(pages)), parser_version="fusion-1")
    return Universe(ledger=ledger, materials=loaded, offsets=offsets, origin=origin, pdf=pdf)


# ---------------------------------------------------------------- 出处重映射


def _remap_ref(ref: SourceRef, universe: Universe) -> list[SourceRef]:
    """把全局页 ref 拆成“每份资料一段”，并带上原资料页码。"""
    pages = list(range(ref.page_start, (ref.page_end or ref.page_start) + 1))
    out: list[SourceRef] = []
    for page in pages:
        if not (1 <= page <= universe.page_count):
            continue
        item = universe.origin_of(page)
        if out and out[-1].material == item["label"] and \
                (out[-1].page_end or out[-1].page_start) == page - 1 and \
                (out[-1].source_page or 0) + (page - out[-1].page_start) == item["source_page"]:
            out[-1] = out[-1].model_copy(update={"page_end": page})
            continue
        out.append(SourceRef(material=item["label"], page_start=page, page_end=page,
                             source_page=int(item["source_page"])))
    return out


def remap_section(section: LectureSection, universe: Universe) -> LectureSection:
    blocks = []
    for block in section.blocks:
        refs: list[SourceRef] = []
        for ref in block.source_refs:
            refs.extend(_remap_ref(ref, universe))
        fig = block.figure
        if fig is not None:
            mapped = _remap_ref(fig.source, universe)
            if mapped:
                fig = fig.model_copy(update={"source": mapped[0]})
        blocks.append(block.model_copy(update={"source_refs": refs, "figure": fig}))
    sec_refs: list[SourceRef] = []
    for ref in section.source_refs or []:
        sec_refs.extend(_remap_ref(ref, universe))
    return section.model_copy(update={"blocks": blocks, "source_refs": sec_refs})


# ---------------------------------------------------------------- 明细分节（不靠模型）


def _page_png(universe: Universe, global_page: int, assets_dir: Path) -> Path | None:
    """把原文页渲染成图片：扫描件/公式页宁可放原页影像，也不硬转乱码。"""
    try:
        doc = pymupdf.open(str(universe.pdf))
    except Exception:
        return None
    try:
        if not (1 <= global_page <= len(doc)):
            return None
        assets_dir.mkdir(parents=True, exist_ok=True)
        target = assets_dir / f"page_{global_page:04d}.png"
        doc[global_page - 1].get_pixmap(dpi=120).save(str(target))
        return target
    except Exception:
        return None
    finally:
        doc.close()


def digest_section(chapter: Chapter, universe: Universe, *, index: int,
                   assets_dir: Path | None = None,
                   registry: "DedupeRegistry | None" = None) -> LectureSection:
    reg = registry or _DEFAULT_REGISTRY
    """按章把原文页组织成正文：每页一个块，出处带原资料页码。

    这是确定性路径：文字全部来自资料原文，不做改写，也不假装是讲稿。
    图/公式/扫描页放原页影像，避免公式被转成乱码，也避免整页丢失。
    """
    blocks: list[LectureBlock] = []
    used_pages: list[int] = []
    previous_label = ""
    for span in chapter.spans:
        off = universe.offsets.get(span.artifact_id, 0)
        for local, source_page in zip(span.pages, span.source_pages):
            global_page = off + int(local)
            row = next((o for o in universe.origin if o["global_page"] == global_page), None)
            text = universe.ledger.pages[global_page - 1].text or ""
            if row is None:
                continue
            unit = build_page_unit(global_page, text)
            ref = SourceRef(material=span.label, page_start=global_page, page_end=global_page,
                            source_page=int(source_page))
            prefix = ""
            if previous_label and span.label != previous_label:
                # 章级过渡：只陈述导航事实，不额外断言两份资料的关系。
                prefix = f"（衔接）下面换到《{span.label}》第 {source_page} 页，继续同一主题。"
            body = clean_text(text).strip()
            if not body:
                body = f"第 {source_page} 页是扫描/图片页，原文没有可提取文字，内容以本页原页影像为准。"
            dup = reg.find(body)
            if dup is not None and unit.kind == "text":
                # 同名内容只保留一次正文；后出现的只留定位，不重复展开。
                body = f"与《{dup['chapter']}》内容重复，此处不重复展开（相似度 {dup['similarity']:g}）。"
                prefix = ""
                chapter.deduped.append({"page": global_page, "source_page": source_page,
                                        "duplicate_of": dup["chapter"], "similarity": dup["similarity"]})
            else:
                reg.register(body, chapter.title or f"第 {index} 节", global_page)
            blocks.append(LectureBlock(
                id=f"fuse-{index}-{global_page}", kind=BlockKind.PARAGRAPH,
                text=(prefix + body)[:3500], source_refs=[ref],
            ))
            if unit.kind in ("image", "formula") and assets_dir is not None:
                png = _page_png(universe, global_page, assets_dir)
                if png is not None:
                    bid = f"fuse-{index}-{global_page}-img"
                    blocks.append(LectureBlock(
                        id=bid, kind=BlockKind.FIGURE, text="",
                        source_refs=[ref],
                        figure={
                            "image_id": f"p{global_page}", "caption": f"第 {source_page} 页原页影像",
                            "source": ref, "after_block_id": bid, "asset_path": str(png),
                            "origin": "source",
                            "source_note": "扫描/公式页保留原页；文字无法可靠提取时不硬转。",
                        },
                    ))
            used_pages.append(global_page)
            previous_label = span.label
    if not blocks:
        raise ValueError(f"章节「{chapter.title}」没有可用的原文页")
    sec_refs = []
    for page in sorted(set(used_pages)):
        item = universe.origin_of(page)
        sec_refs.append(SourceRef(material=item["label"], page_start=page, page_end=page,
                                  source_page=int(item["source_page"])))
    materials = chapter.materials
    summary = ("本段把 " + "、".join(f"《{m}》" for m in materials) + " 的同一主题页放在一起，原文照录。"
               if len(materials) > 1 else "本段按资料原文页组织。")
    return LectureSection(
        id=f"fuse-{index}", title=chapter.title or f"第 {index} 节", level=2, blocks=blocks,
        source_refs=sec_refs, summary=summary,
        objectives=[f"读懂《{materials[0]}》相关页并说清要点"] if materials else [],
        key_terms=[chapter.title] if chapter.title else [],
        self_test=["合上讲义，按本章目录复述要点"], visual_hint="none",
    )


# ---------------------------------------------------------------- 成文（模型）

FUSE_NOTE = """这是多份资料融合成的一份讲义，不是合订本。本章合并了：
{spans}

要求：
- 按主题讲，不要按资料分段复述；同一概念只定义一次，后面的资料只补充它多出来的做法/例子/结论；
- 资料来源不同时，在正文里自然交代“另一种讲法/另一份资料在这里补充了什么”，不要写“第 X 份资料”这种机器编号；
- 页面上没有的内容不要补，公式用 $...$；
- 每个 block 的 source_pages 只能取上面列出的页。"""


FUSION_SUPPORT_MIN = 0.5
FUSION_TERM_MIN = 0.5


def improvement_reason(support: dict, recall: dict) -> str:
    """成文质量不达标时要重试的理由；达标返回空串。"""
    reasons: list[str] = []
    ratio = support.get("ratio")
    if ratio is not None and ratio < FUSION_SUPPORT_MIN:
        reasons.append(f"正文与引用页支持率只有 {ratio:.0%}")
    rec = recall.get("recall")
    if rec is not None and rec < FUSION_TERM_MIN:
        missing = "、".join((recall.get("missing") or [])[:6])
        reasons.append(f"漏掉资料核心术语 {rec:.0%}" + (f"（缺：{missing}）" if missing else ""))
    return "；".join(reasons)


def _score_of(section: LectureSection, chapter: Chapter, universe: Universe) -> tuple[dict, dict]:
    return measure_support(section, universe), measure_term_recall(section, chapter, universe)


def authored_section(chapter: Chapter, universe: Universe, client, *, index: int, **kwargs) -> LectureSection:
    from tfv2.authoring.lecture import author_section

    spans_text = "\n".join(
        f"- 《{s.label}》原资料第 {s.source_pages[0]}"
        + (f"–{s.source_pages[-1]}" if len(s.source_pages) > 1 else "")
        + f" 页（对应本讲义的页：{sorted(s.global_pages(universe.offsets))}）"
        for s in chapter.spans
    )
    pages = sorted({p for s in chapter.spans for p in s.global_pages(universe.offsets)})
    section = author_section(
        client, universe.ledger,
        chapter_title=chapter.title or "讲义",
        section_title=chapter.title or f"第 {index} 节",
        pages=pages,
        extra_note=FUSE_NOTE.format(spans=spans_text) + "\n" + str(kwargs.pop("extra_note", "")),
        **kwargs,
    )
    if not section.title or section.title.strip() in ("", chapter.title):
        section = section.model_copy(update={"title": chapter.title or section.title})
    return remap_section(section, universe)


def sanitize_prose(text: str) -> str:
    """摘要/结语这类“非正文块”文本里的 $...$ 也要清掉。

    它们不走块的渲染管线，留着 $ 会原样印进 PDF，被 PDF 门禁判成未渲染 LaTeX。
    """
    from tfv2.authoring.normalize import _plain_math

    body = str(text or "")
    if "$" not in body and "\\" not in body:
        return body
    return _plain_math(body)


def measure_term_recall(section: LectureSection, chapter: Chapter, universe: Universe) -> dict:
    """这一章资料里的高频术语，模型成文覆盖了多少（考点覆盖的确定性代理）。"""
    from tfv2.quality import metrics

    corpus = []
    for span in chapter.spans:
        off = universe.offsets.get(span.artifact_id, 0)
        for local in span.pages:
            page_no = off + int(local)
            if 1 <= page_no <= universe.page_count:
                corpus.append(universe.ledger.pages[page_no - 1].text or "")
    if not corpus:
        return {"terms": 0, "hit": 0, "recall": 0.0, "missing": []}
    terms = metrics.term_candidates("\n".join(corpus), top=20)
    return metrics.term_recall(terms, " ".join(b.text or "" for b in section.blocks))


def measure_support(section: LectureSection, universe: Universe) -> dict:
    """模型成文的块，引用的页到底支不支持这段话（2-gram 重合）。

    不修改正文；把数字写进融合报告，供人工复核和后续重试策略使用。
    """
    from tfv2.quality import metrics

    def _page_text(page_no: int) -> str:
        if 1 <= page_no <= universe.page_count:
            return universe.ledger.pages[page_no - 1].text or ""
        return ""

    blocks = [{"id": b.id, "kind": b.kind.value if hasattr(b.kind, "value") else str(b.kind),
               "text": b.text, "source_refs": [r.model_dump() for r in b.source_refs]}
              for b in section.blocks]
    return metrics.citation_support(blocks, _page_text)


def _normalize_math(section: LectureSection) -> LectureSection:
    """公式与 TeX 收口（与讲义生成共用同一套规则）。"""
    from tfv2.authoring.normalize import sanitize_section_math

    return sanitize_section_math(section)


def digest_section(chapter: Chapter, universe: Universe, *, index: int,
                   assets_dir: Path | None = None,
                   registry: "DedupeRegistry | None" = None) -> LectureSection:
    reg = registry or _DEFAULT_REGISTRY
    """按章把原文页组织成正文：每页一个块，出处带原资料页码。

    这是确定性路径：文字全部来自资料原文，不做改写，也不假装是讲稿。
    图/公式/扫描页放原页影像，避免公式被转成乱码，也避免整页丢失。
    """
    blocks: list[LectureBlock] = []
    used_pages: list[int] = []
    previous_label = ""
    for span in chapter.spans:
        off = universe.offsets.get(span.artifact_id, 0)
        for local, source_page in zip(span.pages, span.source_pages):
            global_page = off + int(local)
            row = next((o for o in universe.origin if o["global_page"] == global_page), None)
            text = universe.ledger.pages[global_page - 1].text or ""
            if row is None:
                continue
            unit = build_page_unit(global_page, text)
            ref = SourceRef(material=span.label, page_start=global_page, page_end=global_page,
                            source_page=int(source_page))
            prefix = ""
            if previous_label and span.label != previous_label:
                # 章级过渡：只陈述导航事实，不额外断言两份资料的关系。
                prefix = f"（衔接）下面换到《{span.label}》第 {source_page} 页，继续同一主题。"
            body = clean_text(text).strip()
            if not body:
                body = f"第 {source_page} 页是扫描/图片页，原文没有可提取文字，内容以本页原页影像为准。"
            dup = reg.find(body)
            if dup is not None and unit.kind == "text":
                # 同名内容只保留一次正文；后出现的只留定位，不重复展开。
                body = f"与《{dup['chapter']}》内容重复，此处不重复展开（相似度 {dup['similarity']:g}）。"
                prefix = ""
                chapter.deduped.append({"page": global_page, "source_page": source_page,
                                        "duplicate_of": dup["chapter"], "similarity": dup["similarity"]})
            else:
                reg.register(body, chapter.title or f"第 {index} 节", global_page)
            blocks.append(LectureBlock(
                id=f"fuse-{index}-{global_page}", kind=BlockKind.PARAGRAPH,
                text=(prefix + body)[:3500], source_refs=[ref],
            ))
            if unit.kind in ("image", "formula") and assets_dir is not None:
                png = _page_png(universe, global_page, assets_dir)
                if png is not None:
                    bid = f"fuse-{index}-{global_page}-img"
                    blocks.append(LectureBlock(
                        id=bid, kind=BlockKind.FIGURE, text="",
                        source_refs=[ref],
                        figure={
                            "image_id": f"p{global_page}", "caption": f"第 {source_page} 页原页影像",
                            "source": ref, "after_block_id": bid, "asset_path": str(png),
                            "origin": "source",
                            "source_note": "扫描/公式页保留原页；文字无法可靠提取时不硬转。",
                        },
                    ))
            used_pages.append(global_page)
            previous_label = span.label
    if not blocks:
        raise ValueError(f"章节「{chapter.title}」没有可用的原文页")
    sec_refs = []
    for page in sorted(set(used_pages)):
        item = universe.origin_of(page)
        sec_refs.append(SourceRef(material=item["label"], page_start=page, page_end=page,
                                  source_page=int(item["source_page"])))
    materials = chapter.materials
    summary = ("本段把 " + "、".join(f"《{m}》" for m in materials) + " 的同一主题页放在一起，原文照录。"
               if len(materials) > 1 else "本段按资料原文页组织。")
    return LectureSection(
        id=f"fuse-{index}", title=chapter.title or f"第 {index} 节", level=2, blocks=blocks,
        source_refs=sec_refs, summary=summary,
        objectives=[f"读懂《{materials[0]}》相关页并说清要点"] if materials else [],
        key_terms=[chapter.title] if chapter.title else [],
        self_test=["合上讲义，按本章目录复述要点"], visual_hint="none",
    )


# ---------------------------------------------------------------- 成文（模型）

FUSE_NOTE = """这是多份资料融合成的一份讲义，不是合订本。本章合并了：
{spans}

要求：
- 按主题讲，不要按资料分段复述；同一概念只定义一次，后面的资料只补充它多出来的做法/例子/结论；
- 资料来源不同时，在正文里自然交代“另一种讲法/另一份资料在这里补充了什么”，不要写“第 X 份资料”这种机器编号；
- 页面上没有的内容不要补，公式用 $...$；
- 每个 block 的 source_pages 只能取上面列出的页。"""


FUSION_SUPPORT_MIN = 0.5
FUSION_TERM_MIN = 0.5


def improvement_reason(support: dict, recall: dict) -> str:
    """成文质量不达标时要重试的理由；达标返回空串。"""
    reasons: list[str] = []
    ratio = support.get("ratio")
    if ratio is not None and ratio < FUSION_SUPPORT_MIN:
        reasons.append(f"正文与引用页支持率只有 {ratio:.0%}")
    rec = recall.get("recall")
    if rec is not None and rec < FUSION_TERM_MIN:
        missing = "、".join((recall.get("missing") or [])[:6])
        reasons.append(f"漏掉资料核心术语 {rec:.0%}" + (f"（缺：{missing}）" if missing else ""))
    return "；".join(reasons)


def _score_of(section: LectureSection, chapter: Chapter, universe: Universe) -> tuple[dict, dict]:
    return measure_support(section, universe), measure_term_recall(section, chapter, universe)


def authored_section(chapter: Chapter, universe: Universe, client, *, index: int, **kwargs) -> LectureSection:
    from tfv2.authoring.lecture import author_section

    spans_text = "\n".join(
        f"- 《{s.label}》原资料第 {s.source_pages[0]}"
        + (f"–{s.source_pages[-1]}" if len(s.source_pages) > 1 else "")
        + f" 页（对应本讲义的页：{sorted(s.global_pages(universe.offsets))}）"
        for s in chapter.spans
    )
    pages = sorted({p for s in chapter.spans for p in s.global_pages(universe.offsets)})
    section = author_section(
        client, universe.ledger,
        chapter_title=chapter.title or "讲义",
        section_title=chapter.title or f"第 {index} 节",
        pages=pages,
        extra_note=FUSE_NOTE.format(spans=spans_text) + "\n" + str(kwargs.pop("extra_note", "")),
        **kwargs,
    )
    if not section.title or section.title.strip() in ("", chapter.title):
        section = section.model_copy(update={"title": chapter.title or section.title})
    return remap_section(section, universe)


def sanitize_prose(text: str) -> str:
    """摘要/结语这类“非正文块”文本里的 $...$ 也要清掉。

    它们不走块的渲染管线，留着 $ 会原样印进 PDF，被 PDF 门禁判成未渲染 LaTeX。
    """
    from tfv2.authoring.normalize import _plain_math

    body = str(text or "")
    if "$" not in body and "\\" not in body:
        return body
    return _plain_math(body)


def measure_term_recall(section: LectureSection, chapter: Chapter, universe: Universe) -> dict:
    """这一章资料里的高频术语，模型成文覆盖了多少（考点覆盖的确定性代理）。"""
    from tfv2.quality import metrics

    corpus = []
    for span in chapter.spans:
        off = universe.offsets.get(span.artifact_id, 0)
        for local in span.pages:
            page_no = off + int(local)
            if 1 <= page_no <= universe.page_count:
                corpus.append(universe.ledger.pages[page_no - 1].text or "")
    if not corpus:
        return {"terms": 0, "hit": 0, "recall": 0.0, "missing": []}
    terms = metrics.term_candidates("\n".join(corpus), top=20)
    return metrics.term_recall(terms, " ".join(b.text or "" for b in section.blocks))


def measure_support(section: LectureSection, universe: Universe) -> dict:
    """模型成文的块，引用的页到底支不支持这段话（2-gram 重合）。

    不修改正文；把数字写进融合报告，供人工复核和后续重试策略使用。
    """
    from tfv2.quality import metrics

    def _page_text(page_no: int) -> str:
        if 1 <= page_no <= universe.page_count:
            return universe.ledger.pages[page_no - 1].text or ""
        return ""

    blocks = [{"id": b.id, "kind": b.kind.value if hasattr(b.kind, "value") else str(b.kind),
               "text": b.text, "source_refs": [r.model_dump() for r in b.source_refs]}
              for b in section.blocks]
    return metrics.citation_support(blocks, _page_text)


def _normalize_math(section: LectureSection) -> LectureSection:
    """公式块只包一层 $$。

    模型经常把“公式 + 说明”混在一个 formula 块里（写成温度系数就是 $$..$$ 即 $..$。），
    再包一层 $$ 会让 KaTeX 解析失败、把 TeX 原样漏到 PDF 里。这种混排块按段落处理，
    交给 normalize 做纯文本化；只有真正单一公式才保留 $$ 包裹。
    """
    for block in section.blocks:
        if block.kind != BlockKind.FORMULA:
            continue
        text = (block.text or "").strip()
        if not text:
            continue
        if text.startswith("$$") and text.endswith("$$") and text.count("$$") == 2:
            continue
        inner = re.sub(r"^\${1,2}\s*", "", text)
        inner = re.sub(r"\s*\${1,2}$", "", inner).strip()
        if "$" in inner:
            block.kind = BlockKind.PARAGRAPH
            block.text = inner
        else:
            block.text = "$$" + inner + "$$"
    return sanitize_math(section)


def _cited_pages(section: LectureSection) -> set[int]:
    pages: set[int] = set()
    for block in section.blocks:
        refs = list(block.source_refs)
        if block.figure is not None:
            refs.append(block.figure.source)
        for ref in refs:
            pages.update(range(ref.page_start, (ref.page_end or ref.page_start) + 1))
    return pages


def backfill_pages(section: LectureSection, chapter: Chapter, universe: Universe, *,
                   index: int) -> tuple[list[int], LectureSection]:
    """模型漏掉的页不能被静默丢掉：补一条明确的原文页块，并记进报告。

    补的是资料原文，不是编出来的讲解；读者能看出这是“原文补充”。
    """
    wanted: list[int] = []
    for span in chapter.spans:
        off = universe.offsets.get(span.artifact_id, 0)
        wanted.extend(off + int(p) for p in span.pages)
    missing = [p for p in sorted(set(wanted)) if p not in _cited_pages(section)]
    if not missing:
        return [], section
    blocks = list(section.blocks)
    refs = list(section.source_refs)
    for page in missing:
        item = universe.origin_of(page)
        text = clean_text(universe.ledger.pages[page - 1].text or "").strip()
        body = (f"原文补充：第 {item['source_page']} 页（模型正文没有覆盖本页，这里按原文补上，不做改写）："
                + (text[:1200] if text else "本页为图/表/扫描页，内容以原页影像为准。"))
        blocks.append(LectureBlock(
            id=f"fuse-{index}-backfill-{page}", kind=BlockKind.PARAGRAPH, text=body,
            source_refs=[SourceRef(material=item["label"], page_start=page, page_end=page,
                                   source_page=int(item["source_page"]))],
        ))
        refs.append(SourceRef(material=item["label"], page_start=page, page_end=page,
                              source_page=int(item["source_page"])))
    return missing, section.model_copy(update={"blocks": blocks, "source_refs": refs})


def author_with_retry(chapter: Chapter, universe: Universe, client, *, index: int,
                      gen_lang: str = "zh", author_fn=None, max_attempts: int = 2) -> dict:
    """成文一次，质量不达标最多再试一次；只有更好才采纳。

    返回 {section, backfilled, support, recall, attempts, retry_reason}；
    两次都不达标就把原因留在 retry_reason 里，不静默放过。
    """
    fn = author_fn or authored_section
    section = fn(chapter, universe, client, index=index, target_score=80, days_left=7,
                 foundation="基础较弱", persona="老师", gen_lang=gen_lang)
    attempts = 1
    backfilled, section = backfill_pages(section, chapter, universe, index=index)
    support, recall = _score_of(section, chapter, universe)
    retry_reason = improvement_reason(support, recall)
    best = {"section": section, "backfilled": backfilled, "support": support,
            "recall": recall, "attempts": attempts, "retry_reason": retry_reason}
    if not retry_reason or max_attempts <= 1:
        return best
    try:
        retry = fn(chapter, universe, client, index=index, target_score=80, days_left=7,
                   foundation="基础较弱", persona="老师", gen_lang=gen_lang,
                   extra_note=f"上一版不合格：{retry_reason}。请确认每个结论都能被引用页支持，"
                              "并把漏掉的资料术语写进正文。")
        r_backfill, retry = backfill_pages(retry, chapter, universe, index=index)
        r_support, r_recall = _score_of(retry, chapter, universe)
        best["attempts"] = 2
        if ((r_support.get("ratio") or 0) + (r_recall.get("recall") or 0)) > \
                ((support.get("ratio") or 0) + (recall.get("recall") or 0)):
            retry_reason = improvement_reason(r_support, r_recall)
            best = {"section": retry, "backfilled": r_backfill, "support": r_support,
                    "recall": r_recall, "attempts": 2, "retry_reason": retry_reason}
        else:
            best["retry_reason"] = retry_reason + "；重试未变好，保留原稿"
    except Exception as exc:  # noqa: BLE001
        best["retry_reason"] = f"{retry_reason}；重试失败：{type(exc).__name__}: {str(exc)[:120]}"
    return best


# ---------------------------------------------------------------- 主流程


def fuse_materials(
    output_id: str,
    materials: list[dict],
    *,
    title: str = "",
    course: str = "",
    author: bool = True,
    client=None,
    gen_lang: str = "zh",
    parent_id: str | None = None,
    progress=None,
) -> dict:
    """把多份资料融合成一份讲义；返回 artifact 信息与融合报告。"""
    if not materials:
        raise ValueError("至少选一份资料")
    if author and client is None:
        # 不能“要求模型成文但悄悄退回原文页”：这是静默降级，产品禁止。
        raise ValueError("要求模型成文，但没有可用的模型客户端；请检查模型配置后重试")
    out = service.artifact_path(output_id)
    if out is None:
        from tfv2.product.data_paths import ARTIFACT_ROOT
        out = ARTIFACT_ROOT / output_id
    if out.exists():
        shutil.rmtree(out)
    registry = DedupeRegistry()

    if progress:
        progress(6, "读取资料页")
    universe = build_universe(materials, out)

    (out / "assets").mkdir(exist_ok=True)
    (out / "source_assets").mkdir(exist_ok=True)
    if progress:
        progress(18, "切分章节")
    per_material = [chapters_of_material(m) for m in universe.materials]
    chapters = unique_titles(fuse_chapters(per_material))
    if not chapters:
        raise ValueError("资料里没有可用章节")

    report = {
        "mode": "fusion",
        "requested": "author" if author else "digest",
        "materials": [{"artifact_id": m.artifact_id, "label": m.label,
                       "pages": len(m.pages), "chapters": len(c)} for m, c in zip(universe.materials, per_material)],
        "chapters": [], "page_count": universe.page_count,
        "page_map": universe.origin,
    }

    sections: list[LectureSection] = []
    for i, chapter in enumerate(chapters, start=1):
        if progress:
            progress(20 + int(52 * (i - 1) / max(1, len(chapters))), f"融合第 {i}/{len(chapters)} 章：{chapter.title}")
        section = None
        mode = "digest"
        reason = ""
        backfilled: list[int] = []
        support: dict = {}
        recall: dict = {}
        attempts = 0
        retry_reason = ""
        if author and client is not None:
            try:
                outcome = author_with_retry(chapter, universe, client, index=i, gen_lang=gen_lang)
                section = outcome["section"]
                backfilled = outcome["backfilled"]
                support, recall = outcome["support"], outcome["recall"]
                attempts, retry_reason = outcome["attempts"], outcome["retry_reason"]
                mode = "authored"
            except Exception as exc:  # noqa: BLE001 — 失败必须记录原因，不能静默
                reason = f"{type(exc).__name__}: {str(exc)[:200]}"
                section = None
        if section is None:
            section = digest_section(chapter, universe, index=i,
                                     assets_dir=out / "source_assets", registry=registry)
            mode = "digest"
        # 模型和原文页都可能把 TeX 留在 $...$ 之外；统一按既有规范清洗后再进产物。
        section = _normalize_math(correct_block_kinds(section))
        sections.append(section)
        report["chapters"].append({
            "index": i, "title": section.title, "mode": mode, "fallback_reason": reason,
            "backfilled_pages": [universe.origin_of(p)["source_page"] for p in backfilled],
            "citation_support": support.get("ratio"),
            "attempts": attempts, "retry_reason": retry_reason,
            "term_recall": recall.get("recall"),
            "missing_terms": recall.get("missing") or [],
            "weak_blocks": support.get("weak_blocks") or [],
            "materials": chapter.materials, "deduped": chapter.deduped,
            "pages": sorted({r.page_start for b in section.blocks for r in b.source_refs
                             if b.kind != BlockKind.FIGURE}),
        })

    # 校准：真实模型改写的章节实测支持率 100%，所以 0.5 以下才值得提示，
    # 避免把正常改写误报成“引用不实”。
    weak_chapters = [c for c in report["chapters"]
                     if c.get("mode") == "authored" and (c.get("citation_support") or 0) < 0.5]
    low_recall = [c for c in report["chapters"]
                  if c.get("mode") == "authored" and (c.get("term_recall") or 0) < 0.5]
    warnings: list[str] = []
    if weak_chapters:
        warnings.append("这些章节的正文和引用页重合偏低，建议人工复核：" +
                        "；".join(f"第{c['index']}节 {c['citation_support']:.0%}" for c in weak_chapters))
    if low_recall:
        warnings.append("这些章节漏掉了资料里的核心术语，建议补写：" +
                        "；".join(f"第{c['index']}节 {c['term_recall']:.0%}" for c in low_recall))
    if warnings:
        report["warnings"] = warnings
    if progress:
        progress(74, "整理目录 / 摘要")
    label_list = [m.label for m in universe.materials]
    section_label = f"{len(label_list)} 份资料 · {len(sections)} 节 · {universe.page_count} 页"
    course_name = (course or "").strip() or (title or "").strip() or Path(label_list[0]).stem
    doc_title = (title or "").strip() or f"{course_name} 融合讲义"
    materials_line = "；".join(f"{m.label}（{len(m.pages)} 页）" for m in universe.materials)

    overview = (
        f"本讲义把 {len(label_list)} 份资料（{materials_line}）按主题重排为 {len(sections)} 节："
        "同名主题合成一章，跨资料的地方保留过渡，重复内容只讲一次，"
        f"每段都标注原资料页码，便于回查。共覆盖 {universe.page_count} 页。"
    )
    header = LectureHeader(
        title=doc_title, course=course_name, section_label=section_label,
        materials=label_list, coverage_scope=f"{universe.page_count} 页",
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )
    summary = LectureSummary(
        overview=sanitize_prose(overview),
        knowledge_map=[sanitize_prose(s.title) for s in sections][:14],
        exam_focus=[],
        how_to_use="先看目录找到对应主题，再读本章；每章末尾的出处写着原资料页码，可回原文核对。",
    )
    closing = LectureClosing(
        persona="老师",
        text=sanitize_prose("这份讲义把多份资料按主题合在了一起：先认清同一主题下各自的定义和条件，"
                            "再对照它们的例题和结论。读的时候按章走一遍，遇到与原文不一致的地方，"
                            "以标注的原资料页码为准。"),
    )
    footer = LectureFooter(
        agent_name="TermFinale", coverage_percent=100.0,
        material_label=" + ".join(Path(x).stem[:40] for x in label_list) or "多资料合集",
        disclaimer="具体请以实际资料为准，本资料不承担由此产生的法律责任。AI 生成内容仅供复习参考。",
    )
    project = {
        "id": output_id,
        "chapter_title": doc_title,
        "header": header.model_dump(mode="json"),
        "summary": summary.model_dump(mode="json"),
        "closing": closing.model_dump(mode="json"),
        "footer": footer.model_dump(mode="json"),
        "sections_files": ["sections.json"],
        "page_count": universe.page_count,
        "coverage_percent": 100.0,
        "scope_pages": list(range(1, universe.page_count + 1)),
        "overview_pages": [],
        "overview_mode": False,
        "constraints": {"fusion": {"materials": materials, "parent": parent_id}},
        "source_file": "source/fused.pdf",
        "assets_dir": "source_assets",
        "out_dir": ".",
        "language_policy": LanguagePolicy(ui_lang="zh", gen_lang="简体中文" if gen_lang == "zh" else gen_lang,
                                          source_lang=None, translation_mode="none").model_dump(mode="json"),
    }
    (out / "sections.json").write_text(
        json.dumps([s.model_dump(mode="json") for s in sections], ensure_ascii=False, indent=2), encoding="utf-8")
    rows = []
    for page in range(1, universe.page_count + 1):
        item = universe.origin_of(page)
        rows.append({"page": page, "source_page": item["source_page"], "material": item["label"],
                     "text": universe.ledger.pages[page - 1].text,
                     "quality": universe.ledger.pages[page - 1].quality.value})
    (out / "source_pages.json").write_text(json.dumps({
        "version": 1, "material": doc_title, "fused": True,
        "origin_material": materials_line, "page_count": universe.page_count, "pages": rows,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "project.json").write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8")

    if progress:
        progress(82, "排版 / 生成 PDF")
    build_project(out / "project.json", pdf=True)
    (out / "fusion_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if progress:
        progress(96, "融合完成")
    artifact = service.get_artifact(output_id)
    return {"id": output_id, "artifact": artifact, "pages": universe.page_count,
            "sections": len(sections), "materials": len(label_list),
            "authored": sum(1 for c in report["chapters"] if c["mode"] == "authored"),
            "digest": sum(1 for c in report["chapters"] if c["mode"] == "digest"),
            "report": report}

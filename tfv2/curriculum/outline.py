"""v2 课程大纲：真实章节/小节 + 页码覆盖；无有效大纲就失败，不生成假章节。"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from tfv2.domain.page import PageLedger

_SECTION_RE = re.compile(r"^(\d+\.\d+)\s+(.+)$")
_CHAPTER_RE = re.compile(r"^第[一二三四五六七八九十百零\d]+章\s*(.+)$")
_HEAD_RE = re.compile(r"^([一二三四五六七八九十]+)、\s*(.+)$")
_MATERIAL_HEAD_RE = re.compile(r"^【.*(?:资料|权重|第\s*\d+\s*页).*】$")


class OutlineError(RuntimeError):
    """无法从资料得到可信大纲。"""


class Subsection(BaseModel):
    title: str = Field(min_length=1)
    pages: list[int] = Field(min_length=1)


class Section(BaseModel):
    title: str = Field(min_length=1)
    pages: list[int] = Field(min_length=1)
    subsections: list[Subsection] = Field(min_length=1)


class CourseOutline(BaseModel):
    chapter_title: str = Field(min_length=1)
    sections: list[Section] = Field(min_length=1)
    source: Literal["pptx", "fallback", "manual"] = "pptx"
    page_count: int = Field(ge=1)

    @model_validator(mode="after")
    def _coverage_exact(self) -> "CourseOutline":
        expected = list(range(1, self.page_count + 1))
        all_pages: list[int] = []
        titles: list[str] = []
        for sec in self.sections:
            titles.append(sec.title)
            if sec.pages != list(range(min(sec.pages), max(sec.pages) + 1)):
                raise ValueError(f"章节「{sec.title}」页码不连续")
            all_pages.extend(sec.pages)
            sub_pages: list[int] = []
            sub_titles: list[str] = []
            for sub in sec.subsections:
                sub_titles.append(sub.title)
                if not set(sub.pages).issubset(set(sec.pages)):
                    raise ValueError(f"小节「{sub.title}」页码超出章节")
                sub_pages.extend(sub.pages)
            if sorted(sub_pages) != sorted(sec.pages):
                raise ValueError(f"章节「{sec.title}」小节没有完整覆盖本章页码")
            if len(sub_titles) != len(set(sub_titles)):
                raise ValueError(f"章节「{sec.title}」存在重复小节标题")
        if len(titles) != len(set(titles)):
            raise ValueError("存在重复章节标题")
        if sorted(all_pages) != expected:
            raise ValueError("章节没有完整覆盖 1..page_count")
        return self


def _lines(text: str) -> list[str]:
    return [x.strip() for x in (text or "").splitlines() if x.strip()]


def _clean_title(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    text = re.sub(r"[#＃]+$", "", text).strip()
    return text


def _chapter_title(ledger: PageLedger) -> str:
    for page in ledger.pages:
        for line in _lines(page.text):
            m = _CHAPTER_RE.match(line)
            if m:
                return _clean_title(line)
    return _clean_title(ledger.material.rsplit(".", 1)[0]) or "讲义"


def _section_starts(ledger: PageLedger) -> list[tuple[int, str]]:
    starts: list[tuple[int, str]] = []
    seen_pages: set[int] = set()
    for page in ledger.pages:
        for line in _lines(page.text):
            m = _SECTION_RE.match(line)
            if not m:
                continue
            title = _clean_title(f"{m.group(1)} {m.group(2)}")
            if _MATERIAL_HEAD_RE.match(title):
                continue
            if page.page_no in seen_pages:
                continue
            starts.append((page.page_no, title))
            seen_pages.add(page.page_no)
            break
    return starts


def _norm(text: str) -> str:
    return re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", text or "")


def _toc_titles(pages: list, start: int, end: int) -> list[str]:
    """在前几页里找“一、二、三…”最密集的一页，当作本节目录。"""
    best_page = None
    best_titles: list[str] = []
    for page in pages:
        if not (start <= page.page_no <= end):
            continue
        titles: list[str] = []
        for line in _lines(page.text):
            m = _HEAD_RE.match(line)
            if m and len(m.group(2)) <= 40:
                t = _clean_title(m.group(2))
                if t and t not in titles:
                    titles.append(t)
        if len(titles) > len(best_titles):
            best_titles = titles
            best_page = page.page_no
        if page.page_no >= start + 4 and best_titles:
            break
    return best_titles


def _find_title_page(pages: list, start: int, end: int, title: str, after: int = 0) -> int | None:
    key = _norm(title)[:8]
    if not key:
        return None
    for page in pages:
        if page.page_no < max(start, after + 1) or page.page_no > end:
            continue
        if key in _norm(page.text):
            return page.page_no
    return None


def _build_subsections(pages: list, start: int, end: int) -> list[Subsection]:
    titles = _toc_titles(pages, start, end)
    if len(titles) < 2:
        # 没有可识别目录：整节作为一个正文小节；不伪造多个标题。
        return [Subsection(title="正文", pages=list(range(start, end + 1)))]

    mapped: list[tuple[str, int]] = []
    last = start - 1
    for title in titles:
        page_no = _find_title_page(pages, start, end, title, after=last)
        if page_no is None:
            page_no = max(start, last + 1)
        if page_no <= last:
            page_no = last + 1
        if page_no > end:
            page_no = end
        mapped.append((title, page_no))
        last = page_no

    # 同页冲突：后面的标题顺延，保证每节至少一页。
    for i in range(1, len(mapped)):
        if mapped[i][1] <= mapped[i - 1][1]:
            mapped[i] = (mapped[i][0], min(end, mapped[i - 1][1] + 1))

    # 如果标题页之前还有内容，补“本节导入”。
    first_page = mapped[0][1]
    out: list[Subsection] = []
    if first_page > start:
        out.append(Subsection(title="本节导入", pages=list(range(start, first_page))))
    for i, (title, page_no) in enumerate(mapped):
        next_page = mapped[i + 1][1] if i + 1 < len(mapped) else end + 1
        if next_page <= page_no:
            next_page = page_no + 1
        out.append(Subsection(title=title, pages=list(range(page_no, min(end, next_page - 1) + 1))))
    return out


def _build_sections(ledger: PageLedger) -> list[Section]:
    starts = _section_starts(ledger)
    if not starts:
        title = _chapter_title(ledger)
        return [Section(title=title, pages=list(range(1, ledger.page_count + 1)),
                        subsections=_build_subsections(ledger.pages, 1, ledger.page_count))]
    sections: list[Section] = []
    for i, (start_page, title) in enumerate(starts):
        sec_start = 1 if i == 0 else start_page
        sec_end = (starts[i + 1][0] - 1) if i + 1 < len(starts) else ledger.page_count
        if sec_end < sec_start:
            raise OutlineError(f"章节「{title}」页码范围为空")
        subs = _build_subsections(ledger.pages, sec_start, sec_end)
        sections.append(Section(title=title, pages=list(range(sec_start, sec_end + 1)), subsections=subs))
    return sections


def build_outline(ledger: PageLedger) -> CourseOutline:
    """从页账本构建大纲；结构不合法时抛 OutlineError，不静默兜底成假章节。"""
    if not ledger.pages:
        raise OutlineError("页账本为空")
    chapter_title = _chapter_title(ledger)
    if _MATERIAL_HEAD_RE.match(chapter_title):
        raise OutlineError("章节标题是资料头，拒绝生成")
    sections = _build_sections(ledger)
    try:
        return CourseOutline(
            chapter_title=chapter_title,
            sections=sections,
            source="pptx",
            page_count=ledger.page_count,
        )
    except ValueError as exc:
        raise OutlineError(str(exc)) from exc


def load_outline(path: str | Path) -> CourseOutline:
    """读取人工确认过的大纲（source=manual）；仍走同一套覆盖校验。"""
    text = Path(path).read_text(encoding="utf-8")
    try:
        return CourseOutline.model_validate_json(text)
    except ValueError as exc:
        raise OutlineError(f"大纲文件不合法：{exc}") from exc


def save_outline(outline: CourseOutline, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(outline.model_dump_json(indent=2), encoding="utf-8")
    return target

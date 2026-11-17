"""把大纲/小节/摘要/结语/页脚装配成 LectureSpec。"""
from __future__ import annotations

from tfv2.domain.lecture import (
    LanguagePolicy,
    LectureClosing,
    LectureFooter,
    LectureHeader,
    LectureSection,
    LectureSpec,
    LectureSummary,
    TocItem,
)


def build_lecture_spec(
    *,
    chapter_title: str,
    header: LectureHeader,
    summary: LectureSummary,
    sections: list[LectureSection],
    closing: LectureClosing,
    footer: LectureFooter,
    page_count: int,
    coverage_percent: float,
    scope_pages: list[int] | None = None,
    language_policy: LanguagePolicy | None = None,
    overview_mode: bool = False,
) -> LectureSpec:
    toc = [TocItem(level=1, title=chapter_title, page_no=1, anchor="chapter-title")]
    for i, sec in enumerate(sections, start=2):
        toc.append(TocItem(level=sec.level, title=sec.title, page_no=i, anchor=sec.id))
    return LectureSpec(
        chapter_title=chapter_title,
        header=header,
        toc=toc,
        summary=summary,
        sections=sections,
        closing=closing,
        footer=footer,
        language_policy=language_policy or LanguagePolicy(gen_lang="中文", source_lang="中文"),
        page_count=page_count,
        coverage_percent=coverage_percent,
        overview_mode=overview_mode,
        scope_pages=scope_pages or [],
    )

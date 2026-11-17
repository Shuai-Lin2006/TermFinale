"""v2 讲义内容契约。

原则：
- 结构化内容先于 Markdown/HTML；渲染器只负责排版，不再让模型直接产出最终 HTML。
- 每个小节必须能回到资料页；正文 block 不允许出现 P.x（出处统一放小节末尾）。
- 讲义是教材，不是卡片流：标头/目录/摘要/正文/小节出处/图片/结语/页脚。
"""
from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class LanguagePolicy(BaseModel):
    """语言四角色：界面/生成/源内容/译文。"""

    ui_lang: str = "zh"
    gen_lang: str = "中文"
    source_lang: str | None = None
    translation_mode: Literal["none", "marked"] = "marked"


class SourceRef(BaseModel):
    """一条资料出处；page_start/page_end 是资料原始页码，不是成稿页码。"""

    material: str = Field(min_length=1)
    page_start: int = Field(ge=1)
    page_end: int | None = Field(default=None, ge=1)
    quote: str | None = None
    # artifact 的页码空间可能已被用户裁切（只选了原资料的几十页）。
    # source_page 记录这段内容在原始资料里的真实起始页；未裁切时等于 page_start。
    # 它只用于展示/溯源；门禁与覆盖率仍按 page_start/page_end（artifact 页码空间）计算。
    source_page: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def _page_range(self) -> "SourceRef":
        if self.page_end is not None and self.page_end < self.page_start:
            raise ValueError("page_end 不能小于 page_start")
        return self


class FigureRef(BaseModel):
    """图片必须挂在对应讲解 block 后，带图注与来源页。"""

    image_id: str = Field(min_length=1)
    caption: str = Field(min_length=1)
    source: SourceRef
    after_block_id: str = Field(min_length=1)
    asset_path: str | None = None
    origin: Literal["source", "redrawn", "schematic"] = "schematic"
    source_note: str | None = None
    bbox: list[float] | None = None


class LectureHeader(BaseModel):
    """标头：标题 + 用户情况；不放 App 名/开发者/随机祝福/源文件名。"""

    title: str = Field(min_length=1)
    course: str = Field(min_length=1)
    section_label: str | None = None
    materials: list[str] = Field(default_factory=list)
    target_score: int | None = Field(default=None, ge=0, le=100)
    days_left: int | None = Field(default=None, ge=0)
    foundation: str | None = None
    persona: str = "老师"
    coverage_scope: str = ""
    generated_at: str = ""


class TocItem(BaseModel):
    """教材目录项；page_no 是成稿页码，不是资料页码。"""

    level: Literal[1, 2, 3]
    title: str = Field(min_length=1)
    page_no: int = Field(ge=1)
    anchor: str = Field(min_length=1)


class LectureSummary(BaseModel):
    """正文之前的全篇摘要：这份资料到底涉及什么。"""

    overview: str = Field(min_length=1)
    knowledge_map: list[str] = Field(default_factory=list)
    exam_focus: list[str] = Field(default_factory=list)
    how_to_use: str = ""


class BlockKind(str, Enum):
    PARAGRAPH = "paragraph"
    CLAIM = "claim"
    FORMULA = "formula"
    EXAMPLE = "example"
    PITFALL = "pitfall"
    SUMMARY = "summary"
    FIGURE = "figure"
    QUOTE = "quote"
    TABLE = "table"


class LectureBlock(BaseModel):
    """正文最小单元；claim/example 建议带 source_refs，section 级出处是硬要求。"""

    id: str = Field(min_length=1)
    kind: BlockKind
    text: str = ""
    source_refs: list[SourceRef] = Field(default_factory=list)
    figure: FigureRef | None = None
    doc_page: int | None = Field(default=None, ge=1)


class LectureSection(BaseModel):
    """一节 = 一个考点/知识块；必须有资料出处。"""

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    level: Literal[2, 3] = 2
    blocks: list[LectureBlock] = Field(default_factory=list)
    source_refs: list[SourceRef] = Field(default_factory=list)
    summary: str | None = None
    objectives: list[str] = Field(default_factory=list)
    key_terms: list[str] = Field(default_factory=list)
    self_test: list[str] = Field(default_factory=list)
    visual_hint: str = "none"


class LectureClosing(BaseModel):
    """文末单独一大段，按人设鼓励；不是模板句。"""

    persona: str = Field(min_length=1)
    text: str = Field(min_length=1)


class LectureFooter(BaseModel):
    """所有 AI 生成资料末尾的一行小字；不影响阅读。"""

    agent_name: str = "TermFinale"
    coverage_percent: float = Field(ge=0, le=100)
    material_label: str = Field(min_length=1)
    disclaimer: str = Field(
        default="具体请以实际资料为准，本资料不承担由此产生的法律责任。",
        min_length=1,
    )


class LectureSpec(BaseModel):
    """一份讲义的完整契约；只有通过 LectureGate 才能进入 delivered。"""

    schema_version: str = "2.0"
    chapter_title: str | None = None
    header: LectureHeader
    toc: list[TocItem] = Field(default_factory=list)
    summary: LectureSummary
    sections: list[LectureSection] = Field(default_factory=list)
    closing: LectureClosing
    footer: LectureFooter
    language_policy: LanguagePolicy = Field(default_factory=LanguagePolicy)
    page_count: int = Field(ge=1)
    coverage_percent: float = Field(ge=0, le=100)
    overview_mode: bool = False
    # 章节样章/分册可限定覆盖范围；为空表示整份资料。
    scope_pages: list[int] = Field(default_factory=list)

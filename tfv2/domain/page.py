"""v2 页账本：每一页都必须有账，读不出来的页也要显式记录。"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator


class PageQuality(str, Enum):
    TEXT = "text"
    OCR = "ocr"
    IMAGE_ONLY = "image_only"
    LOW_TEXT = "low_text"
    EMPTY = "empty"


class PageImage(BaseModel):
    image_id: str = Field(min_length=1)
    caption: str | None = None
    kind: str = "content"  # content / decoration / screenshot / logo
    discarded_reason: str | None = None
    asset_path: str | None = None  # v2 ingest 抽取到本地的图片路径
    bbox: list[float] | None = None  # source page bbox [x0,y0,x1,y1], if known


class Page(BaseModel):
    material: str = Field(min_length=1)
    page_no: int = Field(ge=1)
    text: str = ""
    quality: PageQuality = PageQuality.TEXT
    images: list[PageImage] = Field(default_factory=list)
    ocr_used: bool = False
    formula_damage: bool = False
    missing_reason: str | None = None


class PageLedger(BaseModel):
    """一份资料的页账本；pages 必须覆盖 1..page_count，不允许静默丢页。"""

    material: str = Field(min_length=1)
    page_count: int = Field(ge=1)
    pages: list[Page] = Field(default_factory=list)
    source_hash: str = Field(min_length=1)
    parser_version: str = Field(min_length=1)

    @model_validator(mode="after")
    def _every_page_accounted(self) -> "PageLedger":
        nums = [p.page_no for p in self.pages]
        if len(nums) != len(set(nums)):
            raise ValueError("页账本存在重复页码")
        expected = set(range(1, self.page_count + 1))
        missing = sorted(expected - set(nums))
        if missing:
            raise ValueError(f"页账本缺少页码：{missing[:10]}")
        extra = sorted(set(nums) - expected)
        if extra:
            raise ValueError(f"页账本出现超出总页数的页码：{extra[:10]}")
        return self

    @property
    def readable_pages(self) -> int:
        return sum(1 for p in self.pages if p.quality not in (PageQuality.EMPTY,))

    @property
    def coverage(self) -> float:
        return round(self.readable_pages / self.page_count, 4)

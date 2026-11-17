"""Canonical document model shared by every module."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator


class FactKind(str, Enum):
    DEFINITION = "definition"
    FORMULA = "formula"
    CONCLUSION = "conclusion"
    PITFALL = "pitfall"
    FIGURE = "figure"


class Fact(BaseModel):
    fact_id: str = Field(min_length=1)
    page: int = Field(ge=1)
    kind: FactKind
    text: str = Field(min_length=1)
    source_span: str = ""
    confidence: float = Field(default=0.8, ge=0, le=1)


class SectionPlan(BaseModel):
    plan_id: str = Field(min_length=1)
    title: str = ""
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    fact_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _page_order(self) -> "SectionPlan":
        if self.page_end < self.page_start:
            raise ValueError("section page_end < page_start")
        return self


class CanonicalDocument(BaseModel):
    document_id: str = Field(min_length=1)
    material: str = Field(min_length=1)
    page_count: int = Field(ge=1)
    facts: list[Fact] = Field(default_factory=list)
    plans: list[SectionPlan] = Field(default_factory=list)
    status: str = "draft"
    issues: list[str] = Field(default_factory=list)

    @property
    def coverage(self) -> float:
        planned = {fid for p in self.plans for fid in p.fact_ids}
        return round(len(planned) / max(1, len(self.facts)), 4)

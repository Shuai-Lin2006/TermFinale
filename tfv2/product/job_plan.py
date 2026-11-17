"""Per-file job planning: estimate, preview ranges and confirmation."""
from __future__ import annotations

from pydantic import BaseModel, Field

from .scale_policy import DetailMode, estimate


class FileSpec(BaseModel):
    name: str = Field(min_length=1)
    pages: int = Field(ge=1)
    artifact_id: str = ""


class FilePlan(BaseModel):
    name: str
    pages: int
    artifact_id: str = ""
    size: str
    coverage: float
    mode: str
    minutes: int
    cost_cny: float
    preview_pages: int
    preview_range: str
    requires_confirm: bool


class JobPlan(BaseModel):
    files: list[FilePlan]
    total_minutes: int
    total_cost_cny: float
    parallel_workers: int
    requires_confirm: bool
    merge: bool


def build_plan(files: list[FileSpec], *, mode: DetailMode = DetailMode.MAIN,
               parallel_workers: int = 2, preview_pages: int = 2,
               merge: bool = True) -> JobPlan:
    workers = max(1, min(int(parallel_workers), max(1, len(files)), 8))
    rows: list[FilePlan] = []
    for f in files:
        e = estimate(f.pages, mode=mode, parallel_units=workers, preview_pages=preview_pages)
        rows.append(FilePlan(
            name=f.name, pages=f.pages, artifact_id=f.artifact_id, size=e.size.value, coverage=e.coverage,
            mode=e.mode.value, minutes=e.minutes, cost_cny=e.cost_cny,
            preview_pages=e.preview_pages,
            preview_range=f"1-{min(e.preview_pages, f.pages)}",
            requires_confirm=e.requires_confirm(),
        ))
    return JobPlan(files=rows,
                   total_minutes=sum(x.minutes for x in rows),
                   total_cost_cny=round(sum(x.cost_cny for x in rows), 2),
                   parallel_workers=workers,
                   requires_confirm=any(x.requires_confirm for x in rows),
                   merge=merge)

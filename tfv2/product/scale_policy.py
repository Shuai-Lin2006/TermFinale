"""Long-document policy: per-file coverage, mode, preview and estimates."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SizeClass(str, Enum):
    SMALL = "small"          # <= 50
    MEDIUM = "medium"        # 51-100
    LARGE = "large"          # 101-150
    XLARGE = "xlarge"        # > 150


class DetailMode(str, Enum):
    OUTLINE = "outline"      # 大框
    MAIN = "main"            # 大部分
    FULL = "full"            # 全部


def coverage_target(pages: int) -> float:
    if pages <= 50:
        return 1.0
    if pages <= 100:
        return 0.90
    if pages <= 150:
        return 0.85
    return 0.80


def size_class(pages: int) -> SizeClass:
    if pages <= 50:
        return SizeClass.SMALL
    if pages <= 100:
        return SizeClass.MEDIUM
    if pages <= 150:
        return SizeClass.LARGE
    return SizeClass.XLARGE


@dataclass(frozen=True)
class Estimate:
    pages: int
    size: SizeClass
    coverage: float
    mode: DetailMode
    parallel_units: int
    preview_pages: int
    minutes: int
    cost_cny: float

    def requires_confirm(self) -> bool:
        return self.pages > 50 or self.cost_cny >= 3.0


def estimate(pages: int, *, mode: DetailMode = DetailMode.MAIN,
             parallel_units: int = 1, preview_pages: int = 2) -> Estimate:
    """Rough, explicit estimate; never use it as a billing promise."""
    pages = max(1, int(pages))
    parallel_units = max(1, min(int(parallel_units), 8))
    # 2-page units; parse + generate + verify + merge are included.
    minutes_per_page = {DetailMode.OUTLINE: 0.25, DetailMode.MAIN: 0.45, DetailMode.FULL: 0.7}[mode]
    cost_per_page = {DetailMode.OUTLINE: 0.03, DetailMode.MAIN: 0.06, DetailMode.FULL: 0.10}[mode]
    minutes = max(1, round(pages * minutes_per_page / (1 + 0.35 * (parallel_units - 1))))
    cost = round(pages * cost_per_page, 2)
    return Estimate(pages=pages, size=size_class(pages), coverage=coverage_target(pages),
                    mode=mode, parallel_units=parallel_units,
                    preview_pages=min(preview_pages, pages), minutes=minutes, cost_cny=cost)


def per_file_estimates(files: list[tuple[str, int]], *, mode: DetailMode = DetailMode.MAIN) -> list[dict]:
    """Multiple files are estimated independently, never summed into one size class."""
    out = []
    for name, pages in files:
        e = estimate(pages, mode=mode)
        out.append({"file": name, **e.__dict__, "requires_confirm": e.requires_confirm()})
    return out

"""讲义档位与多资料编排规则。

规则只按“单个资料总页数”判断；多资料拼接不改变单资料的档位集合。
覆盖目标按产品定义写死，任何档位都不得遗漏知识点。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


TIER_LABELS = {
    "standard": "标准（高质量全覆盖）",
    "normal": "普通讲义",
    "premium": "精品讲义",
    "broad": "高范围讲义",
}

# 单资料页数 -> {档位: 最低覆盖率}；1–50 只有 standard，必须 100%。
COVERAGE_TARGETS = {
    "standard": 100,
    "normal": 50,
    "premium": 50,
    "broad": 50,
}


def tiers_for_pages(total_pages: int) -> list[str]:
    n = max(0, int(total_pages))
    if n <= 50:
        return ["standard"]
    if n <= 150:
        return ["premium", "broad"]
    if n <= 500:
        return ["normal", "premium", "broad"]
    return ["normal", "premium"]


def coverage_target(total_pages: int, tier: str) -> int:
    n = max(0, int(total_pages))
    if n <= 50:
        return 100
    if n <= 150:
        return 70 if tier == "premium" else 85
    if n <= 500:
        return {"normal": 50, "premium": 65, "broad": 75}[tier]
    return 50


def tier_detail_policy(total_pages: int, tier: str) -> str:
    n = max(0, int(total_pages))
    if n <= 50:
        return "逐页讲透：定义、条件、公式、例题、图注尽量齐全。"
    if tier == "broad":
        return "保证基本框架、完整目录和摘要，覆盖目标内不漏知识点；不保证每页图文并茂或逐题展开。"
    if tier == "premium":
        return "重点页深讲，其余页保证框架和要点；不保证每页配图。"
    return "保证基本框架、完整目录和摘要，覆盖目标内不漏知识点；细节和配图从简。"


def tier_warning(total_pages: int, tier: str) -> str:
    target = coverage_target(total_pages, tier)
    policy = tier_detail_policy(total_pages, tier)
    if tier == "standard":
        return f"必须高质量、全覆盖，覆盖率 100%；{policy}"
    return f"覆盖目标 ≥{target}%，不得遗漏知识点；{policy}"


def tier_guarantees() -> dict:
    return {"framework": True, "toc": True, "summary": True, "sources": True,
            "figures": "best_effort", "per_page_detail": "not_guaranteed"}


@dataclass
class MaterialInput:
    artifact_id: str
    total_pages: int
    pages: list[int] = field(default_factory=list)

    def effective_pages(self) -> list[int]:
        if self.pages:
            return sorted({p for p in self.pages if 1 <= int(p) <= self.total_pages})
        return list(range(1, self.total_pages + 1))


@dataclass
class MaterialPlan:
    artifact_id: str
    total_pages: int
    pages: list[int]
    tiers: list[str]
    default_tier: str
    warnings: dict[str, str]
    coverage_targets: dict[str, int]
    detail_policies: dict[str, str]


def plan_materials(materials: Iterable[MaterialInput], merge: bool = False) -> dict:
    items = list(materials)
    if not items:
        raise ValueError("至少选一份资料")
    plans: list[MaterialPlan] = []
    for m in items:
        tiers = tiers_for_pages(m.total_pages)
        plans.append(MaterialPlan(
            artifact_id=m.artifact_id,
            total_pages=m.total_pages,
            pages=m.effective_pages(),
            tiers=tiers,
            default_tier=tiers[0],
            warnings={t: tier_warning(m.total_pages, t) for t in tiers},
            coverage_targets={t: coverage_target(m.total_pages, t) for t in tiers},
            detail_policies={t: tier_detail_policy(m.total_pages, t) for t in tiers},
        ))
    merge_tiers: list[str] = []
    if merge and len(items) > 1:
        merge_tiers = list(plans[0].tiers)
        for p in plans[1:]:
            merge_tiers = [t for t in merge_tiers if t in p.tiers]
        if not merge_tiers:
            raise ValueError("这些资料的可用档位没有交集，不能拼接；请分开生成")
    return {
        "merge": bool(merge and len(items) > 1),
        "materials": [
            {
                "artifact_id": p.artifact_id,
                "total_pages": p.total_pages,
                "pages": p.pages,
                "tiers": p.tiers,
                "default_tier": p.default_tier,
                "warnings": p.warnings,
                "coverage_targets": p.coverage_targets,
                "detail_policies": p.detail_policies,
                "guarantees": tier_guarantees(),
                "no_omit": True,
            }
            for p in plans
        ],
        "merge_tiers": merge_tiers,
    }

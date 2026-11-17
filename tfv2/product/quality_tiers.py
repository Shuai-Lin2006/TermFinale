"""Quality/cost tiers exposed before a job starts.

Users choose outcomes, not model names. All ranges are estimates; actual usage
is written to the task ledger. Page coverage is guaranteed in every tier.
"""
from __future__ import annotations

TIERS = {
    "eco": {
        "label": "省钱",
        "summary": "本地候选优先，Flash 只补空页/冲突；讲义偏骨架，慢一点也能看。",
        "page_coverage": "100%",
        "lecture": "骨架版",
        "extraction": "候选 + 轻核验",
        "exam": "题库抽题，少重写",
        "multiplier": 0.45,
    },
    "balanced": {
        "label": "均衡",
        "summary": "本地解析 + Flash 提取 + Pro-low 讲义；默认，质量和成本平衡。",
        "page_coverage": "100%",
        "lecture": "完整版",
        "extraction": "批量核验",
        "exam": "蓝图 + 一次审计",
        "multiplier": 1.0,
    },
    "max": {
        "label": "精修",
        "summary": "Pro 成文、独立答案审计、图注/公式复核；慢，但适合最终交付。",
        "page_coverage": "100%",
        "lecture": "精修版",
        "extraction": "逐块复核",
        "exam": "独立解题 + 冲突复核",
        "multiplier": 2.2,
    },
}

MODULE_WEIGHT = {"extract": 0.35, "lecture": 1.0, "exam": 0.20}


def estimate(pages: int, modules: list[str] | None = None, tier: str = "balanced") -> dict:
    pages = max(1, int(pages or 1))
    modules = [m for m in (modules or ["lecture", "extract", "exam"]) if m in MODULE_WEIGHT] or ["lecture"]
    key = tier if tier in TIERS else "balanced"
    t = TIERS[key]
    # Reference: balanced, all three modules, 1000 pages ≈ 70–120 min, ¥25–45.
    factor = (pages / 1000.0) * t["multiplier"] * sum(MODULE_WEIGHT[m] for m in modules) / sum(MODULE_WEIGHT.values())
    time_min = max(2, round(70 * factor))
    time_max = max(time_min + 2, round(120 * factor))
    cost_min = max(1, round(25 * factor, 1))
    cost_max = max(cost_min + 1, round(45 * factor, 1))
    return {
        "tier": key,
        "label": t["label"],
        "summary": t["summary"],
        "pages": pages,
        "modules": modules,
        "page_coverage": t["page_coverage"],
        "lecture": t["lecture"],
        "extraction": t["extraction"],
        "exam": t["exam"],
        "time_min_minutes": time_min,
        "time_max_minutes": time_max,
        "cost_min_cny": cost_min,
        "cost_max_cny": cost_max,
        "note": "估算，按实际 token/模型账单结算；超预算自动停。",
    }


def all_estimates(pages: int, modules: list[str] | None = None) -> list[dict]:
    return [estimate(pages, modules, key) for key in ("eco", "balanced", "max")]

"""Page-count policy: precise mandatory <=100, options 101-500 and >1000."""
from __future__ import annotations

import math


def options(page_count: int) -> dict:
    n = max(1, int(page_count))
    precise = {
        "mode": "precise", "label": "精准",
        "quality": "逐页覆盖，语义核验，成本/时间高",
        "time_min_minutes": max(2, math.ceil(n * 0.25)),
        "time_max_minutes": max(3, math.ceil(n * 0.45)),
        "cost_min_cny": round(max(1, n * 0.025), 1),
        "cost_max_cny": round(max(2, n * 0.06), 1),
        "calibration": "实测：100 页扫描件精准约 31.2 分钟（1869s）",
    }
    approx = {
        "mode": "approx", "label": "大概",
        "quality": "快速浏览，章节级覆盖，可能漏细节",
        "time_min_minutes": max(2, math.ceil(n * 0.025)),
        "time_max_minutes": max(3, math.ceil(n * 0.05)),
        "cost_min_cny": round(max(1, n * 0.004), 1),
        "cost_max_cny": round(max(2, n * 0.012), 1),
    }
    if n <= 100:
        return {"page_count": n, "required": "precise", "choices": [precise],
                "warning": "≤100 页必须精准；不提供大概模式。实测 100 页约 31 分钟，请预留时间。"}
    if n <= 500:
        return {"page_count": n, "required": None, "choices": [precise, approx],
                "warning": "精准会明显更慢更贵；实测 100 页约 31 分钟，大概更快但可能漏细节。"}
    return {"page_count": n, "required": None, "choices": [precise, approx],
            "warning": "≥501 页：精准模式时间和成本很高，建议先按页码范围或分章；大概模式更快但不能保证逐页精准。"}


def choose(page_count: int, mode: str) -> dict:
    info = options(page_count)
    for item in info["choices"]:
        if item["mode"] == mode:
            return item
    raise ValueError(f"该页数不支持模式：{mode}")

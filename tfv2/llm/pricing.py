"""Configurable CNY price table. No built-in prices, no silent guesses."""
from __future__ import annotations

import json
import os
from pathlib import Path


def load_prices() -> dict | None:
    raw = os.getenv("TERMFINALE_PRICE_JSON", "").strip()
    if not raw:
        return None
    try:
        if Path(raw).is_file():
            data = json.loads(Path(raw).read_text(encoding="utf-8"))
        else:
            data = json.loads(raw)
    except Exception:
        return None
    if not isinstance(data, dict) or not data:
        return None
    out = {}
    for model, item in data.items():
        if not isinstance(item, dict):
            return None
        try:
            inp = float(item["input"])
            outp = float(item["output"])
        except Exception:
            return None
        if inp < 0 or outp < 0:
            return None
        out[str(model)] = {"input": inp, "output": outp}
    return out


def estimate(by_model: dict | None) -> float | None:
    """CNY estimate; None if any model has no configured price."""
    prices = load_prices()
    if not prices or not by_model:
        return None
    total = 0.0
    for model, item in by_model.items():
        p = prices.get(str(model))
        if p is None:
            return None
        total += (int(item.get("prompt_tokens") or 0) * p["input"]
                  + int(item.get("completion_tokens") or 0) * p["output"]) / 1_000_000
    return round(total, 6)

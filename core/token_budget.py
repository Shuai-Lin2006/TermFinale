"""本地每日 Token 预算：跨进程简单文件计数，超限拒绝新调用。"""
from __future__ import annotations
import json, os, threading
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "data" / "token_usage.json"
_LOCK = threading.Lock()


def daily_max() -> int:
    """0 means no local daily limit; a positive value restores the guard."""
    try:
        return max(0, int(os.getenv("TERMFINALE_DAILY_TOKENS", "0")))
    except Exception:
        return 0


def _read() -> dict:
    try:
        data = json.loads(PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def _write(data: dict) -> None:
    PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    tmp.replace(PATH)


def status() -> dict:
    with _LOCK:
        data = _read(); day = date.today().isoformat()
        used = int((data.get(day) or {}).get("tokens", 0))
    maximum = daily_max()
    return {"day": day, "used": used, "max": maximum,
            "left": None if maximum <= 0 else max(0, maximum - used),
            "unlimited": maximum <= 0}


def check() -> None:
    s = status()
    if s["max"] > 0 and s["used"] >= s["max"]:
        raise RuntimeError(f"今日 Token 预算已用完：{s['used']}/{s['max']}")


def add(tokens: int) -> None:
    if tokens <= 0:
        return
    with _LOCK:
        data = _read(); day = date.today().isoformat()
        item = data.get(day) if isinstance(data.get(day), dict) else {"tokens": 0}
        item["tokens"] = int(item.get("tokens", 0)) + int(tokens)
        data[day] = item
        _write(data)

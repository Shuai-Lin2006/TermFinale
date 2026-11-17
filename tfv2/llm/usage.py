"""Per-process model usage ledger (tokens, calls, models).

One chapter runs in one subprocess, so a process-local ledger is sufficient and
avoids cross-thread context issues. Cost in CNY is intentionally not guessed
here; callers can price tokens with their own contract.
"""
from __future__ import annotations

import threading

_LOCK = threading.Lock()
_STATE = {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "by_model": {}}


def reset() -> None:
    with _LOCK:
        _STATE.update({"calls": 0, "prompt_tokens": 0, "completion_tokens": 0,
                       "total_tokens": 0, "by_model": {}})


def add(model: str, *, prompt_tokens: int = 0, completion_tokens: int = 0,
        total_tokens: int = 0) -> None:
    p = max(0, int(prompt_tokens or 0))
    c = max(0, int(completion_tokens or 0))
    t = max(0, int(total_tokens or 0)) or (p + c)
    if t <= 0:
        return
    name = str(model or "unknown")
    with _LOCK:
        _STATE["calls"] += 1
        _STATE["prompt_tokens"] += p
        _STATE["completion_tokens"] += c
        _STATE["total_tokens"] += t
        item = _STATE["by_model"].setdefault(name, {"calls": 0, "tokens": 0, "prompt_tokens": 0, "completion_tokens": 0})
        item["calls"] += 1
        item["tokens"] += t
        item["prompt_tokens"] += p
        item["completion_tokens"] += c


def snapshot() -> dict:
    with _LOCK:
        return {
            "calls": _STATE["calls"],
            "prompt_tokens": _STATE["prompt_tokens"],
            "completion_tokens": _STATE["completion_tokens"],
            "total_tokens": _STATE["total_tokens"],
            "by_model": {k: dict(v) for k, v in _STATE["by_model"].items()},
        }

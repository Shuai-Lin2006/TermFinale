"""Minimal usable profile: never hide failed modules.

This is a beta profile, not a release. UI stays off until the release gate passes.
"""
from __future__ import annotations

from pathlib import Path

from . import release_gate

ALWAYS_CHECK = ("lecture", "extract", "exam")


def evaluate(workspace_root: str | Path) -> dict:
    gate = release_gate.evaluate(workspace_root, ui_ready=False, benchmark_passed=False)
    enabled = []
    disabled = []
    for module in ALWAYS_CHECK:
        info = gate["modules"].get(module) or {}
        (enabled if info.get("validated") else disabled).append(module)
    # questions is deliberately not silently enabled: it needs a manual bank
    # or a successful real extraction run.
    q = gate["modules"].get("questions") or {}
    questions = {
        "enabled": bool(q.get("validated")),
        "mode": "manual_bank_required" if not q.get("validated") else "extraction",
        "reason": "questions 未 validated；需人工题库或重跑" if not q.get("validated") else "",
    }
    ready = len(enabled) == len(ALWAYS_CHECK)
    return {
        "mode": "beta" if ready else "not_ready",
        "release": False,
        "ui": False,
        "enabled": enabled,
        "disabled": disabled,
        "questions": questions,
        "release_blockers": gate["blockers"],
        "note": "beta 不是发布；questions 未 validated 时必须显式提示人工题库",
    }

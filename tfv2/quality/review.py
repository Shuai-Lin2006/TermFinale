"""Deterministic lecture review + only low-risk automatic revisions."""
from __future__ import annotations

import re
from pathlib import Path

from tfv2.domain.lecture import BlockKind, LectureSpec


def _norm(text: str) -> str:
    return re.sub(r"\s+", "", text or "").lower()


def review_lecture(spec: LectureSpec) -> dict:
    issues: list[dict] = []
    seen: dict[str, str] = {}
    for sec in spec.sections:
        blocks = [b for b in sec.blocks if b.kind != BlockKind.FIGURE]
        if sum(len(b.text or "") for b in blocks) < 180:
            issues.append({"code": "section.short", "severity": "warn", "section": sec.title,
                           "message": "本节正文偏短，可能只有提纲"})
        if not any(b.kind == BlockKind.EXAMPLE for b in sec.blocks):
            issues.append({"code": "section.no_example", "severity": "info", "section": sec.title,
                           "message": "本节没有例题；定义型小节可接受"})
        for b in blocks:
            key = _norm(b.text)
            if len(key) < 40:
                continue
            if key in seen and seen[key] != b.id:
                issues.append({"code": "block.duplicate", "severity": "warn", "section": sec.title,
                               "block": b.id, "message": "正文与其他块完全重复"})
            seen[key] = b.id
            if not b.source_refs:
                issues.append({"code": "block.no_source", "severity": "hard", "section": sec.title,
                               "block": b.id, "message": "正文缺少来源"})
        for b in sec.blocks:
            if b.kind == BlockKind.FIGURE and b.figure is not None:
                if not b.figure.caption.strip():
                    issues.append({"code": "figure.no_caption", "severity": "warn", "section": sec.title,
                                   "message": "图片缺图注"})
    hard = sum(1 for x in issues if x["severity"] == "hard")
    warn = sum(1 for x in issues if x["severity"] == "warn")
    return {"issues": issues, "hard": hard, "warn": warn,
            "score": max(0, 100 - hard * 25 - warn * 3), "passed": hard == 0}


def _dedupe_safe(spec: LectureSpec) -> list[dict]:
    """Remove exact duplicate long prose inside one section. Nothing else."""
    applied: list[dict] = []
    for sec in spec.sections:
        seen: set[str] = set()
        kept = []
        for b in sec.blocks:
            if b.kind == BlockKind.PARAGRAPH:
                key = _norm(b.text)
                if len(key) >= 60 and key in seen:
                    applied.append({"section": sec.title, "removed": b.id,
                                    "reason": "同节完全重复段落"})
                    continue
                seen.add(key)
            kept.append(b)
        sec.blocks = kept
    return applied


def review_markdown(report: dict, applied: list[dict]) -> str:
    lines = ["# 自动审稿报告", "", f"- 分数：{report.get('score')}",
             f"- 硬问题：{report.get('hard')}，提醒：{report.get('warn')}",
             f"- 自动修订：{len(applied)}", ""]
    if applied:
        lines += ["## 已应用的低风险修订", ""] + [f"- {x['section']}：删除 {x['removed']}（{x['reason']}）" for x in applied] + [""]
    lines += ["## 审稿问题", ""]
    for x in report.get("issues") or []:
        lines.append(f"- `{x['code']}`（{x['severity']}）{x.get('section','')} {x['message']}")
    return "\n".join(lines) + "\n"


def review_and_revise(spec: LectureSpec) -> tuple[dict, list[dict]]:
    applied = _dedupe_safe(spec)
    return review_lecture(spec), applied

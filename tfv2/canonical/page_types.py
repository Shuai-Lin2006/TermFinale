"""Page type classifier: content vs exercise/empty/overview."""
from __future__ import annotations

import re
from enum import Enum

_Q = re.compile(r"^\s*(?:\d{1,3}[.、]|[（(]\s*\d{1,3}\s*[）)])")
_OPT = re.compile(r"^\s*[A-D][.、]")
_EX = re.compile(r"(习题|练习|作业|答案|解答|试卷|考试|选择题|填空题)")
_OVERVIEW = re.compile(r"(目录|本章小结|本章小结|前言|序言|符号表|术语表)")
_SYMBOL = re.compile(r"^[^：:]{1,24}[：:]")


class PageType(str, Enum):
    CONTENT = "content"
    EXERCISE = "exercise"
    EMPTY = "empty"
    OVERVIEW = "overview"


def classify_page(text: str) -> PageType:
    t = text or ""
    lines = [x.strip() for x in t.splitlines() if x.strip()]
    if not t.strip():
        return PageType.EMPTY
    if _OVERVIEW.search(t[:300]):
        return PageType.OVERVIEW
    symbol_lines = sum(1 for x in lines if _SYMBOL.match(x) and len(x) < 90)
    if len(lines) >= 8 and symbol_lines / len(lines) >= 0.55:
        return PageType.OVERVIEW
    if t.count("：") + t.count(":") >= 15 and len(t) < 4000:
        return PageType.OVERVIEW
    numbered = sum(1 for x in lines if _Q.match(x))
    options = sum(1 for x in lines if _OPT.match(x))
    if _EX.search(t[:500]) or options >= 3 or numbered >= 5:
        return PageType.EXERCISE
    if len(t.strip()) < 40:
        return PageType.EMPTY
    return PageType.CONTENT

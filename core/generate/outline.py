"""课程大纲规划：先定章节，再逐章生成。

旧实现按「2 页 PPT = 一章」硬切，出来的目录是 16 篇并列作文，没有主线。
现在先用一次轻量 AI 调用规划章节（含必考点、重要度、预估字数），
失败则退回分页启发式大纲——保证离线/断网也能跑。
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Callable

from loguru import logger

MAX_CHAPTERS = 10
MAX_PAGES_PER_CHAPTER = 6
MAX_TOTAL_PAGES = 40

_DISABLE_AI = os.getenv("TERMFINALE_DISABLE_AI", "").strip().lower() in ("1", "true", "yes")


@dataclass
class Chapter:
    index: int
    title: str
    pages: list[int]                 # pages 列表中的 0-based 下标
    must_know: list[str] = field(default_factory=list)
    importance: int = 3              # 1~5
    est_words: int = 1800


@dataclass
class Outline:
    chapters: list[Chapter]
    source: str = "fallback"         # ai | fallback


# --------------------------------------------------------------------------- #
# 启发式兜底
# --------------------------------------------------------------------------- #
def _page_head(page: str, limit: int = 60) -> str:
    text = re.sub(r"\[\[\[IMAGE:.*?\]\]\]", "", page)
    text = re.sub(r"【《.*?》第.*?页】", "", text).strip()
    for line in text.splitlines():
        line = line.strip()
        if len(line) >= 4:
            return line[:limit]
    return ""


def fallback_outline(pages: list[str], chapters: int | None = None) -> Outline:
    n = len(pages)
    if n == 0:
        return Outline([], source="fallback")
    count = chapters or max(3, min(MAX_CHAPTERS, round(n / 3)))
    count = min(count, n)
    size = max(1, -(-n // count))
    out: list[Chapter] = []
    for i in range(0, n, size):
        idx = list(range(i, min(n, i + size)))
        title = ""
        for page_index in idx:
            if len(re.sub(r"\s", "", pages[page_index])) >= 80:
                title = _page_head(pages[page_index])
                break
        title = title or _page_head(pages[idx[0]]) or f"第 {len(out) + 1} 部分"
        out.append(Chapter(index=len(out), title=title, pages=idx, importance=3))
    return Outline(out, source="fallback")


# --------------------------------------------------------------------------- #
# AI 大纲
# --------------------------------------------------------------------------- #
def build_digest(pages: list[str], per_page: int = 180, max_chars: int = 14000) -> str:
    # 长文档不能只看前 40 页：均匀抽样，让大纲能覆盖全书（1001 页也成立）。
    n = len(pages)
    if n == 0:
        return ""
    if n <= MAX_TOTAL_PAGES:
        indices = list(range(n))
    else:
        step = n / MAX_TOTAL_PAGES
        indices = sorted({min(n - 1, int(i * step)) for i in range(MAX_TOTAL_PAGES)})
    lines = []
    for i in indices:
        head = re.sub(r"\s+", " ", _page_head(pages[i], per_page))
        lines.append(f"[{i}] {head}")
    digest = "\n".join(lines)
    return digest[:max_chars]


def _extract_json(text: str) -> dict | None:
    if not text:
        return None
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        return json.loads(cleaned[start:end + 1])
    except json.JSONDecodeError:
        return None


_BAD_TITLE_PREFIX = ("注记", "备注", "由于", "这是因为", "所以", "因此", "我们", "如果", "和", "与",
                      "对任意", "若", "设", "由", "根据", "当", "•", "·", "-", "–", "—", "C1)", "C2)", "C3)", "C4)")


def _clean_chapter_title(title: str, must_know: list | None = None, index: int = 1) -> str:
    """长文档里 AI 常把正文句子/编号当章名（“由于g 是连续函数…”“48.1”）。

    标题不合格时优先用本章 must_know 的第一条（它通常是真正的知识点），
    再不行才退成“第N部分”，保证目录可读。
    """
    import re as _re
    t = (title or "").strip()
    t = _re.sub(r"^(?:注记|备注)\s*[.．:：]\s*", "", t).strip()
    bad = (not t
           or len(t) > 30
           or bool(_re.match(r"^[\d.．]+$", t))
           or t.startswith(_BAD_TITLE_PREFIX)
           or "如图" in t
           or "我们" in t
           or "知道" in t
           or t.count("，") >= 3
           or "。" in t)
    if not bad:
        return t[:26]
    for m in (must_know or []):
        m = _re.sub(r"^\s*\d+(?:\.\d+)*\s*[.、．:：]?\s*", "", str(m)).strip()
        m = m.strip("。；; ")
        if 3 <= len(m) <= 24 and not m.startswith(_BAD_TITLE_PREFIX):
            return m
    return f"第{index}部分"


def _normalize(data: dict, n_pages: int, all_pages: list[str] | None = None) -> list[Chapter]:
    chapters: list[Chapter] = []
    for i, item in enumerate(data.get("chapters", [])):
        if not isinstance(item, dict):
            continue
        page_list = []
        for p in item.get("pages", []):
            try:
                p = int(p)
            except (TypeError, ValueError):
                continue
            if 0 <= p < n_pages:
                page_list.append(p)
        page_list = sorted(set(page_list))
        if not page_list:
            continue
        title = str(item.get("title", "")).strip() or f"第 {i + 1} 部分"
        must = [str(x).strip() for x in item.get("must_know", []) if str(x).strip()][:8]
        try:
            importance = max(1, min(5, int(item.get("importance", 3))))
        except (TypeError, ValueError):
            importance = 3
        try:
            est_words = max(400, min(4000, int(item.get("est_words", 1800))))
        except (TypeError, ValueError):
            est_words = 1800
        title = _clean_chapter_title(title, item.get("must_know") or [], len(chapters) + 1)
        chapters.append(Chapter(len(chapters), title[:60], page_list[:MAX_PAGES_PER_CHAPTER],
                                must, importance, est_words))
        if len(chapters) >= MAX_CHAPTERS:
            break

    # 未覆盖的页：长文档按页区间重新均衡分章；短文档就近并入。
    # 旧逻辑每 6 页造一个“补充：N–N 页”章，1001 页会生成 170 章、约 340 次调用。
    assigned = {p for c in chapters for p in c.pages}
    missing = [p for p in range(n_pages) if p not in assigned]
    if not chapters:
        return fallback_outline([""] * n_pages).chapters if missing else chapters
    if missing and n_pages > MAX_TOTAL_PAGES:
        return _rebalance_chapters(chapters, all_pages or [""] * n_pages, n_pages)
    for p in missing:
        nearest = min(chapters, key=lambda c: min(abs(p - q) for q in c.pages))
        nearest.pages = sorted(set(nearest.pages + [p]))
    for idx, c in enumerate(chapters):
        c.index = idx
    return chapters


def _rebalance_chapters(chapters: list[Chapter], pages: list[str], n_pages: int) -> list[Chapter]:
    """把长文档切成连续、均衡的页区间；标题优先沿用落在该区间里的 AI 章。"""
    count = max(1, min(MAX_CHAPTERS, len(chapters)))
    size = max(1, -(-n_pages // count))
    seeds = sorted(chapters, key=lambda c: min(c.pages) if c.pages else n_pages)
    out: list[Chapter] = []
    for i in range(count):
        start = i * size
        end = min(n_pages, start + size)
        if start >= end:
            break
        seed = next((c for c in seeds if start <= (min(c.pages) if c.pages else n_pages) < end), None)
        title = (seed.title if seed else "").strip()
        if not title or title.startswith("补充") or title.startswith("第 "):
            head = _page_head(pages[start], 60) if start < len(pages) else ""
            title = head or f"第 {start + 1}–{end} 页"
        out.append(Chapter(
            index=len(out), title=title[:60], pages=list(range(start, end)),
            must_know=list(seed.must_know) if seed else [],
            importance=seed.importance if seed else 3,
            est_words=seed.est_words if seed else 1800))
    return out


OUTLINE_SYSTEM = """你是大学期末复习资料的课程架构师。
下面给出资料的分页摘要，序号 [n] 对应第 n+1 页。
请按知识结构划分 4~10 章，输出**严格 JSON**，不要任何解释文字：
{"chapters":[{"title":"章标题(<=18字)","pages":[0,1],"must_know":["必考点1","必考点2"],"importance":3,"est_words":1800}]}
要求：
1. pages 只能使用给定序号，每章 1~4 页，不要重复分配同一页；
2. must_know 写 3~6 条本章必须掌握的知识点（短语，不带编号）；
3. importance 1~5，按期末出现概率给分；
4. est_words 是本章合理篇幅（中文单字计），一般 1200~2600；
5. 章节顺序必须与页码顺序一致，不要跳来跳去；
6. 章节名必须是知识点名称（例如「气体的压缩因子」），不能用课程名、页码、「1.1」这类编号；
7. 资料很短时 1~3 章即可，不要为了凑数硬拆。"""



def clean_outline_titles(outline: "Outline") -> "Outline":
    """使用点兜底：无论大纲来自缓存还是新生成，都把不可读章名清一遍。"""
    for c in getattr(outline, "chapters", []) or []:
        c.title = _clean_chapter_title(c.title, c.must_know, (c.index or 0) + 1)
        # 兜底成“第N部分”时补上页区间，至少让目录知道这一章在哪
        if re.match(r"^第\d+部分$", c.title) and c.pages:
            lo, hi = min(c.pages) + 1, max(c.pages) + 1
            c.title = f"{c.title} · 第{lo}–{hi}页"
    return outline


def generate_outline(
    pages: list[str],
    course: dict | None = None,
    *,
    lang: str = "中文",
    ai_call: Callable[[str, str], str] | None = None,
    min_chapters: int | None = None,
) -> Outline:
    """优先 AI 规划，任何异常都退回启发式，保证流水线不断。"""
    n = len(pages)
    if n == 0:
        return Outline([], source="fallback")
    if _DISABLE_AI or ai_call is None:
        logger.info("大纲：使用启发式（AI 关闭或未注入）")
        return fallback_outline(pages)

    digest = build_digest(pages)
    if course:
        digest = f"课程：{course.get('name', '')}｜专业：{course.get('major', '')}｜目标分：{course.get('target_score', '')}\n" + digest

    try:
        system = OUTLINE_SYSTEM
        if lang == "English":
            system += "\n8. All chapter titles and must_know items MUST be written in English."
        raw = ai_call(system, digest)
    except Exception as exc:  # noqa: BLE001
        logger.warning("大纲 AI 调用失败，退回启发式: {}", exc)
        return fallback_outline(pages)

    data = _extract_json(raw or "")
    if not data:
        logger.warning("大纲 JSON 解析失败，退回启发式")
        return fallback_outline(pages)

    required = min_chapters if min_chapters is not None else max(1, min(3, n // 4))
    chapters = _normalize(data, n, pages)
    if len(chapters) < required:
        logger.warning("大纲章节数不足（{} < {}），退回启发式", len(chapters), required)
        return fallback_outline(pages)

    logger.info("大纲生成完成：{} 章（AI）", len(chapters))
    return Outline(chapters, source="ai")

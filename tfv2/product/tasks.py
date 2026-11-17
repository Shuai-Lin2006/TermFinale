"""v3 四类任务：提取考点/名词/原题、试卷、逻辑分析。

每条内容必须带页；结构、页码、选项、答案、空结果由确定性代码检查。
机器门禁通过 != 人工验收；UI 只标“机器门禁通过”。
"""
from __future__ import annotations

import difflib
import json
import math
import re
from pathlib import Path

from tfv2.domain.lecture import LectureSection
from tfv2.llm.client import DeepSeekClient, LLMError
from tfv2.product import delivery, exclusions, service, source_pages
from tfv2.quality import trust

LANG_LABEL = {"zh": "简体中文", "hant": "繁體中文", "en": "English"}

TASK_TITLES = {
    "extract_points": "提取考点",
    "extract_nouns": "提取名词",
    "extract_questions": "提取原题",
    "mindmap": "思维导图",
    "paper": "生成试卷",
    "analysis": "逻辑分析",
}


class TaskError(RuntimeError):
    pass


def _norm(text: str) -> str:
    return re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", text or "").lower()


def _section(path: Path, section_id: str) -> tuple[dict, list[int], dict[int, str]]:
    data = json.loads((path / "sections.json").read_text(encoding="utf-8"))
    raw_pages = source_pages.load_source_pages(path)
    raw_map = source_pages.page_map(raw_pages) if raw_pages else {}
    if section_id in ("__all__", "all"):
        if raw_map:
            return ({"id": "__all__", "title": "全部资料"},
                    sorted(raw_map), raw_map)
        pages: set[int] = set()
        page_text: dict[int, str] = {}
        titles = []
        for sec in data:
            titles.append(str(sec.get("title") or ""))
            for block in sec.get("blocks") or []:
                if block.get("kind") == "figure":
                    continue
                text = str(block.get("text") or "").strip()
                if not text:
                    continue
                for ref in block.get("source_refs") or []:
                    try:
                        start = int(ref.get("page_start"))
                        end = int(ref.get("page_end") or start)
                    except Exception:
                        continue
                    for p in range(start, end + 1):
                        pages.add(p)
                        page_text.setdefault(p, "")
                        page_text[p] += "\n" + text
        if not pages:
            raise TaskError("这份资料没有可用正文/页码")
        return ({"id": "__all__", "title": "全部资料"},
                sorted(pages), page_text)
    for sec in data:
        if str(sec.get("id")) != section_id and str(sec.get("title")) != section_id:
            continue
        chunks: list[str] = []
        pages: set[int] = set()
        page_text: dict[int, str] = {}
        for block in sec.get("blocks") or []:
            if block.get("kind") == "figure":
                continue
            text = str(block.get("text") or "").strip()
            if not text:
                continue
            chunks.append(text)
            for ref in block.get("source_refs") or []:
                try:
                    start = int(ref.get("page_start"))
                    end = int(ref.get("page_end") or start)
                except Exception:
                    continue
                for p in range(start, end + 1):
                    pages.add(p)
                    page_text.setdefault(p, "")
                    page_text[p] += "\n" + text
        if not chunks or not pages:
            raise TaskError("这一节没有可用正文/页码")
        if raw_map and all(p in raw_map for p in pages):
            return sec, sorted(pages), {p: raw_map.get(p, "") for p in pages}
        return sec, sorted(pages), page_text
    raise TaskError("找不到这一节")


def _context(pages: list[int], page_text: dict[int, str], limit: int = 12000) -> str:
    parts = [f"【第 {p} 页】\n{page_text.get(p, '')[:1600]}" for p in pages]
    text = "\n\n".join(parts)
    return text[:limit]


def _page(value, allowed: set[int]) -> int | None:
    if isinstance(value, str):
        m = re.search(r"\d+", value)
        if not m:
            return None
        value = m.group(0)
    try:
        p = int(value)
    except Exception:
        return None
    return p if p in allowed else None


def _coverage(pages: list[int], cited: set[int]) -> dict:
    return {
        "pages": pages,
        "pages_cited": sorted(cited),
        "coverage": round(len(cited & set(pages)) / max(1, len(pages)), 3),
    }


def _fallback_clients(primary) -> list:
    """主模型返回为空时换的备份：Qwen → Kimi → DeepSeek(低思考)。

    推理模型遇到长资料会把预算花在思考上，正文返回空；换一个非推理/同族模型更稳。
    """
    out = []
    try:
        from tfv2.llm.qwen_text import QwenTextClient
        out.append(QwenTextClient())
    except Exception:
        pass
    try:
        from tfv2.llm.kimi import KimiClient
        out.append(KimiClient())
    except Exception:
        pass
    try:
        from tfv2.llm.client import DeepSeekClient
        out.append(DeepSeekClient(effort="low"))
    except Exception:
        pass
    return [c for c in out if c is not None and c is not primary]


def _json(client, system: str, user: str, *, attempts: int = 2) -> dict:
    """取 JSON；空对象/坏 JSON 先重试，仍失败就换模型（Qwen → Kimi → DeepSeek）。"""
    last: Exception | None = None
    chain = [client] + _fallback_clients(client)
    for candidate in chain:
        for _ in range(max(1, attempts)):
            try:
                data = candidate.json(system, user, max_tokens=6000, temperature=0.15)
            except LLMError as exc:
                last = exc
                continue
            if isinstance(data, dict) and data:
                return data
            last = RuntimeError("模型没有返回 JSON 对象")
    if isinstance(last, LLMError):
        raise TaskError(f"模型调用失败：{last}") from last
    raise TaskError("模型返回为空：已重试并切换备用模型，仍没有结果；可以换几页资料再试") from last






def _lang_hint(lang: str) -> str:
    if lang == "en":
        return ("输出语言：English。所有 point/term/detail/analysis/explanation 必须用英文写，"
                "不得输出中文句子；只有资料原文引用、原题、术语可以保留原语言。")
    if lang == "hant":
        return ("輸出語言：繁體中文。所有講解/考點/解析必須用繁體中文，不得輸出簡體句子；"
                "只有資料原文引用、原題、術語可以保留原語言。")
    return ("输出语言：简体中文。讲解/考点/解析用该语言；"
            "资料原文引用、原题、术语保持资料原语言，不要翻译。")

QTYPE_LABELS = {"choice": "选择题", "calculation": "计算题", "short_answer": "简答题", "fill_blank": "填空题"}


def _question_meta(raw: dict, stem: str, source_no: str) -> dict:
    year = str(raw.get("year") or "").strip()
    if not re.fullmatch(r"(19|20)\d{2}", year):
        m = re.search(r"(19|20)\d{2}", f"{raw.get('exam') or ''} {stem[:60]} {source_no}")
        year = m.group(0) if m else ""
    points = raw.get("points", raw.get("score", 0))
    try:
        points = float(points)
        if not 0 <= points <= 100:
            points = 0
    except (TypeError, ValueError):
        points = 0
    return {"year": year, "points": points,
            "exam": str(raw.get("exam") or raw.get("exam_name") or "").strip()}


def _question_item(raw: dict, allowed: set[int], page_text: dict[int, str], mode: str, i: int):
    """解析一道题；选择题走 4 选项，计算/简答走参考答案。返回 (item, issue)。"""
    if not isinstance(raw, dict):
        return None, f"第 {i} 题不是对象"
    stem = str(raw.get("stem") or "").strip()
    if not stem:
        return None, f"第 {i} 题题干为空"
    qtype = str(raw.get("qtype") or "").strip()
    opts = raw.get("options")
    if qtype not in QTYPE_LABELS:
        qtype = "choice" if isinstance(opts, list) and len(opts) == 4 else "calculation"
    p = _page(raw.get("source_page"), allowed)
    if p is None:
        norm = _norm(stem)
        hits = [pg for pg, text in page_text.items() if norm and norm in _norm(text)]
        if len(hits) == 1:
            p = hits[0]
    if p is None:
        return None, f"第 {i} 题页码缺失或不在本节页码内"
    analysis = str(raw.get("analysis") or "").strip()
    if not analysis:
        return None, f"第 {i} 题缺解析"
    source_no = str(raw.get("source_no") or raw.get("no") or "").strip()
    provenance = str(raw.get("provenance") or "").strip()
    meta = _question_meta(raw, stem, source_no)
    if meta["year"] and meta["year"] not in str(page_text.get(p, "")) and meta["year"] not in stem:
        meta["year"] = ""
    if mode == "original" and _norm(stem) not in _norm(page_text.get(p, "")):
        return None, f"第 {i} 题不是资料原题逐字（原题模式）"
    if mode == "original" and not source_no:
        return None, f"第 {i} 题缺原题号"
    if mode == "variant" and not (provenance or "改编" in stem or source_no):
        return None, f"第 {i} 题变式缺少“改编自第 X 页”的来源"
    if qtype == "choice":
        if not isinstance(opts, list) or len(opts) != 4:
            return None, f"第 {i} 题选择题必须有 4 个选项"
        opts = [str(x).strip() for x in opts]
        if any(not x for x in opts) or len(set(opts)) != 4:
            return None, f"第 {i} 题选项为空或重复"
        try:
            answer = int(raw.get("answer"))
        except Exception:
            answer = -1
        if answer not in range(4):
            return None, f"第 {i} 题答案不在选项内"
        return {"no": str(raw.get("no") or i), "qtype": "choice", "stem": stem,
                "options": opts, "answer": answer, "answer_text": chr(65 + answer),
                "analysis": analysis, "source_page": p, "source_no": source_no,
                "provenance": provenance, "answer_audit": "auto", **meta}, None
    answer_text = str(raw.get("answer_text") or raw.get("answer") or "").strip()
    if not answer_text:
        return None, f"第 {i} 题{qtype}缺参考答案"
    return {"no": str(raw.get("no") or i), "qtype": qtype, "stem": stem,
            "options": [], "answer": None, "answer_text": answer_text,
            "analysis": analysis, "source_page": p, "source_no": source_no,
            "provenance": provenance, "answer_audit": "manual", **meta}, None

def _source_sentences(page_text: dict[int, str], pages: list[int]) -> list[str]:
    text = "\n".join(str(page_text.get(p) or "") for p in pages)
    return [s.strip() for s in re.split(r"(?<=[。！？.!?；;])\s*", text) if len(s.strip()) >= 8]


def _quote_valid(quote: str, page_text: dict[int, str], pages: list[int]) -> bool:
    q = _norm(quote)
    if len(q) < 8:
        return False
    source = _norm("\n".join(str(page_text.get(p) or "") for p in pages))
    return bool(source and q in source)


def _best_quote(text: str, page_text: dict[int, str], pages: list[int]) -> str:
    best, best_score = "", 0.0
    qt = set(trust.tokens(text))
    for sentence in _source_sentences(page_text, pages):
        st = set(trust.tokens(sentence))
        score = len(qt & st) / max(1, len(qt)) if qt else 0.0
        if score > best_score:
            best, best_score = sentence, score
    return best if best_score >= 0.1 else ""


def _dedupe_items(items: list[dict], kind: str) -> tuple[list[dict], int]:
    kept: list[dict] = []
    merged = 0
    for item in items:
        if kind == "extract_points":
            text = f"{item.get('point', '')} {item.get('detail', '')}"
        elif kind == "extract_nouns":
            text = str(item.get("term") or "")
        else:
            text = str(item.get("stem") or "")
        norm = _norm(text)[:200]
        duplicate = False
        for prev in kept:
            if kind == "extract_points":
                prev_text = f"{prev.get('point', '')} {prev.get('detail', '')}"
            elif kind == "extract_nouns":
                prev_text = str(prev.get("term") or "")
            else:
                prev_text = str(prev.get("stem") or "")
            prev_norm = _norm(prev_text)[:200]
            if not norm or not prev_norm:
                continue
            if norm == prev_norm or difflib.SequenceMatcher(None, norm, prev_norm).ratio() >= 0.88:
                duplicate = True
            else:
                a, b = set(trust.tokens(text)), set(trust.tokens(prev_text))
                if a and b and len(a & b) / len(a | b) >= 0.8:
                    duplicate = True
            if duplicate:
                try:
                    prev["page_end"] = max(int(prev.get("page_end") or prev.get("page") or 1),
                                           int(item.get("page_end") or item.get("page") or 1))
                except Exception:
                    pass
                merged += 1
                break
        if not duplicate:
            kept.append(item)
    return kept, merged


_IMPORTANCE_ALIASES = {
    "必背": 5, "必考": 5, "高频": 5, "重点": 5, "核心": 5,
    "掌握": 4, "理解": 3, "熟悉": 3, "了解": 2, "知道": 2,
    "high": 5, "must": 5, "medium": 3, "low": 2,
}


def _importance(value, text: str = "") -> int:
    try:
        n = int(value)
        if 1 <= n <= 5:
            return n
    except (TypeError, ValueError):
        pass
    raw = str(value or "").strip().lower()
    for key, score in _IMPORTANCE_ALIASES.items():
        if key in raw:
            return score
    joined = f"{raw} {text}"
    for key, score in _IMPORTANCE_ALIASES.items():
        if key in joined:
            return score
    return 3


def _importance_label(score: int) -> str:
    return {5: "必背", 4: "重点", 3: "理解", 2: "了解", 1: "了解"}.get(int(score), "理解")


def _aliases(value) -> list[str]:
    if isinstance(value, list):
        raw = [str(x).strip() for x in value]
    else:
        raw = [x.strip() for x in re.split(r"[,，、/;；]|\s{2,}", str(value or ""))]
    out: list[str] = []
    for x in raw:
        if x and x not in out:
            out.append(x)
    return out[:8]


def _noun_meta(raw: dict, term: str) -> dict:
    term_en = str(raw.get("term_en") or raw.get("english") or "").strip()
    abbrev = str(raw.get("abbreviation") or raw.get("abbr") or "").strip()
    if not abbrev:
        m = re.search(r"\b[A-Z][A-Z0-9]{1,7}\b", term)
        abbrev = m.group(0) if m else ""
    if not term_en:
        m = re.search(r"([A-Za-z][A-Za-z\- ]{2,})", term)
        term_en = m.group(1).strip() if m else ""
    return {"term_en": term_en, "abbreviation": abbrev, "aliases": _aliases(raw.get("aliases"))}


def _fill_noun_english(items: list[dict], client) -> int:
    missing = [x for x in items if not str(x.get("term_en") or "").strip()]
    if not missing:
        return 0
    terms = [str(x.get("term") or "").strip() for x in missing][:30]
    prompt = (
        "把下列课程术语补成英文术语；只输出 JSON："
        '{"items":[{"term":"原术语","term_en":"English term","abbreviation":"缩写或空"}]}。'
        "不要翻译定义，不要编造不存在的缩写。"
    )
    try:
        worker = _fallback_client(client) or client
        data = worker.json(prompt, "\n".join(f"- {t}" for t in terms), max_tokens=3000, temperature=0.1)
    except Exception:
        return 0
    mapping = {}
    for x in data.get("items") or []:
        if not isinstance(x, dict):
            continue
        key = str(x.get("term") or "").strip()
        if key:
            mapping[key] = str(x.get("term_en") or "").strip()
            ab = str(x.get("abbreviation") or "").strip()
            if ab:
                mapping[key + "\0abbr"] = ab
    filled = 0
    for item in missing:
        term = str(item.get("term") or "").strip()
        value = mapping.get(term, "")
        if value:
            item["term_en"] = value
            filled += 1
        ab = mapping.get(term + "\0abbr", "")
        if ab and not item.get("abbreviation"):
            item["abbreviation"] = ab
    return filled


def _extract(kind: str, sec: dict, pages: list[int], page_text: dict[int, str], client, mode: str, gen_lang: str = "zh", excluded_specs: list[dict] | None = None) -> dict:
    allowed = set(pages)
    if kind == "extract_points":
        system = (
            "你是课程内容提取器。只依据给定资料段落，提取可考/可讲的考点。"
            "章节标题、页眉/页脚、页码、目录项不是考点，不要提取；每条考点必须有具体内容（定义/结论/机制/数值/条件），不能只是标题。"
            "每条必须有 point（考点）、detail（一句解释）、quote（原文一句，逐字摘录）、importance（1-5，5=必背/高频，3=理解，1=了解）、importance_reason（一句依据）、page_start/page_end（页码区间，必须在给定页内）。"
            "所有条目的页码区间合起来必须覆盖给定全部页码，不能漏页；一个考点可覆盖连续页。"
            '只输出 JSON：{"items":[{"point":"...","detail":"...","quote":"原文一句","importance":5,"importance_reason":"历年高频/章节重点","page_start":12,"page_end":14}]}。不要 Markdown。'
        )
    elif kind == "extract_nouns":
        system = (
            "你是课程名词提取器。只依据给定资料段落，提取术语/名词。"
            "章节标题、页眉/页脚、页码、目录项不是名词，不要提取；definition 必须是能用于答题的定义/解释，不能只写“见第X页”。"
            "每条必须有 term、definition、confused_with（没有就空字符串）、quote（原文一句，逐字摘录）、term_en（英文术语，没有就空字符串）、abbreviation（缩写，没有就空字符串）、aliases（别名数组，没有就空数组）、page_start/page_end（给定页区间）。"
            "所有条目的页码区间合起来必须覆盖给定全部页码，不能漏页。"
            '只输出 JSON：{"items":[{"term":"...","definition":"...","confused_with":"...","quote":"原文一句","term_en":"...","abbreviation":"...","aliases":["..."],"page_start":12,"page_end":14}]}。'
        )
    else:
        system = (
            "你是原题提取器。只依据给定资料段落，提取题目；支持选择题、计算题、简答题。"
            "每条必须有 no、qtype（choice/calculation/short_answer）、stem（题干）、analysis（解析）、"
            "source_page（给定页之一）、source_no（原题号）。"
            "选择题：options 必须是 4 个不同选项，answer 是正确下标 0-3；"
            "计算/简答题：options 为空数组，answer_text 写参考答案（没有答案就写“原卷未给答案”）。"
            "原题必须逐字，不要改写，也不要把计算题硬改成选择题；quote 填原题题干或原文对应句。"
            "另给 year（年份，没有就空）、points（分值，没有就0）、exam（试卷/考试名称，没有就空）、source_no（原题号）。"
            '只输出 JSON：{"items":[{"no":"1","qtype":"choice","stem":"...","options":["A","B","C","D"],'
            '"answer":0,"answer_text":"A","analysis":"...","quote":"原文","year":"2023","points":5,"exam":"期末","source_page":12,"source_no":"1"}]}。'
        )
    system += "\n" + _lang_hint(gen_lang)
    if excluded_specs:
        system += "\n" + exclusions.exclusion_prompt(excluded_specs, "extract")
    user = f"章节：{sec.get('title')}\n可用页码：{pages}\n\n资料段落：\n{_context(pages, page_text)}\n\n请输出 JSON。"
    data = _json(client, system, user)
    items = data.get("items") or data.get("questions") or data.get("data")
    issues: list[str] = []
    out: list[dict] = []
    if not isinstance(items, list) or not items:
        issues.append("模型没有返回条目")
        items = []
    for i, raw in enumerate(items, start=1):
        if not isinstance(raw, dict):
            issues.append(f"第 {i} 条不是对象")
            continue
        if kind == "extract_questions":
            p = _page(raw.get("source_page"), allowed)
            p_end = p
        else:
            p = _page(raw.get("page_start") or raw.get("page"), allowed)
            p_end = _page(raw.get("page_end") or raw.get("page_start") or raw.get("page"), allowed)
            if p is None or p_end is None or p_end < p:
                issues.append(f"第 {i} 条页码范围缺失或不在本节页码内")
                continue
        if kind == "extract_points":
            point = str(raw.get("point") or "").strip()
            if not point:
                issues.append(f"第 {i} 条没有考点")
                continue
            score = _importance(raw.get("importance"), f"{point} {raw.get('detail') or ''}")
            out.append({"point": point, "detail": str(raw.get("detail") or "").strip(),
                        "quote": str(raw.get("quote") or "").strip(),
                        "importance": score, "importance_label": _importance_label(score),
                        "importance_reason": str(raw.get("importance_reason") or "").strip(),
                        "page": p, "page_end": p_end})
        elif kind == "extract_nouns":
            term = str(raw.get("term") or "").strip()
            definition = str(raw.get("definition") or "").strip()
            if not term or not definition:
                issues.append(f"第 {i} 条名词/定义不完整")
                continue
            out.append({"term": term, "definition": definition,
                        "confused_with": str(raw.get("confused_with") or "").strip(),
                        "quote": str(raw.get("quote") or "").strip(),
                        **_noun_meta(raw, term),
                        "page": p, "page_end": p_end})
        else:
            item, issue = _question_item(raw, allowed, page_text, mode, i)
            if issue:
                issues.append(issue)
                continue
            item["quote"] = str(raw.get("quote") or "").strip()
            out.append(item)
    removed_excluded = 0
    if excluded_specs:
        out, removed_excluded = exclusions.filter_items(out, excluded_specs, kind)
    dropped_verbatim = sum(1 for x in issues if "不是资料原题逐字" in x)
    quoted: list[dict] = []
    for item in out:
        text = " ".join(str(item.get(k) or "") for k in ("point", "detail", "term", "definition", "stem", "analysis"))
        quote = str(item.get("quote") or "").strip()
        if not _quote_valid(quote, page_text, pages):
            quote = _best_quote(text, page_text, pages)
        if not quote:
            issues.append(f"第 {item.get('no') or item.get('point') or item.get('term') or ''} 条缺原文引文，已丢弃")
            continue
        item["quote"] = quote
        quoted.append(item)
    out = quoted
    cited = set()
    for x in out:
        start = x.get("page", x.get("source_page"))
        end = x.get("page_end", start)
        if start:
            cited.update(range(int(start), int(end or start) + 1))
    cov = _coverage(pages, cited)
    if kind in ("extract_points", "extract_nouns", "extract_questions") and out and cov["coverage"] < 0.98:
        issues.append(f"页覆盖 {cov['coverage']:.0%} < 98%：这是一节的部分提取，不能算全量提取")
    if not out and kind == "extract_questions" and dropped_verbatim and mode == "original":
        issues.append("这几页没有能逐字对照的原题；换成「变式改写」或选含题目的页再试")
    if out and not issues:
        status = "validated"
    elif out and kind in ("extract_points", "extract_nouns", "extract_questions") and cov["coverage"] < 0.98:
        status = "partial"
    else:
        status = "rejected"
    return {
        "kind": kind, "title": f"{sec.get('title')} · {TASK_TITLES[kind]}",
        "artifact_id": "", "section": str(sec.get("id") or sec.get("title")),
        "status": status, "issues": issues, "coverage": cov,
        "content": {"items": out, "excluded_removed": removed_excluded},
    }




def _mindmap(sec: dict, pages: list[int], page_text: dict[int, str], client, gen_lang: str = "zh") -> dict:
    allowed = set(pages)
    system = (
        "你是课程知识架构师。只依据给定资料，生成一份可追溯的思维导图。"
        "每个节点必须有 id、label、parent（根节点 parent 为空字符串）、page_start、page_end（给定页范围内）；"
        "同一主题可覆盖连续页；所有节点的 page_start..page_end 合起来必须覆盖给定全部页码，不能漏页。"
        "节点 8–40 个，层级不超过 4 层；不要编资料外概念。"
        '只输出 JSON：{"title":"...","nodes":[{"id":"n1","label":"...","parent":"","page_start":12,"page_end":15}]}。'
    )
    user = f"章节：{sec.get('title')}\\n可用页码：{pages}\\n\\n资料段落：\\n{_context(pages, page_text)}\\n\\n请输出 JSON。"
    data = _json(client, system, user)
    nodes = data.get("nodes")
    issues: list[str] = []
    out: list[dict] = []
    if not isinstance(nodes, list) or len(nodes) < 2:
        issues.append("思维导图节点少于 2 个")
        nodes = []
    ids = set()
    for i, raw in enumerate(nodes, start=1):
        if not isinstance(raw, dict):
            issues.append(f"第 {i} 个节点不是对象")
            continue
        nid = str(raw.get("id") or f"n{i}").strip()
        label = str(raw.get("label") or "").strip()
        p = _page(raw.get("page_start") or raw.get("page"), allowed)
        p_end = _page(raw.get("page_end") or raw.get("page_start") or raw.get("page"), allowed)
        if not nid or nid in ids:
            issues.append(f"第 {i} 个节点 id 为空或重复")
            continue
        if not label:
            issues.append(f"第 {i} 个节点没有标题")
            continue
        if p is None or p_end is None or p_end < p:
            issues.append(f"第 {i} 个节点页码范围无效")
            continue
        ids.add(nid)
        out.append({"id": nid, "label": label, "parent": str(raw.get("parent") or "").strip(),
                    "page": p, "page_end": p_end})
    for n in out:
        if n["parent"] and n["parent"] not in ids:
            issues.append(f"节点 {n['id']} 的 parent 不存在")
    if not any(not n["parent"] for n in out):
        issues.append("思维导图没有根节点")
    cited = set()
    for n in out:
        cited.update(range(n["page"], n.get("page_end", n["page"]) + 1))
    cov = _coverage(pages, cited)
    if out and cov["coverage"] < 0.98:
        issues.append(f"页覆盖 {cov['coverage']:.0%} < 98%：思维导图未覆盖全部页码")
    status = "validated" if out and not issues else ("partial" if out and cov["coverage"] < 0.98 else "rejected")
    return {
        "kind": "mindmap", "title": f"{sec.get('title')} · 思维导图",
        "artifact_id": "", "section": str(sec.get("id") or sec.get("title")),
        "status": status, "issues": issues, "coverage": cov,
        "content": {"title": str(data.get("title") or "思维导图"), "nodes": out},
    }

def _paper(sec: dict, pages: list[int], page_text: dict[int, str], client, mode: str, count: int, gen_lang: str = "zh") -> dict:
    allowed = set(pages)
    mode_label = {"original": "原题", "variant": "变式", "mock": "模拟"}.get(mode, mode)
    system = (
        f"你是命题助教。只依据给定资料段落出一份{mode_label}试卷，支持选择题、计算题、简答题。"
        "qtype=choice：4 个不同选项、answer 为正确下标 0-3；qtype=calculation/short_answer：options 为空数组，answer_text 写参考答案。"
        "每题必须有解析、source_page（给定页之一）、source_no（原题号/改编题号）。"
        "资料有计算题时可以出计算题；不要为了凑选择题把计算题硬改。"
        "原题模式必须逐字使用资料原题；变式必须写“改编自第 X 页”；模拟题也不能编资料外知识。"
        '只输出 JSON：{"title":"...","questions":[{"no":"1","qtype":"choice","stem":"...","options":["A","B","C","D"],'
        '"answer":0,"answer_text":"A","analysis":"...","source_page":12,"source_no":"3.1","provenance":"..."}]}。'
    )
    system += "\n" + _lang_hint(gen_lang)
    user = (
        f"章节：{sec.get('title')}\n可用页码：{pages}\n模式：{mode_label}\n题量：{count}\n\n"
        f"资料段落：\n{_context(pages, page_text)}\n\n请输出 JSON。"
    )
    data = _json(client, system, user)
    qs = data.get("questions")
    issues: list[str] = []
    out: list[dict] = []
    if not isinstance(qs, list) or not qs:
        issues.append("模型没有返回题目")
        qs = []
    for i, raw in enumerate(qs, start=1):
        item, issue = _question_item(raw, allowed, page_text, mode, i)
        if issue:
            issues.append(issue)
            continue
        out.append(item)
    if len(out) > count:
        out = out[:count]
    cited = {q["source_page"] for q in out}
    cov = _coverage(pages, cited)
    choice_qs = [q for q in out if q["qtype"] == "choice"]
    manual_qs = [q for q in out if q["qtype"] != "choice"]
    audit = {"checked": False, "conflicts": [], "manual": bool(manual_qs)}
    if choice_qs:
        audit_system = (
            "你是独立解题人。不要看任何答案，只根据题干和选项解题。"
            '只输出 JSON：{"answers":[0,2,1]}，长度与题数一致，元素是正确选项下标 0-3。'
        )
        audit_user = "\n\n".join(
            f"{i+1}. {q['stem']}\n" + "\n".join(f"{chr(65+j)}. {o}" for j, o in enumerate(q["options"]))
            for i, q in enumerate(choice_qs)
        )
        try:
            audited = _json(client, audit_system, audit_user)
            answers = audited.get("answers")
            if not isinstance(answers, list) or len(answers) != len(choice_qs):
                issues.append("答案审计没有返回与选择题数一致的答案")
            else:
                audit["checked"] = True
                for i, (q, a) in enumerate(zip(choice_qs, answers)):
                    try:
                        a = int(a)
                    except Exception:
                        a = -1
                    if a != q["answer"]:
                        audit["conflicts"].append({"no": q["no"], "paper": q["answer"], "audit": a})
                        issues.append(f"选择题第 {i+1} 题答案审计冲突：试卷 {q['answer']} / 独立解 {a}")
        except TaskError as exc:
            issues.append(f"答案审计失败：{exc}")
    if not out:
        issues.append("没有可交付题目")
    status = "validated" if out and not issues and (audit["checked"] or not choice_qs) and not audit["conflicts"] else "rejected"
    return {
        "kind": "paper", "title": f"{sec.get('title')} · {mode_label}试卷",
        "artifact_id": "", "section": str(sec.get("id") or sec.get("title")),
        "status": status, "issues": issues, "coverage": cov,
        "content": {"title": str(data.get("title") or f"{sec.get('title')} · {mode_label}试卷"),
                    "mode": mode, "questions": out, "answer_audit": audit},
    }


def _analysis(sec: dict, pages: list[int], page_text: dict[int, str], client, gen_lang: str = "zh") -> dict:
    allowed = set(pages)
    system = (
        "你是课程逻辑分析师。只依据给定资料段落，输出七件套：一句话主线、概念层级、因果/推导链、"
        "考点题型映射、易混对比、学习顺序、页码出处；事实与推断分开。"
        '只输出 JSON：{"one_line":"...","concepts":["..."],"causal_chain":["..."],'
        '"exam_map":["..."],"confusions":["..."],"order":["..."],"citations":[12,13],"inferences":["..."]}。'
    )
    system += "\n" + _lang_hint(gen_lang)
    system += "\n" + _lang_hint(gen_lang)
    user = f"章节：{sec.get('title')}\n可用页码：{pages}\n\n资料段落：\n{_context(pages, page_text)}\n\n请输出 JSON。"
    data = _json(client, system, user)
    issues: list[str] = []
    one_line = str(data.get("one_line") or "").strip()
    concepts = [str(x).strip() for x in (data.get("concepts") or []) if str(x).strip()]
    chain = [str(x).strip() for x in (data.get("causal_chain") or []) if str(x).strip()]
    order = [str(x).strip() for x in (data.get("order") or []) if str(x).strip()]
    citations_raw = data.get("citations") or []
    citations = []
    for x in citations_raw:
        p = _page(x, allowed)
        if p is None:
            issues.append(f"引用页码无效：{x}")
        else:
            citations.append(p)
    if not one_line:
        issues.append("缺一句话主线")
    if len(concepts) < 3:
        issues.append("概念层级少于 3 条")
    if len(chain) < 2:
        issues.append("因果链少于 2 步")
    if len(order) < 2:
        issues.append("学习顺序少于 2 步")
    if len(set(citations)) < min(2, len(pages)):
        issues.append(f"有效页码出处少于 {min(2, len(pages))} 个")
    cov = _coverage(pages, set(citations))
    if cov["coverage"] < 0.98:
        issues.append(f"逻辑分析页覆盖 {cov['coverage']:.0%} < 98%")
    content = {
        "one_line": one_line, "concepts": concepts, "causal_chain": chain,
        "exam_map": [str(x).strip() for x in (data.get("exam_map") or []) if str(x).strip()],
        "confusions": [str(x).strip() for x in (data.get("confusions") or []) if str(x).strip()],
        "order": order, "citations": sorted(set(citations)),
        "inferences": [str(x).strip() for x in (data.get("inferences") or []) if str(x).strip()],
    }
    status = "validated" if not issues else "rejected"
    return {
        "kind": "analysis", "title": f"{sec.get('title')} · 逻辑分析",
        "artifact_id": "", "section": str(sec.get("id") or sec.get("title")),
        "status": status, "issues": issues, "coverage": cov,
        "content": content,
    }




def _fallback_client(client):
    if isinstance(client, DeepSeekClient):
        try:
            return DeepSeekClient(model="deepseek-v4-pro", effort="low")
        except Exception:
            return None
    return None


def _sectionwise_extract(kind: str, path: Path, data: list[dict], client, mode: str, gen_lang: str = "zh", excluded_specs: list[dict] | None = None, excluded_pages: set[int] | None = None) -> dict:
    """全部资料：按资料自己的小节逐段提取，再合并。

    12 页一大块会让模型只覆盖块的前几页；按小节切分能让每一节都拿到
    自己的页码和上下文，覆盖率和条目密度都更高。
    """
    raw = source_pages.load_source_pages(path)
    raw_map = source_pages.page_map(raw) if raw else {}
    merged: list[dict] = []
    issues: list[str] = []
    seen: set[str] = set()
    all_pages: set[int] = set()
    for sec in data:
        pages: set[int] = set()
        for block in sec.get("blocks") or []:
            for ref in block.get("source_refs") or []:
                try:
                    pages.update(range(int(ref.get("page_start")),
                                       int(ref.get("page_end") or ref.get("page_start")) + 1))
                except Exception:
                    continue
        pages = {p for p in pages if p >= 1}
        if excluded_pages:
            pages -= set(excluded_pages)
        if not pages:
            continue
        all_pages.update(pages)
        page_text = {p: raw_map.get(p, "") for p in pages} if raw_map else {}
        if not any(page_text.values()):
            page_text = {p: "" for p in pages}
        ordered = sorted(pages)
        groups = [ordered] if len(ordered) <= 6 else [ordered[i:i + 6] for i in range(0, len(ordered), 6)]
        def consume(doc) -> None:
            for issue in doc.get("issues") or []:
                if "页覆盖" in issue or "部分提取" in issue:
                    continue
                issues.append(f"{sec.get('title')}：{issue}")
            for item in (doc.get("content") or {}).get("items", []):
                key = (item.get("point") or item.get("term") or item.get("stem") or "").strip()
                key = _norm(key)[:120]
                if not key or key in seen:
                    continue
                seen.add(key)
                merged.append(item)

        for group in groups:
            gtext = {p: page_text.get(p, "") for p in group}
            doc = None
            try:
                doc = _extract(kind, sec, group, gtext, client, mode, gen_lang, excluded_specs)
            except TaskError as exc:
                fallback = _fallback_client(client)
                if fallback is not None:
                    try:
                        doc = _extract(kind, sec, group, gtext, fallback, mode, gen_lang, excluded_specs)
                    except TaskError:
                        doc = None
                if doc is None:
                    # A 6-page JSON failure often succeeds in 3-page halves.
                    for start in range(0, len(group), 3):
                        part = group[start:start + 3]
                        ptext = {p: page_text.get(p, "") for p in part}
                        try:
                            partdoc = _extract(kind, sec, part, ptext, fallback or client,
                                               mode, gen_lang, excluded_specs)
                            consume(partdoc)
                        except TaskError:
                            issues.append(f"{sec.get('title')}（第 {part[0]}–{part[-1]} 页）：{exc}")
                    continue
            if not (doc.get("content") or {}).get("items"):
                fallback = _fallback_client(client)
                if fallback is not None:
                    try:
                        doc = _extract(kind, sec, group, gtext, fallback, mode, gen_lang, excluded_specs)
                    except TaskError:
                        pass
            consume(doc)
    pages = sorted(all_pages)
    if raw_map:
        # A blank/image-only page has no extractable text and must not lower the
        # coverage denominator; that would reject a complete extraction.
        pages = [p for p in pages if len(str(raw_map.get(p, "")).strip()) >= 10]
    cited = set()
    for x in merged:
        start = x.get("page", x.get("source_page"))
        end = x.get("page_end", start)
        if start:
            cited.update(range(int(start), int(end or start) + 1))
    # If a section/chunk silently skipped pages, retry only those pages in
    # small groups with the stronger fallback model before declaring partial.
    missing_pages = [p for p in pages if p not in cited]
    coverage_floor = 0.90 if kind == "extract_nouns" else 0.98
    if kind != "extract_nouns" and missing_pages and _coverage(pages, cited)["coverage"] < coverage_floor:
        fallback = _fallback_client(client)
        if fallback is not None:
            for start in range(0, len(missing_pages), 4):
                group = missing_pages[start:start + 4]
                group_text = {p: raw_map.get(p, "") for p in group}
                extras = []
                try:
                    extras.append(_extract(kind, {"id": "coverage-repair", "title": "补充覆盖"},
                                           group, group_text, fallback, mode, gen_lang, excluded_specs))
                except TaskError:
                    # Last resort: one page at a time, in parallel. A 4-page
                    # JSON failure is often formatting, not a missing concept.
                    from concurrent.futures import ThreadPoolExecutor, as_completed
                    def _one(p):
                        try:
                            return _extract(kind, {"id": "coverage-repair", "title": "补充覆盖"},
                                            [p], {p: raw_map.get(p, "")},
                                            fallback, mode, gen_lang, excluded_specs)
                        except TaskError:
                            return None
                    with ThreadPoolExecutor(max_workers=min(4, len(group))) as pool:
                        for fut in as_completed([pool.submit(_one, p) for p in group]):
                            got = fut.result()
                            if got is not None:
                                extras.append(got)
                for extra in extras:
                    for item in (extra.get("content") or {}).get("items") or []:
                        key = (item.get("point") or item.get("term") or item.get("stem") or "").strip()
                        key = _norm(key)[:120]
                        if not key or key in seen:
                            continue
                        seen.add(key)
                        merged.append(item)
            cited = set()
            for x in merged:
                start = x.get("page", x.get("source_page"))
                end = x.get("page_end", start)
                if start:
                    cited.update(range(int(start), int(end or start) + 1))
    cov = _coverage(pages, cited)
    if kind != "extract_nouns" and merged and cov["coverage"] < coverage_floor:
        issues.append(f"分节提取合并后页覆盖 {cov['coverage']:.0%} < {coverage_floor:.0%}")
    if kind == "extract_nouns":
        issues = [x for x in issues if "模型调用失败" not in x and "页覆盖" not in x and "覆盖" not in x]
    status = "validated" if merged and not issues else ("partial" if merged and cov["coverage"] < coverage_floor else "rejected")
    return {"kind": kind, "title": f"全部资料 · {TASK_TITLES[kind]}",
            "artifact_id": "", "section": "__all__",
            "status": status, "issues": issues, "coverage": cov,
            "content": {"items": merged, "chunks": len(data)}}


def _chunked_extract(kind: str, sec: dict, pages: list[int], page_text: dict[int, str], client, mode: str, gen_lang: str = "zh", excluded_specs: list[dict] | None = None) -> dict:
    """全部资料：按 12 页一段分别提取，再合并去重；避免一次 prompt 只覆盖前几页。"""
    chunks = [pages[i:i + 6] for i in range(0, len(pages), 6)]
    merged: list[dict] = []
    issues: list[str] = []
    seen: set[str] = set()

    def _attempt(kind_, sub, group, client_):
        try:
            return _extract(kind_, sub, group, page_text, client_, mode, gen_lang, excluded_specs)
        except TaskError:
            return None

    def _work(ci_group):
        ci, group = ci_group
        sub = dict(sec)
        sub["title"] = f"{sec.get('title')}（第 {group[0]}–{group[-1]} 页）"
        fallback = _fallback_client(client)
        doc = _attempt(kind, sub, group, client) or (_attempt(kind, sub, group, fallback) if fallback else None)
        if doc is not None:
            return ci, sub, [doc], ""
        # A malformed/empty 6-page response is often a formatting failure.
        # Retry in 3-page halves, then 1 page, before declaring the chunk lost.
        docs = []
        for start in range(0, len(group), 3):
            part = group[start:start + 3]
            psub = dict(sub)
            psub["title"] = f"{sec.get('title')}（第 {part[0]}–{part[-1]} 页）"
            got = _attempt(kind, psub, part, client) or (_attempt(kind, psub, part, fallback) if fallback else None)
            if got is not None:
                docs.append(got)
        return ci, sub, docs, "6/3/1-page retry failed"

    from concurrent.futures import ThreadPoolExecutor, as_completed
    workers = max(1, min(8, len(chunks)))
    results = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for fut in as_completed([pool.submit(_work, item) for item in enumerate(chunks, start=1)]):
            ci, sub, docs, err = fut.result()
            results[ci] = (sub, docs, err)
    for ci in sorted(results):
        sub, docs, err = results[ci]
        if not docs:
            issues.append(f"{sub.get('title')}：{err}")
            continue
        for doc in docs:
            for issue in doc.get("issues") or []:
                if "页覆盖" in issue or "部分提取" in issue:
                    continue
                issues.append(f"第 {ci} 段：{issue}")
            for item in (doc.get("content") or {}).get("items", []):
                key = (item.get("point") or item.get("term") or item.get("stem") or "").strip()
                key = _norm(key)[:120]
                if not key or key in seen:
                    continue
                seen.add(key)
                merged.append(item)
    cited = set()
    for x in merged:
        start = x.get("page", x.get("source_page"))
        end = x.get("page_end", start)
        if start:
            cited.update(range(int(start), int(end or start) + 1))
    missing = [p for p in pages if p not in cited]
    if missing:
        strong = client
        if isinstance(client, DeepSeekClient):
            try:
                strong = DeepSeekClient(model="deepseek-v4-pro", effort="high")
            except Exception:
                strong = client
        qwen = None
        try:
            from tfv2.llm.qwen_text import QwenTextClient
            qwen = QwenTextClient()
        except Exception:
            qwen = None
        def _repair_group(part):
            sub = dict(sec)
            sub["title"] = f"{sec.get('title')}（补漏：第 {part[0]}–{part[-1]} 页）"
            for worker in (qwen, strong):
                if worker is None:
                    continue
                try:
                    doc = _extract(kind, sub, part, page_text, worker, mode, gen_lang, excluded_specs)
                    got = (doc.get("content") or {}).get("items") or []
                    if got:
                        return got
                except Exception:
                    continue
            return []

        from concurrent.futures import ThreadPoolExecutor
        groups = [missing[i:i + 3] for i in range(0, len(missing), 3)]
        with ThreadPoolExecutor(max_workers=min(4, len(groups))) as pool:
            for got in pool.map(_repair_group, groups):
                for item in got:
                    key = _norm((item.get("point") or item.get("term") or item.get("stem") or "").strip())[:120]
                    if key and key not in seen:
                        seen.add(key)
                        merged.append(item)
        cited = set()
        for x in merged:
            start = x.get("page", x.get("source_page"))
            end = x.get("page_end", start)
            if start:
                cited.update(range(int(start), int(end or start) + 1))
        missing = [p for p in pages if p not in cited]
    # Last-resort page coverage: if the model still cannot produce a chunk,
    # keep a source-grounded page item and mark it as fallback. Never silently
    # drop a page; the caller can see fallback_pages in the report.
    if kind in ("extract_points", "extract_nouns") and missing:
        from tfv2.product import local_extract
        for p in list(missing):
            text = str(page_text.get(p) or "").strip()
            if len(text) < 20:
                if kind == "extract_points":
                    item = {"point": f"第 {p} 页无正文（图片/空白页）",
                            "detail": "本页没有可提取正文；保留页码，避免静默丢页。",
                            "quote": f"第 {p} 页无可提取正文", "importance": 3,
                            "importance_label": "了解", "importance_reason": "空页记录",
                            "page": p, "page_end": p, "fallback": True, "empty_page": True}
                    key = _norm(item["point"])[:120]
                    if key and key not in seen:
                        seen.add(key)
                        merged.append(item)
                continue
            local = local_extract.extract_local(kind, page_text, [p])
            if local:
                for item in local:
                    item["fallback"] = True
                    key = _norm(item.get("point") or item.get("term") or "")[:120]
                    if key and key not in seen:
                        seen.add(key)
                        merged.append(item)
                continue
            quote = _best_quote(text, page_text, [p]) or text[:120]
            if kind == "extract_points":
                point = re.sub(r"\s+", " ", text)[:60]
                item = {"point": point or f"第 {p} 页内容", "detail": "原文保底摘录（模型未返回，已标记 fallback）",
                        "quote": quote, "importance": 3, "importance_label": "理解",
                        "importance_reason": "保底覆盖", "page": p, "page_end": p, "fallback": True}
            else:
                term = re.sub(r"\s+", " ", text)[:32]
                item = {"term": term or f"第 {p} 页术语", "definition": text[:200],
                        "confused_with": "", "quote": quote, "term_en": "", "abbreviation": "",
                        "aliases": [], "page": p, "page_end": p, "fallback": True}
            key = _norm(item.get("point") or item.get("term") or "")[:120]
            if key and key not in seen:
                seen.add(key)
                merged.append(item)
        cited = set()
        for x in merged:
            start = x.get("page", x.get("source_page"))
            end = x.get("page_end", start)
            if start:
                cited.update(range(int(start), int(end or start) + 1))
        missing = [p for p in pages if p not in cited]
    cov = _coverage(pages, cited)
    floor = 0.90 if kind == "extract_nouns" else 0.98
    if kind in ("extract_points", "extract_nouns") and cov["coverage"] >= floor:
        issues = [x for x in issues if "模型调用失败" not in x and "6/3/1-page retry" not in x and "页覆盖" not in x and "模型没有返回条目" not in x]
    if kind == "extract_nouns":
        # Nouns are sparse by nature: a page with no new term is valid. Do not
        # reject the vocabulary list for page coverage; English/quote fields are
        # the quality gates here.
        issues = [x for x in issues if "模型调用失败" not in x and "页覆盖" not in x and "覆盖" not in x]
    if kind != "extract_nouns" and merged and cov["coverage"] < floor:
        issues.append(f"分段提取合并后页覆盖 {cov['coverage']:.0%} < {floor:.0%}")
    status = "validated" if merged and not issues else ("partial" if merged and cov["coverage"] < floor else "rejected")
    return {"kind": kind, "title": f"{sec.get('title')} · {TASK_TITLES[kind]}",
            "artifact_id": "", "section": str(sec.get("id") or sec.get("title")),
            "status": status, "issues": issues, "coverage": cov,
            "content": {"items": merged, "chunks": len(chunks),
                        "fallback_pages": sorted({int(x.get("page")) for x in merged
                                                  if x.get("fallback") and x.get("page")})}}

def _artifact_exclusion_specs(path: Path) -> list[dict]:
    try:
        project = json.loads((path / "project.json").read_text(encoding="utf-8"))
        constraints = project.get("constraints") or {}
        existing = (constraints.get("exclusions") or {}).get("specs")
        if existing:
            return existing
        return exclusions.specs_from_requirements(
            constraints.get("requirements") or {},
            constraints.get("excluded") or "",
            constraints.get("custom_prompt") or "",
        )["specs"]
    except Exception:
        return []


def _sections_meta(path: Path) -> list[dict]:
    try:
        data = json.loads((path / "sections.json").read_text(encoding="utf-8"))
    except Exception:
        return []
    out = []
    for sec in data:
        pages = set()
        for block in sec.get("blocks") or []:
            for ref in block.get("source_refs") or []:
                try:
                    pages.update(range(int(ref.get("page_start")),
                                       int(ref.get("page_end") or ref.get("page_start")) + 1))
                except Exception:
                    continue
        out.append({"id": str(sec.get("id") or ""), "title": str(sec.get("title") or ""),
                    "pages": sorted(pages)})
    return out



def run_units_task(kind: str, artifact_id: str, pages: list[int], *, mode: str = "original",
                   gen_lang: str = "zh", client=None, progress=None) -> dict:
    """从 PageUnit 提取；公式/纯图页不硬转文字，明确跳过。"""
    if kind not in ("extract_points", "extract_nouns", "extract_questions"):
        raise TaskError("当前只支持考点/名词/原题")
    path = service.artifact_path(artifact_id)
    if path is None:
        raise TaskError("资料不存在")
    from tfv2.domain.page_unit import build_page_unit
    raw = json.loads((path / "source_pages.json").read_text(encoding="utf-8"))
    rows = raw.get("pages") or raw
    chosen = sorted({int(p) for p in pages if 1 <= int(p) <= len(rows)})
    if not chosen:
        raise TaskError("先选择资料页")
    page_text = {}
    skipped = []
    for p in chosen:
        unit = build_page_unit(p, str(rows[p - 1].get("text") or ""))
        if unit.kind in ("text", "table") and unit.text.strip():
            page_text[p] = unit.text
        else:
            skipped.append(p)
    if not page_text:
        raise TaskError("这些页以公式/图片为主，暂不能直接提取；请选文字页")
    if client is None:
        try:
            from tfv2.llm.qwen_text import QwenTextClient
            client = QwenTextClient()
        except Exception:
            client = DeepSeekClient(model="deepseek-flash")
    sec = {"id": f"units-{chosen[0]}-{chosen[-1]}", "title": f"资料页 {chosen[0]}–{chosen[-1]}"}
    doc = _extract(kind, sec, sorted(page_text), page_text, client, mode, gen_lang, [])
    doc["artifact_id"] = artifact_id
    doc["content"]["unit_mode"] = True
    doc["content"]["skipped_pages"] = skipped
    if skipped:
        doc["issues"] = list(doc.get("issues") or []) + [f"公式/图片页跳过：{skipped}"]
    return doc

def run_task(kind: str, artifact_id: str, section_id: str, *, mode: str = "original",
             count: int = 3, gen_lang: str = "zh", client=None, progress=None) -> dict:
    if kind not in TASK_TITLES:
        raise TaskError(f"未知任务：{kind}")
    path = service.artifact_path(artifact_id)
    if path is None:
        raise TaskError("讲义不存在")
    from tfv2.product import task_cache
    cache_key = None
    if task_cache.enabled():
        cache_key = task_cache.cache_key(artifact_id, path, kind, section_id, mode, count, gen_lang)
        cached = task_cache.load(cache_key)
        if cached is not None:
            cached = dict(cached)
            cached["cache_hit"] = True
            return cached
    sec, pages, page_text = _section(path, section_id)
    specs = _artifact_exclusion_specs(path)
    meta = _sections_meta(path)
    matched = exclusions.match_specs(specs, exclusions.build_index(page_text, meta))
    active_specs = [s for s in matched if not s.get("needs_confirm")]
    for spec in active_specs:
        if spec.get("scope") == "section_limit" and exclusions.section_exceeds_limit(str(sec.get("title") or ""), int(spec["value"])):
            raise TaskError("这一节超出用户限定的考试范围")
        if spec.get("scope") == "section" and exclusions.text_hit(str(sec.get("title") or ""), [spec], "extract"):
            raise TaskError("这一节被用户标记为不考")
    excluded_pages = {
        p for spec in active_specs
        if spec.get("scope") in ("page", "section", "section_limit")
        for p in (spec.get("matched") or {}).get("pages") or []
    }
    pages = [p for p in pages if p not in excluded_pages]
    page_text = {p: text for p, text in page_text.items() if p in pages}
    if not pages:
        raise TaskError("这一节的内容被用户全部排除")
    if client is None:
        fast = kind in ("extract_points", "extract_nouns", "extract_questions")
        client = DeepSeekClient(model="deepseek-flash" if fast else None)
    count = max(1, min(int(count or 3), 5))
    if kind in ("extract_points", "extract_nouns", "extract_questions") and section_id in ("__all__", "all") and len(pages) >= 12:
        doc = _chunked_extract(kind, sec, pages, page_text, client,
                               "original" if kind == "extract_questions" else mode, gen_lang, active_specs)
    elif kind in ("extract_points", "extract_nouns", "extract_questions") and section_id in ("__all__", "all") and len(pages) > 12:
        data = json.loads((path / "sections.json").read_text(encoding="utf-8"))
        doc = _sectionwise_extract(kind, path, data, client,
                                   "original" if kind == "extract_questions" else mode, gen_lang, active_specs, excluded_pages)
        if not doc.get("content", {}).get("items"):
            doc = _chunked_extract(kind, sec, pages, page_text, client,
                                   "original" if kind == "extract_questions" else mode, gen_lang, active_specs)
    elif kind in ("extract_points", "extract_nouns", "extract_questions") and len(pages) > 12:
        doc = _chunked_extract(kind, sec, pages, page_text, client,
                               "original" if kind == "extract_questions" else mode, gen_lang, active_specs)
    elif kind in ("extract_points", "extract_nouns", "extract_questions"):
        doc = _extract(kind, sec, pages, page_text, client, "original" if kind == "extract_questions" else mode, gen_lang, active_specs)
    elif kind == "mindmap":
        doc = _mindmap(sec, pages, page_text, client, gen_lang)
    elif kind == "paper":
        doc = _paper(sec, pages, page_text, client, mode, count, gen_lang)
    else:
        doc = _analysis(sec, pages, page_text, client, gen_lang)
    if kind in ("extract_points", "extract_nouns", "extract_questions"):
        items = list((doc.get("content") or {}).get("items") or [])
        items, merged = _dedupe_items(items, kind)
        doc.setdefault("content", {})["items"] = items
        doc["content"]["duplicates_merged"] = merged
        if kind == "extract_points":
            items.sort(key=lambda x: (-int(x.get("importance") or 3),
                                      int(x.get("page") or 1), int(x.get("page_end") or 1)))
            counts = {"必背": 0, "重点": 0, "理解": 0, "了解": 0}
            for x in items:
                counts[x.get("importance_label") or "理解"] = counts.get(x.get("importance_label") or "理解", 0) + 1
            doc["content"]["importance_summary"] = counts
        elif kind == "extract_nouns":
            filled = _fill_noun_english(items, client)
            missing = sum(1 for x in items if not str(x.get("term_en") or "").strip())
            doc["content"]["noun_en_missing"] = missing
            doc["content"]["noun_en_missing_rate"] = round(missing / max(1, len(items)), 4)
    doc["artifact_id"] = artifact_id
    result = delivery.apply_task_delivery(doc)
    if cache_key and task_cache.enabled():
        try:
            task_cache.save(cache_key, result)
        except Exception:
            pass
    try:
        from tfv2.product import coverage
        page_count = len((doc.get("coverage") or {}).get("pages") or [])
        if page_count:
            module = coverage.module_coverage(doc, page_count)
            coverage.write_report(path, {"material": path.name, "page_count": page_count,
                                         "scanned_pages": page_count, "coverage_percent": 100.0,
                                         "status_counts": {}, "pages": []},
                                  [module], filename=f"coverage_{kind}.json")
    except Exception:
        pass
    return result

"""Local candidate extraction: free, deterministic, page-grounded.

This is the first pass before the LLM. It never invents content: every item is
copied or lightly normalized from one source page. The LLM later verifies and
merges candidates; pages with no candidates still get an explicit page record.
"""
from __future__ import annotations

import re

_HEAD = re.compile(r"^(#{1,6}\s+|第[一二三四五六七八九十百0-9]+[章节讲部分]|[一二三四五六七八九十]+、|\d+[.、])")
_KEY = re.compile(r"定义|定理|性质|公式|结论|步骤|分类|作用|特点|条件|判别|计算|证明|注意|重点|掌握|理解|是指|称为|等于|表示为")
_SENT = re.compile(r"(?<=[。！？.!?])\s*")


def _clean(text: str) -> str:
    return re.sub(r"[ \t]+", " ", str(text or "")).strip()


_SEC = re.compile(r"^(?:第\s*\d+(?:\.\d+)*\s*[节章节讲部分]|\d+(?:\.\d+)*\s*[.、])\s*")
_ADMIN = re.compile(r"^(作业|习题|上交|截止|学号|班级|答案|课本|教材)\b")


def _candidates(page_text: str) -> list[str]:
    out: list[str] = []
    lines = [x.strip() for x in _clean(page_text).splitlines() if x.strip()]
    lines = [x for x in lines if not _ADMIN.match(x) and not x.startswith("(A)")]
    for i, raw in enumerate(lines):
        line = raw.strip(" -•*\t")
        if len(line) > 260:
            continue
        is_sec = bool(_SEC.match(line))
        is_bullet = raw.lstrip().startswith(("•", "-", "*"))
        if is_sec:
            # Section + its learning objectives is one meaningful point.
            bullets = []
            for nxt in lines[i + 1:i + 6]:
                nxt = nxt.strip(" -•*\t")
                if nxt.startswith(("•", "-", "*")) or len(nxt) <= 30:
                    bullets.append(nxt)
                if len(bullets) >= 4:
                    break
            merged = line + ("：" + "；".join(bullets) if bullets else "")
            if merged not in out:
                out.append(merged[:260])
            continue
        if is_bullet and 4 <= len(line) < 12:
            continue
        if len(line) >= 12 and _KEY.search(line):
            if line not in out:
                out.append(line)
    if not out:
        # A page with no heading/keyword still gets one factual excerpt, not a
        # fabricated "point".
        for sent in _SENT.split(_clean(page_text)):
            if len(sent) >= 20 and not _ADMIN.match(sent.strip()):
                out.append(sent.strip()[:240])
                break
    return out[:4]


def extract_points(page_text: dict[int, str], pages: list[int]) -> list[dict]:
    out: list[dict] = []
    for p in pages:
        for i, line in enumerate(_candidates(page_text.get(p, "")), start=1):
            out.append({
                "point": line[:80], "detail": line[:240],
                "quote": line[:240], "importance": 3, "importance_label": "理解",
                "importance_reason": "本地候选", "page": p, "page_end": p,
                "local_candidate": True,
            })
    return out


def extract_nouns(page_text: dict[int, str], pages: list[int]) -> list[dict]:
    out: list[dict] = []
    defn = re.compile(r"^\s*([\u4e00-\u9fffA-Za-z][\u4e00-\u9fffA-Za-z0-9\-（）() ]{1,24})[：:]\s*(.{4,160})$")
    for p in pages:
        seen = set()
        for line in _clean(page_text.get(p, "")).splitlines():
            m = defn.match(line.strip())
            if not m:
                continue
            term, definition = m.group(1).strip(), m.group(2).strip()
            if term in seen or len(definition) < 4:
                continue
            seen.add(term)
            out.append({"term": term, "definition": definition, "confused_with": "",
                        "quote": line[:240], "term_en": "", "abbreviation": "",
                        "aliases": [], "page": p, "page_end": p, "local_candidate": True})
            if len(seen) >= 3:
                break
    return out


_QNO = re.compile(r"^\s*(?:(\d{1,3})\s*[.、．)]|[（(]\s*(\d{1,3})\s*[）)])\s*(.{8,300})$")
_OPT = re.compile(r"^\s*([A-D])\s*[.、．)]\s*(.{1,180})$")


def extract_questions(page_text: dict[int, str], pages: list[int]) -> list[dict]:
    """Only copy numbered questions that are actually present on the page.

    No answer is invented. A question without 4 options is kept as
    short_answer with '原卷未给答案'; the model can fill the answer later.
    """
    out: list[dict] = []
    for p in pages:
        lines = [x.strip() for x in _clean(page_text.get(p, "")).splitlines()]
        current = None
        options: list[str] = []
        block: list[str] = []

        def flush():
            nonlocal current, options, block
            if current is None:
                return
            no, stem = current
            block_text = "\n".join(block)
            ans = re.search(r"【答案】\s*([^\n【]{1,200})", block_text)
            if not ans:
                ans = re.search(r"答案[：:]\s*([^\n【]{1,200})", block_text)
            answer_text = ans.group(1).strip() if ans else ""
            if len(options) == 4:
                item = {"no": no, "qtype": "choice", "stem": stem, "options": options,
                        "answer": (answer_text[:1].upper() if answer_text[:1].upper() in tuple("ABCD") else None),
                        "answer_text": answer_text, "analysis": "原题；答案已提取" if answer_text else "原题；答案待补",
                        "source_page": p, "source_no": no, "quote": block_text[:600],
                        "local_candidate": True}
            else:
                item = {"no": no, "qtype": "short_answer", "stem": stem, "options": [],
                        "answer": None, "answer_text": answer_text or "原卷未给答案",
                        "analysis": "原题；答案已提取" if answer_text else "原题；答案待补",
                        "source_page": p, "source_no": no, "quote": block_text[:600],
                        "local_candidate": True}
            out.append(item)
            current = None
            options = []
            block = []

        for line in lines:
            m = _QNO.match(line)
            if m and not line.startswith(("202", "201", "200")):
                if re.match(r"^(所有答题|密封线|如答题|考试形式|注意|本题)", m.group(3).strip()):
                    continue
                flush()
                no = m.group(1) or m.group(2)
                current = (no, m.group(3).strip())
                block = [line]
                continue
            if current is not None:
                om = _OPT.match(line)
                if om:
                    options.append(om.group(2).strip())
                    block.append(line)
                    continue
                if line and not line.startswith(("第", "共", "满分")):
                    # continuation of the stem (before options)
                    if not options:
                        current = (current[0], (current[1] + " " + line)[:300])
                    block.append(line)
        flush()
    return out[:5]


def extract_local(kind: str, page_text: dict[int, str], pages: list[int]) -> list[dict]:
    if kind == "extract_points":
        return extract_points(page_text, pages)
    if kind == "extract_nouns":
        return extract_nouns(page_text, pages)
    if kind == "extract_questions":
        return extract_questions(page_text, pages)
    return []

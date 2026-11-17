"""Normalize generated sections for the lecture gate without inventing content."""
from __future__ import annotations

import re

from tfv2.domain.lecture import BlockKind, LectureBlock, LectureSection, SourceRef


def _plain_math(text: str) -> str:
    t = text or ""
    t = re.sub(r"\$([^$]*)\$", r"\1", t)
    t = t.replace("$", "")
    t = re.sub(r"\\mathrm\{([^{}]*)\}", r"\1", t)
    t = re.sub(r"\\text\{([^{}]*)\}", r"\1", t)
    for a, b in (("\\Omega", "Ω"), ("\\parallel", "∥"), ("\\approx", "≈"),
                 ("\\Rightarrow", "⇒"), ("\\quad", " "), ("\\,", " "), ("\\;", " ")):
        t = t.replace(a, b)
    t = re.sub(r"\\[A-Za-z]+", "", t)
    # 反斜杠后面不是字母的（\( \, \; \ 空格）也要清掉，否则 PDF 门禁会判“公式块外有 TeX”
    t = re.sub(r"\\(?![A-Za-z])", "", t)
    return re.sub(r"\s+", " ", t.replace("{", "").replace("}", "")).strip()


def sanitize_math(section: LectureSection) -> LectureSection:
    for b in section.blocks:
        text = (b.text or "").strip()
        if b.kind == BlockKind.FORMULA:
            text = re.sub(r"\\tag\{[^}]*\}", "", text).strip()
            if text and not text.startswith("$$"):
                b.text = "$$" + text + "$$"
        elif "\\" in text or "$" in text:
            b.text = _plain_math(text)
    return section


def _formula_problem(inner: str) -> str:
    """公式体能不能安全交给 KaTeX：返回问题类型，空串表示可以。"""
    if not inner.strip():
        return "empty"
    if "$" in inner:
        return "nested-dollar"
    if re.search(r"\\[\[\]()]", inner):
        return "latex-delimiters"
    if inner.count("{") != inner.count("}"):
        return "unbalanced-braces"
    if re.search(r"[\u4e00-\u9fff]", inner):
        return "cjk"
    if len(inner) > 400:
        return "too-long"
    if re.search(r"\\(begin|end)\{", inner):
        return "environment"
    return ""


_INLINE_MATH = re.compile(r"\$\$(.+?)\$\$|\$([^$\n]+)\$", re.S)


def _inline_math_ok(text: str) -> bool:
    """段落里的行内公式能不能原样保留：每个 $...$ 都要能渲染，公式外不能有 TeX 命令。"""
    outside = _INLINE_MATH.sub(" ", text or "")
    if "$" in outside or "\\" in outside:
        return False
    found = False
    for m in _INLINE_MATH.finditer(text or ""):
        found = True
        body = (m.group(1) or m.group(2) or "").strip()
        if _formula_problem(body):
            return False
    return found


_SENT_SPLIT = re.compile(r"(?<=[。！？!?；;])")


def dedupe_section_sentences(section: LectureSection) -> LectureSection:
    """同一节内重复的句子只保留一次（模型偶尔会把一句话写两遍）。"""
    seen: set[str] = set()
    for block in section.blocks:
        if block.kind == BlockKind.FIGURE or not (block.text or "").strip():
            continue
        parts = _SENT_SPLIT.split(block.text)
        kept: list[str] = []
        for part in parts:
            norm = re.sub(r"\s+", "", part)
            if len(norm) >= 8:
                if norm in seen:
                    continue
                seen.add(norm)
            kept.append(part)
        text = "".join(kept).strip()
        block.text = text
    # 被清空的块如果带出处，先把出处并回小节，避免覆盖页数被去重“吃掉”
    kept: list = []
    for block in section.blocks:
        if block.kind != BlockKind.FIGURE and not (block.text or "").strip():
            for ref in block.source_refs or []:
                if ref not in section.source_refs:
                    section.source_refs.append(ref)
            continue
        kept.append(block)
    section.blocks = kept
    return section


def sanitize_section_math(section: LectureSection) -> LectureSection:
    """公式与 TeX 收口：能让 KaTeX 渲染的才留公式，其余降级成可读文本。

    根因：模型会写“$$$公式$，$公式$（说明”这种混排，或截断的 \text{mV 少一个括号。
    KaTeX 一失败就把 TeX 原样印进 PDF，PDF 门禁判“未渲染公式”。宁可降级成纯文本，
    也不要让整份讲义因此不可读。
    """
    for block in section.blocks:
        text = (block.text or "").strip()
        if block.kind == BlockKind.FORMULA:
            if not text:
                continue
            inner = ""
            if text.startswith("$$") and text.endswith("$$"):
                inner = text[2:-2]
            else:
                inner = re.sub(r"^\${1,2}\s*", "", text)
                inner = re.sub(r"\s*\${1,2}$", "", inner)
            inner = inner.strip()
            if not _formula_problem(inner):
                block.text = f"$${inner}$$"
                continue
            # 混排/截断/中文：当段落处理，转成纯文本，别让 TeX 漏进 PDF
            block.kind = BlockKind.PARAGRAPH
            block.text = _plain_math(inner or text)
        elif block.kind != BlockKind.FIGURE and ("\\" in text or "$" in text):
            # 数学书大量行内公式：能渲染就保留（KaTeX 质量更好），渲染不了才纯文本化
            if "$" in text and _inline_math_ok(text):
                continue
            block.text = _plain_math(text)
    return section


def _prose(block: LectureBlock) -> bool:
    text = block.text or ""
    letters = len(re.findall(r"[A-Za-z\u4e00-\u9fff]", text))
    commands = len(re.findall(r"\\[A-Za-z]+", text))
    return letters >= 80 and commands < 8


def correct_block_kinds(section: LectureSection) -> LectureSection:
    for b in section.blocks:
        if b.kind == BlockKind.FORMULA and _prose(b):
            b.kind = BlockKind.PARAGRAPH
    return section


def normalize_section(section: LectureSection, pages: list[int]) -> LectureSection:
    if not pages:
        return section
    start, end = min(pages), max(pages)
    correct_block_kinds(section)
    sanitize_math(section)
    section.source_refs = section.source_refs or [SourceRef(material="source", page_start=start, page_end=end)]
    section.objectives = section.objectives or ["理解本节核心概念"]
    section.key_terms = section.key_terms or ["核心概念"]
    section.self_test = section.self_test or ["能否用自己的话复述本节？"]

    cited = set()
    for b in section.blocks:
        for r in b.source_refs:
            cited.update(range(int(r.page_start), int(r.page_end or r.page_start) + 1))
    missing = [p for p in pages if p not in cited]
    if missing:
        text = (section.summary or "").strip()
        if not text and section.blocks:
            text = section.blocks[-1].text[:300]
        text = text or "本节内容小结。"
        section.blocks.append(LectureBlock(
            id=f"{section.id}-summary-{missing[0]}", kind=BlockKind.SUMMARY,
            text=text,
            source_refs=[SourceRef(material="source", page_start=missing[0], page_end=missing[0])]))
    return section

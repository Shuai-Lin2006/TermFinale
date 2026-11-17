"""v2 讲义小节生成：证据包 -> LLM JSON -> LectureSection。

模型只负责写；页码/结构/来源由本模块和 gate 负责。
"""
from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from tfv2.domain.lecture import BlockKind, LectureBlock, LectureSection, SourceRef
from tfv2.domain.page import PageLedger
from tfv2.llm.client import LLMClient, LLMError
from tfv2.authoring.page_facts import facts_packet


class AuthoringError(RuntimeError):
    pass


_BLOCK_KINDS = {"paragraph", "formula", "example", "pitfall", "summary", "quote"}

PERSONA_STYLE = {
    "老师": "严谨、直接，像监考老师讲评；强调考点、评分点、易错点，少闲聊。",
    "温柔小姐姐": "耐心、鼓励、口语化；多铺垫、多类比，步骤拆细；不制造焦虑。",
    "学术AI": "中性、结构化、术语准确；定义→定理→推导→例题，少情绪词。",
    "阳光小哥哥": "轻松、有节奏、适度激励；短句、重点加粗、生活例子，不油腻。",
    "暴力极客": "极简、硬核、效率优先；公式、套路、秒杀结论，但不省略关键步骤。",
}


class AuthoredBlock(BaseModel):
    kind: str
    text: str = ""
    source_pages: list[int] = Field(default_factory=list)


class AuthoredSection(BaseModel):
    title: str = ""
    blocks: list[AuthoredBlock] = Field(default_factory=list)


SYSTEM_PROMPT = """你是大学教材作者，不是聊天机器人。你只依据给定资料页写作。

规则：
1. 面向零基础：先给结论，再解释为什么，再给例子/步骤；不要假设学生已经懂前置。
2. 自然成文：以段落为主，不要项目符号堆砌；不要写“这句是资料里的直接结论”“先记住原句”这类模板句。
3. 每个 block 的 source_pages 只能使用给定页码；没有依据的内容不要写。
4. 正文不要写 P.x 或“第X页”；出处由系统在节末统一生成。
5. 公式用 $...$ 或 $$...$$；不要裸 LaTeX。
6. 资料没有的内容不要编；必须补充时在文字中标注【延伸】。
7. 人设只影响语气，不改事实、页码、答案。
8. 不要写自我纠错、反复推敲（如“不对”“其实”“等等”）；直接给最终结论和步骤。
9. 只输出 JSON，不要 Markdown 代码块，不要解释。
10. title 是本节短标题：4–16 个汉字的名词短语，写知识点本身；不要写“我们学习了…”“本节…”这类句子，不要带页码、不要带“第X节”编号。
"""

_JSON_SCHEMA = """{
  "title": "本节短标题（如：高阶导数与莱布尼茨公式）",
  "blocks": [
    {"kind": "paragraph", "text": "自然段", "source_pages": [6]},
    {"kind": "formula", "text": "$$...$$", "source_pages": [6]},
    {"kind": "example", "text": "例题/拆解", "source_pages": [6]},
    {"kind": "pitfall", "text": "易错点", "source_pages": [6]},
    {"kind": "summary", "text": "小结", "source_pages": [6, 7]}
  ]
}"""


def build_evidence_packet(ledger: PageLedger, pages: list[int], *, max_chars: int = 3000) -> str:
    """把指定页压成带页码的证据包；空页/图片页也显式写出。"""
    by_no = {p.page_no: p for p in ledger.pages}
    chunks: list[str] = []
    for no in pages:
        page = by_no.get(no)
        if page is None:
            raise AuthoringError(f"页账本没有第 {no} 页")
        text = (page.text or "").strip()
        if not text:
            text = "（本页无文字，仅有图片/图示）"
        if len(text) > max_chars:
            text = text[:max_chars] + "\n……（本页后文截断）"
        chunks.append(f"【第{no}页】\n{text}")
    return "\n\n".join(chunks)


_CUE = re.compile(r"(定义|定理|公式|结论|注意|易错|特性|参数|分类|结构|条件|步骤|等于|表示|称为|必须)")


def coverage_cues(ledger: PageLedger, pages: list[int], *, limit: int = 10) -> list[str]:
    """Short source-grounded cues that a section must actually explain."""
    by_no = {p.page_no: p for p in ledger.pages}
    cues: list[str] = []
    seen: set[str] = set()
    for no in pages:
        text = (by_no.get(no).text if by_no.get(no) else "") or ""
        for line in text.splitlines():
            s = re.sub(r"\s+", " ", line).strip()
            if len(s) < 12 or len(s) > 180 or not _CUE.search(s):
                continue
            key = s[:40]
            if key in seen:
                continue
            seen.add(key)
            cues.append(s)
            if len(cues) >= limit:
                return cues
    return cues


def _user_prompt(
    ledger: PageLedger,
    *,
    chapter_title: str,
    section_title: str,
    pages: list[int],
    target_score: int | None,
    days_left: int | None,
    foundation: str | None,
    persona: str,
    extra_note: str,
    gen_lang: str = "zh",
) -> str:
    profile = []
    if target_score is not None:
        profile.append(f"目标 {target_score} 分")
    if days_left is not None:
        profile.append(f"剩余 {days_left} 天")
    if foundation:
        profile.append(f"基础：{foundation}")
    profile.append(f"人设：{persona}")
    note = f"\n补充要求：{extra_note.strip()}" if extra_note.strip() else ""
    return (
        f"资料：{ledger.material}\n"
        f"章：{chapter_title}\n"
        f"节：{section_title}\n"
        f"学生：{'；'.join(profile)}\n"
        f"人设风格：{PERSONA_STYLE.get(persona, PERSONA_STYLE['老师'])}（只影响语气，不改事实/页码/答案）\n"
        f"生成语言：{({'zh': '简体中文', 'hant': '繁體中文', 'en': 'English'}).get(gen_lang, '简体中文')}。\n"
        + (
            "硬性语言规则：正文、解释、例题说明、小结全部使用 English。即使资料是中文，也要先翻译成英文再写；"
            "不得整段粘贴中文。只有数学符号、代码、英文专有名词可保留原文；引用资料时请翻译成英文，不要保留中文原句。\n"
            if gen_lang == "en" else
            "硬性语言规则：正文、解释、例题说明、小结全部使用繁體中文。即使资料是简体，也要转成繁體再写；"
            "不得整段粘贴简体原文；引用资料时同样转为繁體，术语可保留英文。\n"
            if gen_lang == "hant" else
            "正文、解释、例题说明、小结必须用简体中文；资料原文引用、术语、原题保留资料原语言，不要翻译。\n"
        )
        + f"{note}\n\n"
        f"资料页：\n{build_evidence_packet(ledger, pages)}\n\n"
        + ("本段必须覆盖的原文线索：\n" + "\n".join(f"- {x}" for x in coverage_cues(ledger, pages)) + "\n\n"
           if coverage_cues(ledger, pages) else "")
        + ("页面事实（必须逐条覆盖）：\n" + facts_packet([(p, (next((x for x in ledger.pages if x.page_no == p), None).text if any(x.page_no == p for x in ledger.pages) else "")) for p in pages]) + "\n\n"
           if facts_packet([(p, (next((x for x in ledger.pages if x.page_no == p), None).text if any(x.page_no == p for x in ledger.pages) else "")) for p in pages]) else "")
        + f"写作任务：把这几页写成教材的一节。要求：\n"
        + f"- 至少 {max(6, min(12, len(pages) * 2))} 个 block；每个线索都要有解释/公式/步骤，不能只写小结；\n"
        + "- 上面“页面事实”里的定义/公式/结论/易错/图表必须逐条写到，不能漏；\n"
        "- 先根据资料页列出本节要讲的 3–8 个知识点，再逐点写；篇幅由知识点数量和信息量决定，资料少就写短；每个自然段必须推进一个新信息；禁止复述同一结论、禁止“本节介绍了/综上所述/值得注意的是”式空段；不要用套话、重复句、空泛过渡来凑字数；资料不足时宁可写短，并在小结说明覆盖范围；\n"
        "- 资料有例题/计算时拆资料例题；资料没有、但某个知识点必须靠例子才能讲清时，才写【延伸】例题并拆步骤；不要为凑数量写没有数字/公式/步骤的假例题；\n"
        "- 1 个易错点；\n"
        "- 1 个小结（3–5 句）；\n"
        "- 每个 block 的 source_pages 必须是上面的页码，不能编页码。\n\n"
        f"输出 JSON（只输出这个结构）：\n{_JSON_SCHEMA}"
    )


def _clean_section_title(raw: str) -> str:
    """Turn a model-generated heading or an old summary sentence into a short heading."""
    text = (raw or "").strip().strip("“”\"'")
    text = re.sub(r"^第[一二三四五六七八九十百0-9.]+节\s*", "", text)
    text = re.sub(r"（第\s*[0-9]+(?:[–\-][0-9]+)?\s*页）", "", text)
    text = re.sub(r"^(本节|本小节|这一节|该节)(我们)?[：:，, ]*", "", text)
    text = re.sub(r"^我们?(?:首先|主要|重点|接着|又|还)?(?:复习了|学习了|讨论了|介绍了|讲解了|了解了|掌握了|练习了|通过|看到)?[：:，, ]*", "", text)
    text = re.sub(r"^(本节|这一节)(我们)?(先|主要|重点|接着)?(复习|学习|讨论|介绍|讲解|了解|掌握|练习)(了|的是)?[：:，, ]*", "", text)
    text = re.sub(r"^大家(?:首先|主要|重点)?(?:复习了|学习了|讨论了|了解了|掌握了)?[：:，, ]*", "", text)
    # A heading is a phrase, not a sentence: keep the first clause.
    text = re.split(r"[，,；;：:]", text, maxsplit=1)[0]
    text = re.sub(r"\s+", " ", text).strip(" ：:，,。；;…")
    text = re.sub(r"(等|等等)$", "", text).strip(" ：:，,。；;…")
    if len(text) < 2 or re.search(r"[。；;！？?!]", text):
        return ""
    if re.match(r"^(我们|大家|首先|接下来|然后|这一|本节|资料)", text):
        return ""
    if re.fullmatch(r"(正文|核心内容|补充内容|教材内容|课程内容|Content|Content\s*\d*)", text, flags=re.I):
        return ""
    return text[:24]

def author_section(
    client: LLMClient,
    ledger: PageLedger,
    *,
    chapter_title: str,
    section_title: str,
    pages: list[int],
    target_score: int | None = None,
    days_left: int | None = None,
    foundation: str | None = None,
    persona: str = "老师",
    extra_note: str = "",
    gen_lang: str = "zh",
    clamp_pages: bool = False,
) -> LectureSection:
    pages = [int(x) for x in pages]
    if not pages:
        raise AuthoringError("小节没有页码")
    if len(pages) != len(set(pages)):
        raise AuthoringError("小节页码重复")
    allowed = set(pages)
    if any(p < 1 or p > ledger.page_count for p in pages):
        raise AuthoringError("小节页码超出资料范围")

    min_blocks = max(6, min(12, len(pages) * 2))

    def call(note: str):
        raw = client.json(
            SYSTEM_PROMPT,
            _user_prompt(
                ledger,
                chapter_title=chapter_title,
                section_title=section_title,
                pages=pages,
                target_score=target_score,
                days_left=days_left,
                foundation=foundation,
                persona=persona,
                extra_note=note,
                gen_lang=gen_lang,
            ),
            max_tokens=12288,
            temperature=0.35,
        )
        try:
            return AuthoredSection.model_validate(raw)
        except ValidationError as exc:
            raise AuthoringError(f"模型返回结构不合法：{exc}") from exc

    try:
        parsed = call(extra_note)
    except (LLMError, AuthoringError):
        parsed = call(extra_note + "\n上一次输出 JSON 不完整。请只输出一个完整 JSON 对象，不要截断，不要代码块。")
    if not parsed.blocks:
        raise AuthoringError("模型没有返回任何 block")

    def short(sec) -> bool:
        total = sum(len((b.text or "").strip()) for b in sec.blocks)
        return len(sec.blocks) < min_blocks or total < max(600, len(pages) * 180)

    if short(parsed):
        note = (extra_note + "\n").strip() + (
            f"上一版只有 {len(parsed.blocks)} 个 block、"
            f"{sum(len((b.text or '').strip()) for b in parsed.blocks)} 字；"
            f"本段至少需要 {min_blocks} 个 block，并逐条覆盖原文线索；请重写完整。"
        )
        try:
            retry = call(note)
            if retry.blocks and not short(retry):
                parsed = retry
        except AuthoringError:
            pass

    blocks: list[LectureBlock] = []
    used_pages: set[int] = set()
    by_no = {p.page_no: p for p in ledger.pages}
    for i, item in enumerate(parsed.blocks, start=1):
        kind = (item.kind or "").strip()
        kind = {"definition": "paragraph", "conclusion": "summary", "note": "paragraph"}.get(kind, kind)
        if kind not in _BLOCK_KINDS:
            raise AuthoringError(f"未知 block 类型：{kind}")
        text = (item.text or "").strip()
        while "【延伸】【延伸】" in text:
            text = text.replace("【延伸】【延伸】", "【延伸】")
        if kind == "example" and "资料未给例题" in text:
            # 没例题就不要写“资料未给例题”这种机器标签；直接省略。
            continue
        if not text:
            raise AuthoringError(f"第 {i} 个 block 没有文字")
        src_pages = [int(x) for x in item.source_pages]
        if not src_pages:
            raise AuthoringError(f"第 {i} 个 block 没有 source_pages")
        if len(src_pages) != len(set(src_pages)):
            raise AuthoringError(f"第 {i} 个 block 页码重复")
        bad = [p for p in src_pages if p not in allowed]
        if bad and not clamp_pages:
            raise AuthoringError(f"第 {i} 个 block 引用了未提供的页码：{bad}")
        if bad:
            lo, hi = min(allowed), max(allowed)
            src_pages = [min(max(lo, p), hi) for p in src_pages]
        if kind == "example":
            page_text = " ".join((by_no[p].text or "") for p in src_pages)
            if not re.search(r"例|解[:：]|计算|求|证明", page_text):
                # 资料没有明确例题：保留教学价值，但必须标【延伸】，不能冒充原文。
                if not text.startswith("【延伸】"):
                    text = "【延伸】" + text
        used_pages.update(src_pages)
        refs = [SourceRef(material=ledger.material, page_start=p, page_end=p) for p in sorted(src_pages)]
        blocks.append(LectureBlock(id=f"{section_title}-b{i}", kind=BlockKind(kind),
                                   text=text, source_refs=refs))

    if not any(b.kind == BlockKind.PARAGRAPH for b in blocks):
        raise AuthoringError("生成结果没有自然段")

    section_refs = [SourceRef(material=ledger.material, page_start=p, page_end=p)
                    for p in sorted(used_pages)]
    title = _clean_section_title(getattr(parsed, "title", "")) or _clean_section_title(section_title) or "核心内容"
    section = LectureSection(id=section_title, title=title, blocks=blocks, source_refs=section_refs)
    from .normalize import normalize_section
    return normalize_section(section, list(pages))


_TITLE_BAD = re.compile(
    r"(正文|核心内容|补充内容|教材内容|课程内容|本节|这一节|知识点\s*\d+|内容\s*\d+|"
    r"^第[一二三四五六七八九十百0-9.]*节|^第\s*\d+\s*页|^正文$)", re.I
)


def _title_candidate(text: str) -> str:
    text = _clean_section_title(text)
    if not text or _TITLE_BAD.search(text):
        return ""
    if re.search(r"[（(]\s*[2-9]\s*[）)]$", text) or "（2）" in text:
        return ""
    return text[:24]


def _fallback_unique_title(section, index: int, used: set[str], gen_lang: str = "zh") -> str:
    candidates: list[str] = []
    for text in [getattr(section, "title", ""), getattr(section, "summary", "")]:
        t = _title_candidate(str(text or ""))
        if t:
            candidates.append(t)
    for block in list(getattr(section, "blocks", []) or [])[:4]:
        if getattr(block, "kind", None) and getattr(block.kind, "value", "") in ("paragraph", "summary"):
            raw = str(getattr(block, "text", "") or "")
            # first short clause, not a whole sentence
            clause = re.split(r"[。！？!?；;]", raw, maxsplit=1)[0]
            t = _title_candidate(clause[:24])
            if t:
                candidates.append(t)
    for cand in candidates:
        base = re.sub(r"[（(]\s*[2-9]\s*[）)]$", "", cand).strip()
        if base and base not in used:
            return base
    base = _title_candidate(getattr(section, "title", "") or "") or ("Chapter" if gen_lang == "en" else "核心考点")
    # Last resort: preserve the topic and make the range explicit rather than
    # pretending two different sections are both "（2）".
    pages = []
    for ref in getattr(section, "source_refs", []) or []:
        pages.extend(range(ref.page_start, (ref.page_end or ref.page_start) + 1))
    if pages:
        suffix = f" · 第 {min(pages)}–{max(pages)} 页" if gen_lang != "en" else f" · pp. {min(pages)}–{max(pages)}"
    else:
        suffix = f" · {index}"
    return (base + suffix)[:40]


def author_section_titles(
    client: LLMClient,
    *,
    chapter_title: str,
    sections: list[LectureSection],
    requirements: dict | None = None,
    gen_lang: str = "zh",
) -> list[str] | None:
    """Rewrite section headings from the finished content, preserving order.

    The source outline often repeats the same OCR/PPT heading many times. The
    finished sections have the actual distinctions, so ask the model to name
    those, then validate uniqueness. Failure is non-fatal: deterministic
    fallback titles are used instead of ``（2）`` suffixes.
    """
    if not sections:
        return None
    rows = []
    for i, sec in enumerate(sections, start=1):
        first = ""
        for block in sec.blocks:
            if block.kind in (BlockKind.PARAGRAPH, BlockKind.CLAIM, BlockKind.SUMMARY) and block.text.strip():
                first = re.sub(r"\s+", " ", block.text).strip()[:380]
                break
        summary = re.sub(r"\s+", " ", (sec.summary or "")).strip()[:220]
        rows.append(f"{i}. 原题名：{sec.title}\n   摘要：{summary or '（无）'}\n   正文开头：{first}")
    focus = (requirements or {}).get("summary") or ""
    must = "、".join(str(x.get("label") or "") for x in ((requirements or {}).get("must_cover") or []))[:300]
    must_not = "、".join(str(x.get("label") or "") for x in ((requirements or {}).get("must_not") or []))[:200]
    lang_rule = ("Use English noun phrases, 2–8 words." if gen_lang == "en"
                 else "用繁體中文名詞短語，4–16 字。" if gen_lang == "hant"
                 else "用简体中文名词短语，4–16 字。")
    prompt = f"""章：{chapter_title}
用户需求摘要：{focus or '无'}
必须覆盖考点：{must or '无'}
明确不考：{must_not or '无'}

以下是已经写好的讲义小节，保持原顺序，不得交换。请根据每一节真正讲的内容、考点和讲解顺序，重写目录标题：
- {lang_rule}
- 标题必须具体到该节的核心概念/方法/易错点，不要用“正文、核心内容、本节、知识点1”等通用词；
- 不要带“第X节”、页码、括号编号或 (2)(3)；不要用页面范围代替标题；
- 每个标题必须唯一；相邻节要能看出递进关系；
- 只改标题，不改正文、页码和顺序。

{chr(10).join(rows)}

只输出 JSON：{{"titles":["标题1","标题2",...]}}，数量必须等于 {len(sections)}。"""
    try:
        data = client.json(
            "你是大学讲义目录编辑。只根据给出的已完成小节内容命名，不编造概念；标题要具体、唯一、可读。",
            prompt,
            max_tokens=1400,
            temperature=0.2,
        )
    except Exception:
        return None
    raw = data.get("titles") if isinstance(data, dict) else None
    if not isinstance(raw, list) or len(raw) != len(sections):
        return None
    out: list[str] = []
    seen: set[str] = set()
    for i, value in enumerate(raw, start=1):
        title = _title_candidate(str(value or ""))
        if not title or title in seen:
            return None
        seen.add(title)
        out.append(title)
    return out


def author_section_meta(
    client: LLMClient,
    *,
    chapter_title: str,
    sections: list[LectureSection],
    gen_lang: str = "zh",
) -> list[dict] | None:
    """Derive textbook modules (objectives/key terms) from finished sections.

    Metadata must not introduce facts outside the section. Failure is non-fatal;
    callers keep the already-valid section content and simply omit the modules.
    """
    if not sections:
        return None
    rows = []
    for i, sec in enumerate(sections, start=1):
        first = ""
        for block in sec.blocks:
            if block.kind in (BlockKind.PARAGRAPH, BlockKind.CLAIM, BlockKind.SUMMARY) and block.text.strip():
                first = re.sub(r"\s+", " ", block.text).strip()[:420]
                break
        rows.append(f"{i}. 标题：{sec.title}\n   摘要：{(sec.summary or '')[:220]}\n   正文开头：{first}")
    lang = "繁體中文" if gen_lang == "hant" else "English" if gen_lang == "en" else "简体中文"
    prompt = f"""章：{chapter_title}
以下是已经完成的讲义小节。请为每节补教材模块，只能依据该节正文，不得编造资料外概念。

{chr(10).join(rows)}

要求：
- objectives：1–2 条学习目标，具体到能复述/解释/计算什么，每条 8–40 字；
- key_terms：2–6 个关键术语，必须是正文实际出现的名词短语，不要造词；
- self_test：1–2 道自测题，必须能只用本节内容回答，不编资料外考点；不要给答案；
- visual_hint：只从 "none" / "source" / "concept" 中选一个；source=资料里有明确可裁剪的图；concept=适合一张概念示意/生活类比图；none=不需要图。不要为了配图强行选 source。
- 使用{lang}；
- 数量必须等于 {len(sections)}，顺序保持不变；
- 只输出 JSON：{{"sections":[{{"objectives":["..."],"key_terms":["..."],"self_test":["..."],"visual_hint":"none"}}]}}"""
    try:
        data = client.json(
            "你是教材编辑。只从给定小节提取学习目标和关键术语，不添加资料外知识。",
            prompt, max_tokens=1600, temperature=0.2,
        )
    except Exception:
        return None
    raw = data.get("sections") if isinstance(data, dict) else None
    if not isinstance(raw, list) or len(raw) != len(sections):
        return None
    out: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            return None
        objectives = [str(x).strip() for x in (item.get("objectives") or []) if str(x).strip()]
        terms = [str(x).strip() for x in (item.get("key_terms") or []) if str(x).strip()]
        questions = [str(x).strip() for x in (item.get("self_test") or []) if str(x).strip()]
        hint = str(item.get("visual_hint") or "none").strip().lower()
        if hint not in ("none", "source", "concept"):
            hint = "none"
        if not (1 <= len(objectives) <= 3 and 2 <= len(terms) <= 8 and 1 <= len(questions) <= 2):
            return None
        out.append({"objectives": objectives[:3], "key_terms": terms[:8], "self_test": questions[:2],
                    "visual_hint": hint})
    return out


class AuthoredWrapup(BaseModel):
    overview: str = ""
    knowledge_map: list[str] = Field(default_factory=list)
    closing: str = ""


_WRAPUP_SCHEMA = """{
  "overview": "120-220字，3-4句连续的话：这份资料讲什么、按什么顺序展开、学完能做什么。不要逐节复述，不要出现省略号或分号拼接。",
  "knowledge_map": ["4-8个短知识点，每个4-16字，名词短语；不要整句，不要省略号，不要重复"],
  "closing": "80-150字，2-3句完整结语，按给定人设收束，不要中途截断"
}"""


def author_wrapup(
    client: LLMClient,
    *,
    title: str,
    course: str,
    sections: list[LectureSection],
    persona: str = "老师",
    foundation: str | None = None,
    target_score: int | None = None,
    days_left: int | None = None,
    gen_lang: str = "zh",
) -> AuthoredWrapup:
    sec_rows = []
    for i, sec in enumerate(sections, start=1):
        summary = (sec.summary or "").strip()
        if not summary:
            for b in sec.blocks:
                if b.kind == BlockKind.SUMMARY and (b.text or "").strip():
                    summary = b.text.strip()
                    break
        if not summary:
            for b in sec.blocks:
                if b.kind == BlockKind.PARAGRAPH and (b.text or "").strip():
                    summary = b.text.strip()[:240]
                    break
        sec_rows.append(f"{i}. {sec.title}\n   摘要：{summary[:260]}")
    prompt = (
        f"资料标题：{title}\n课程：{course}\n目标分：{target_score}\n剩余天数：{days_left}\n基础：{foundation}\n人设：{persona}\n"
        f"生成语言：{gen_lang}\n人设风格：{PERSONA_STYLE.get(persona, PERSONA_STYLE['老师'])}\n\n各节内容：\n" + "\n".join(sec_rows) + "\n\n"
        "请只依据这些节的内容写全篇概述、知识地图和结语。规则：\n"
        "- overview 必须是连贯的 3–4 句，不要用分号把各节小结拼起来，不要出现省略号；\n"
        "- knowledge_map 只放短知识点名词短语，4–8 条，必须能在正文找到；不要整句、不要省略号；\n"
        "- closing 是全章总结，必须 400–600 字、6–8 句，明显体现人设，不能只写两三句；"
        "结构必须包含：①用一句话串起各节知识链；②本章最容易混淆/漏掉的一个具体点；③接下来怎么复习的具体动作；④按人设给一段完整的鼓励收束。不要空泛鸡汤。\n"
        "- 不编造资料没有的结论；用给定语言输出。\n\n"
        f"输出 JSON：\n{_WRAPUP_SCHEMA}"
    )
    try:
        data = client.json(SYSTEM_PROMPT, prompt, max_tokens=1600, temperature=0.25)
        return AuthoredWrapup.model_validate(data)
    except Exception:
        return AuthoredWrapup()


def fallback_wrapup(sections: list[LectureSection], title: str, persona: str = "老师", gen_lang: str = "zh") -> AuthoredWrapup:
    names = [ _clean_section_title(s.title) or s.title for s in sections ]
    names = [x for x in names if x][:16]
    if gen_lang == "en":
        overview = f"This lecture works through {title} in {len(sections)} connected sections: " + "; ".join(names) + ". Read each section in order, follow the worked example, then close the notes and reproduce the key steps yourself."
        closing = "Take it one section at a time. Read the explanation, work one example, then close the notes and try a problem from memory. If a step is unclear, return to the cited source page rather than memorizing the conclusion."
    elif gen_lang == "hant":
        overview = f"本講義圍繞《{title}》展開，依次整理" + "、".join(names) + f"，共 {len(sections)} 節。建議先讀摘要與目錄，再按節理解概念、跟做例題，最後合上講義自己複述一遍。"
        closing = "別急著一次讀完，先按節把概念、例題和易錯點串起來。讀完一節就合上講義，自己複述並做一道題；卡住時回到出處頁核對，而不是只記結論。"
    else:
        overview = f"本讲义围绕《{title}》展开，依次整理" + "、".join(names) + f"，共 {len(sections)} 节。建议先读摘要与目录，再按节理解概念、跟做例题，最后合上讲义自己复述一遍，把“看懂”变成“能独立做出来”。"
        chain = "、".join(names) if names else "本章各节"
        persona_tail = {
            "老师": "最后按考试讲评的方式提醒你：先判断题型，再写条件和步骤，最后检查边界和单位。把本章两道典型题合上讲义重做一遍，错在哪里就回到对应出处页，不要用“看懂了”代替“做对了”。",
            "温柔小姐姐": "别急着把整章一口气吞下去，今天先挑一节，合上讲义复述概念，再做一道例题；卡住就回到出处页慢慢看。你已经愿意坐下来学了，这本身就很了不起，剩下的我们一节一节来，你会越来越稳的。",
            "学术AI": "请把本章视为一条可迁移的方法链，而不是孤立结论。每节按“识别问题—写出条件—执行步骤—检查边界”复述一次；无法解释的步骤回到出处页核对。完成两轮自测后，再进入综合题训练。",
            "阳光小哥哥": "兄弟/姐妹，别只看不动笔。今天挑一节，合上讲义自己写一遍步骤，再找一道题验证；错了就回出处页看一眼，不丢人。把这一节拿下，明天再推下一节，进度是做题做出来的！",
            "暴力极客": "直接说：别把方法当收藏品。每节只做三件事：识别题型、复述步骤、独立做一题。卡住就回出处页，不要靠感觉；做完再谈掌握，别用看懂自我感动。",
        }
        closing = f"本章的知识链是：{chain}。复习时不要只背结论，要能把每一节的定义、条件、典型步骤和易错点串起来。最容易失分的地方，是把相邻概念混在一起、漏掉适用条件或跳过关键步骤；做题时先判断题型，再写清条件和过程，最后检查边界与单位。如果时间有限，先搭起“目录—定义—例题—自测”的框架，再逐节补细节；遇到卡点先回到出处页核对，不要用看答案代替独立推导。接下来请合上讲义，按目录复述一遍各节要点，再挑两道理科/文科典型题独立完成，错题回到对应出处页核对。{persona_tail.get(persona, persona_tail['老师'])}"
    return AuthoredWrapup(overview=overview, knowledge_map=names, closing=closing)


def _sanitize_visible_text(text: str) -> str:
    """Turn model-escaped line breaks into real layout breaks.

    Some providers return the two characters ``\n`` inside a JSON string.
    Those must not reach the PDF as visible “\n(1)” text. Do not touch real
    LaTeX commands such as ``\nabla``.
    """
    if not text:
        return text
    text = re.sub(r"\\r\\n", "\n", text)
    text = re.sub(r"\\n(?=[\s(（\[【\u4e00-\u9fff。，；：！？、,.;:!?]|\d|$)", "\n", text)
    text = re.sub(r"\\t(?=[\s(（])", " ", text)
    # Normalize common raw TeX degree/spacing fragments that escape math mode.
    text = text.replace("\\,", " ")
    text = text.replace("\\;", " ")
    text = text.replace("\\!", "")
    text = re.sub(r"\^\\circ", "°", text)
    text = text.replace("\\circ", "°")
    return text


def normalize_lecture_sections(sections: list[LectureSection], gen_lang: str = "zh") -> list[LectureSection]:
    """Apply general fixes after the last section is authored.

    - A final recap page chunk must not pretend to be another new method.
    - Repeated / truncated headings get cleaned.
    - Never merge by deleting source content; rename the role instead.
    """
    if not sections:
        return sections
    for sec in sections:
        # A generated block inside a sourced section inherits the section's
        # provenance instead of being rejected by the block-level evidence gate.
        if sec.source_refs:
            for block in sec.blocks:
                if block.kind != BlockKind.FIGURE and (block.text or "").strip() and not block.source_refs:
                    block.source_refs = list(sec.source_refs)
    for sec in sections:
        if sec.title:
            sec.title = _sanitize_visible_text(sec.title)
        if sec.summary:
            sec.summary = _sanitize_visible_text(sec.summary)
        for block in sec.blocks:
            if block.text:
                block.text = _sanitize_visible_text(block.text)
            if block.figure and block.figure.caption:
                block.figure.caption = _sanitize_visible_text(block.figure.caption)
    review_words = ("总结", "回顾", "复习", "小结", "概述", "方法总览", "综合")
    for sec in sections:
        cleaned = _clean_section_title(sec.title)
        if cleaned:
            sec.title = cleaned
    last = sections[-1]
    if len(sections) >= 2:
        text = " ".join([last.title] + [b.text for b in last.blocks[:3] if b.text])
        earlier = [s.title for s in sections[:-1]]
        # Domain-neutral recap detection: count how many earlier section titles
        # have a meaningful phrase repeated in the last section.
        def _title_terms(title: str) -> list[str]:
            parts = [x.strip() for x in re.split(r"[\s、，,：:（）()/·—-]+", title or "") if len(x.strip()) >= 2]
            return [x[:10] for x in parts[:4]]
        hits = sum(1 for title in earlier if any(term in text for term in _title_terms(title)))
        looks_recap = any(w in last.title for w in review_words) or hits >= 2
        # Never replace an already-specific title with the generic "本章总结".
        # The recap rule is only a rescue for generic/empty headings.
        current_title = (last.title or "").strip()
        generic_current = (
            not current_title
            or current_title in {"正文", "核心内容", "补充内容", "教材内容", "课程内容", "Chapter"}
            or bool(re.fullmatch(r"知识点\s*\d+", current_title))
        )
        if looks_recap and generic_current:
            if gen_lang == "en":
                last.title = "Chapter recap"
            elif gen_lang == "hant":
                last.title = "本章總結"
            else:
                last.title = "本章总结"
    # Keep ids stable (anchors); resolve duplicate display titles by content,
    # never by appending (2)/(3) (which is not a chapter title).
    seen: set[str] = set()
    for index, sec in enumerate(sections, start=1):
        base = (sec.title or "").strip() or ("Chapter" if gen_lang == "en" else "核心考点")
        if base in seen:
            base = _fallback_unique_title(sec, index, seen, gen_lang)
        sec.title = base
        seen.add(base)
    return sections

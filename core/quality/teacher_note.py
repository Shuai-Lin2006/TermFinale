"""老师重点说明 → 可执行规则。

用户会说：
- “只考隐函数求导、高阶导数间接法、参数方程二阶导、变化率实际问题；其他不考”
- “第 5 页例 3 必考，参数方程不考”
- “不考 10 个基团命名：-R、-X、-NO2 …；其余都考”
- “命题那几个基团不考”（歧义：要去资料里找具体是哪些基团）

本模块把这些话解析成：页码、必考项、不考项、只考白名单、字面禁用 token。
解析不确定的标 unresolved（存疑），绝不反问用户。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# 负面 / 正面 / 白名单标记（负面优先判断）
_NEG = ("不考", "不要求", "不用看", "跳过", "略过", "排除", "别考", "无需",
        "不涉及", "不重点", "不作为考点", "不复习", "不学")
_ONLY = ("只考", "只讲", "仅考", "只要求", "范围是", "只复习", "只看", "重点只")
_POS = ("必考", "重点", "要考", "会考", "常考", "掌握", "记住", "背下来",
        "重点看", "一定要", "必须")

_PAGE_RANGE = re.compile(r"第?\s*(\d+)\s*(?:[-–—~至到]\s*(\d+))?\s*页")
_P_PAGE = re.compile(r"(?<![A-Za-z0-9])P\.?\s*(\d+)", re.IGNORECASE)
_CLAUSE_SPLIT = re.compile(r"[，,；;。\n]+")
_ITEM_SPLIT = re.compile(r"[、，,/]|以及|及|和")
# 化学基团这类 token：-R、-NO2、-SO3H、-COOH …
_TOKEN = re.compile(r"(?<![A-Za-z0-9])-[A-Za-z][A-Za-z0-9₀-₉]*")
_GROUP_HINT = ("基团", "取代基", "官能团")
_MARKERS = _NEG + _ONLY + _POS


@dataclass
class TeacherRules:
    page_refs: list[int] = field(default_factory=list)
    must_topics: list[str] = field(default_factory=list)
    ban_topics: list[str] = field(default_factory=list)
    only_topics: list[str] = field(default_factory=list)
    literal_bans: list[str] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    source: str = ""

    @property
    def empty(self) -> bool:
        return not any((self.page_refs, self.must_topics, self.ban_topics,
                        self.only_topics, self.literal_bans))

    def to_dict(self) -> dict:
        return {"page_refs": self.page_refs, "must_topics": self.must_topics,
                "ban_topics": self.ban_topics, "only_topics": self.only_topics,
                "literal_bans": self.literal_bans, "unresolved": self.unresolved,
                "notes": self.notes}


def _clean_topic(text: str) -> str:
    text = (text or "").strip()
    # 化学 token 已进 literal_bans，不再作为中文考点；去掉“10 个/3 类”这类计数
    text = _TOKEN.sub(" ", text)
    text = re.sub(r"^\s*\d+\s*(?:个|类|种|条)?\s*", "", text)
    text = re.sub(r"^第?\s*\d+\s*(?:[-–—~至到]\s*\d+)?\s*页\s*(?:例|题)?\s*\d*(?:\.\d+)*\s*", "", text)
    for marker in sorted(_MARKERS, key=len, reverse=True):
        text = text.replace(marker, " ")
    text = re.sub(r"(老师|同学|我们|这次|本次|期末|考试|内容|部分|章节|知识点|考点|题目|要|的)+", " ", text)
    text = re.sub(r"[\s，,。；;：:、（）()【】\[\]]+", " ", text).strip()
    # 去掉“例3”“第5题”这类纯编号
    if re.fullmatch(r"(?:例|题)?\s*\d+(?:\.\d+)*", text):
        return ""
    return text[:24]


def _topic_items(clause: str) -> list[str]:
    raw = clause
    for marker in sorted(_ONLY + _NEG + _POS, key=len, reverse=True):
        raw = raw.replace(marker, " ")
    items = []
    for part in _ITEM_SPLIT.split(raw):
        topic = _clean_topic(part)
        if topic and topic not in items:
            items.append(topic)
    return items


def _find_group_token_line(source_text: str) -> tuple[str, int] | None:
    """在资料里找“基团/取代基”列表所在行，返回 (原文行, 页号)。"""
    if not source_text:
        return None
    page_no = 0
    for line in source_text.splitlines():
        m = re.search(r"第\s*(\d+)\s*页", line)
        if m:
            page_no = int(m.group(1))
        if any(hint in line for hint in _GROUP_HINT):
            if _TOKEN.search(line):
                return line, page_no
    # 有些资料把列表和“基团”分在两行：向后多看 5 行
    lines = source_text.splitlines()
    for i, line in enumerate(lines):
        if any(hint in line for hint in _GROUP_HINT):
            for nxt in lines[i:i + 6]:
                if len(_TOKEN.findall(nxt)) >= 3:
                    m = re.search(r"第\s*(\d+)\s*页", nxt)
                    return nxt, int(m.group(1)) if m else page_no
    return None


def parse_teacher_note(note: str, source_text: str = "") -> TeacherRules:
    """把一段老师重点说明解析成规则；解析不出来就留 unresolved。"""
    rules = TeacherRules()
    note = (note or "").strip()
    if not note:
        return rules
    rules.source = note

    # 1) 页码（含范围）
    for m in _PAGE_RANGE.finditer(note):
        start = int(m.group(1))
        end = int(m.group(2)) if m.group(2) else start
        for n in range(min(start, end), max(start, end) + 1):
            if 1 <= n <= 5000 and n not in rules.page_refs:
                rules.page_refs.append(n)
    for m in _P_PAGE.finditer(note):
        n = int(m.group(1))
        if n not in rules.page_refs:
            rules.page_refs.append(n)

    # 2) 显式化学 token / 英文 token
    tokens = list(dict.fromkeys(_TOKEN.findall(note)))
    if tokens:
        rules.literal_bans.extend(tokens)

    # 3) 逐句解析
    for clause in _CLAUSE_SPLIT.split(note):
        clause = clause.strip()
        if not clause:
            continue
        has_neg = any(k in clause for k in _NEG)
        has_only = any(k in clause for k in _ONLY)
        has_pos = any(k in clause for k in _POS) and not has_neg and not has_only

        if has_only:
            rules.only_topics.extend(
                t for t in _topic_items(clause) if t and t not in rules.only_topics)
        elif has_neg:
            rules.ban_topics.extend(
                t for t in _topic_items(clause)
                if t and t not in rules.ban_topics and not t.startswith("其他"))
        elif has_pos:
            rules.must_topics.extend(
                t for t in _topic_items(clause) if t and t not in rules.must_topics)

    # 3.1) “不考基团命名”要能命中“常见有机基团名称的识别”这类考点
    if any(h in note for h in _GROUP_HINT) and ("命名" in note or "名称" in note):
        for term in ("基团命名", "基团名称"):
            if term not in rules.ban_topics:
                rules.ban_topics.append(term)

    # 4) “基团”歧义：note 只说了“基团”，没有列 token → 去原文找
    if any(hint in note for hint in _GROUP_HINT) and len(rules.literal_bans) < 2:
        found = _find_group_token_line(source_text)
        if found:
            line, page = found
            resolved = list(dict.fromkeys(_TOKEN.findall(line)))
            for t in resolved:
                if t not in rules.literal_bans:
                    rules.literal_bans.append(t)
            if resolved:
                rules.notes.append(
                    f"“基团”自动解析为 {len(resolved)} 个：{'、'.join(resolved)}"
                    + (f"（资料第 {page} 页）" if page else ""))
        else:
            rules.unresolved.append("基团（资料里没找到具体列表）")

    # 5) 去重 & 去掉互相重叠的噪声
    def _uniq(items):
        out = []
        for x in items:
            x = x.strip()
            if x and len(x) >= 2 and x not in out:
                out.append(x)
        return out
    rules.must_topics = _uniq(rules.must_topics)
    rules.ban_topics = _uniq(rules.ban_topics)
    rules.only_topics = _uniq(rules.only_topics)
    rules.literal_bans = _uniq(rules.literal_bans)
    # “只考”里如果也混进了不考项，剔除
    rules.ban_topics = [t for t in rules.ban_topics if t not in rules.only_topics]
    if rules.only_topics and not rules.must_topics:
        rules.notes.append("按“只考”白名单执行：白名单外的考点会被过滤或判失败")
    return rules


def topic_matches(topic: str, rule: str) -> bool:
    """考点与规则是否指同一件事：包含 或 2-gram 覆盖率 ≥0.5。"""
    a = re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", topic or "")
    b = re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", rule or "")
    if not a or not b:
        return False
    if a in b or b in a:
        return True
    if len(b) < 2:
        return False
    grams_b = {b[i:i + 2] for i in range(len(b) - 1)}
    grams_a = {a[i:i + 2] for i in range(len(a) - 1)}
    if not grams_b or not grams_a:
        return False
    # 用较短一侧作分母：允许“相关变化率”匹配“变化率实际问题”这类详略差异
    return len(grams_b & grams_a) / min(len(grams_b), len(grams_a)) >= 0.5

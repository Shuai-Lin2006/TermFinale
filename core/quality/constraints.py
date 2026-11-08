"""任务级约束 + 生成后硬校验。

讲义 / 考点提取 / 训练试卷 各自有独立的范围（页码范围）、排除项、
答案要求与题型结构；这些约束既要写进提示词（事前），也要在生成后
用确定性规则复核（事后）。复核不通过的硬违规会触发重试，重试仍不过
则任务失败——不允许"看起来生成完了"就算通过。

约定：
- ``issues``   硬违规：违反用户明确设定的约束，重试后仍存在即失败；
- ``warnings`` 软信号：可疑但不阻断（例如疑似超纲、覆盖率偏低），
  仍会作为重试反馈，让模型有机会自行修正。

只做能确定性复核的检查；语义判断（是否超纲）只给 warning，避免误杀。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# --------------------------------------------------------------------------- #
# 常量
# --------------------------------------------------------------------------- #
MAX_EXCLUDE_TERMS = 30
MAX_TERM_CHARS = 24

ANSWER_MODES = ("required", "forbidden", "optional")

# 讲义模板标题：不是知识点，不参与"是否有资料依据"的判断
GENERIC_HEADINGS = {
    "概念与定义", "原理与公式", "例题与拆解", "易错与考场用法",
    "概念", "定义", "原理", "公式", "例题", "拆解", "易错", "考场用法",
    "小结", "总结", "引言", "补充", "目录", "概述", "本章小结",
    "示例", "练习", "习题", "考点", "答案", "解析",
}

_PAGE_HEADER_RE = re.compile(r"》\s*第\s*(\d+)\s*页】")
_PAGE_CITE_RE = re.compile(r"第\s*(\d+)\s*页")
_P_CITE_RE = re.compile(r"[（(]\s*P\.?\s*(\d+)\s*[)）]|(?<![A-Za-z0-9])P\.\s*(\d+)")
_IMAGE_TAG_RE = re.compile(r"\[\[\[IMAGE:.*?\]\]\]", re.S)
_MATH_RE = re.compile(r"\$\$.*?\$\$|\$[^$\n]*\$", re.S)

_QUESTION_RE = re.compile(r"(?m)^\s*(?:\*\*|__)?\s*(\d{1,2})\s*[.、．)）]\s*")
_EXAM_POINT_RE = re.compile(r"【考点[:：]\s*([^】]{2,60})】")
_EXTRACT_POINT_RE = re.compile(r"(?m)^###\s*考点[:：]\s*(.+)$")
_KEYWORD_RE = re.compile(r"\[\[([^|\]]+?)\|")

_ANSWER_SECTION_RE = re.compile(r"(?m)^#{1,3}\s*(答案|参考答案|答案与解析|答案及解析)")
_ANSWER_MARK_RE = re.compile(r"【答案】|【解析】|答案[:：]|正确答案[:：]")
_SYNTAX_PLACEHOLDER_RE = re.compile(r"@@\w+@@")


# --------------------------------------------------------------------------- #
# 约束模型
# --------------------------------------------------------------------------- #
@dataclass
class TaskConstraints:
    """一个生成任务的全部约束。不同任务互不继承默认值。"""

    task: str = "guide"                      # guide / extract / exam / analysis
    page_start: int | None = None
    page_end: int | None = None
    exclude_terms: list[str] = field(default_factory=list)
    answer_mode: str = "optional"            # required / forbidden / optional
    extract_type: str = ""                   # points / nouns / questions
    sections: list[dict] = field(default_factory=list)   # [{name,count,points}]
    material_kind: str = "exam"              # exam / lecture
    strict: bool = True                      # 违规是否直接判失败
    max_retries: int = 2
    # 老师重点（由 teacher_note.parse_teacher_note 解析后注入）
    teacher_note: str = ""
    must_topics: list[str] = field(default_factory=list)
    weak_topics: list[str] = field(default_factory=list)
    ban_topics: list[str] = field(default_factory=list)
    only_topics: list[str] = field(default_factory=list)
    literal_bans: list[str] = field(default_factory=list)
    required_pages: list[int] = field(default_factory=list)

    # ---------------- 构造 ---------------- #
    @classmethod
    def from_options(cls, task: str, options: dict | None = None) -> "TaskConstraints":
        """从 API options 里读出 ``constraints`` 子对象（兼容顶层写法）。"""
        options = options or {}
        raw = options.get("constraints")
        raw = raw if isinstance(raw, dict) else {}
        merged = {**options, **raw}   # 任务级约束优先

        page_start = _as_page(merged.get("page_start"))
        page_end = _as_page(merged.get("page_end"))
        if page_start and page_end and page_start > page_end:
            page_start, page_end = page_end, page_start

        sections = _clean_sections(merged.get("sections") or options.get("sections"))
        answer_mode = _answer_mode(task, merged, options)
        return cls(
            task=task,
            page_start=page_start,
            page_end=page_end,
            exclude_terms=_clean_terms(merged.get("exclude_terms")),
            answer_mode=answer_mode,
            extract_type=str(merged.get("extract_type") or options.get("extract_type") or ""),
            sections=sections,
            material_kind=str(merged.get("material_mode") or "exam"),
            strict=bool(merged.get("strict", True)),
            max_retries=max(0, min(5, int(merged.get("max_retries", 2) or 0))),
            teacher_note=str(merged.get("teacher_note") or options.get("teacher_note") or ""),
        )

    def apply_teacher_rules(self, rules) -> None:
        """把解析后的老师规则并进约束；不覆盖用户已手填的同类项。"""
        if rules is None:
            return
        for attr, target in (("must_topics", self.must_topics),
                             ("weak_topics", self.weak_topics),
                             ("ban_topics", self.ban_topics),
                             ("literal_bans", self.literal_bans)):
            for item in getattr(rules, attr, []) or []:
                if item and item not in target:
                    target.append(item)
        if getattr(rules, "only_topics", None):
            self.only_topics = list(dict.fromkeys(rules.only_topics))
        for page in getattr(rules, "page_refs", []) or []:
            if page not in self.required_pages:
                self.required_pages.append(page)
        if getattr(rules, "source", ""):
            self.teacher_note = rules.source

    # ---------------- 查询 ---------------- #
    @property
    def has_scope(self) -> bool:
        return bool(self.page_start or self.page_end)

    @property
    def paper_total(self) -> float:
        return round(sum(s["count"] * s["points"] for s in self.sections), 1)

    def in_scope(self, page: int | None) -> bool:
        if page is None or not self.has_scope:
            return True
        if self.page_start and page < self.page_start:
            return False
        if self.page_end and page > self.page_end:
            return False
        return True

    def scope_label(self) -> str:
        if not self.has_scope:
            return "全部页"
        start = self.page_start or 1
        if self.page_end:
            return f"第 {start}–{self.page_end} 页"
        return f"第 {start} 页之后"

    def to_dict(self) -> dict:
        return {
            "task": self.task,
            "page_start": self.page_start,
            "page_end": self.page_end,
            "exclude_terms": list(self.exclude_terms),
            "answer_mode": self.answer_mode,
            "extract_type": self.extract_type,
            "sections": list(self.sections),
            "material_kind": self.material_kind,
            "strict": self.strict,
            "max_retries": self.max_retries,
            "teacher_note": self.teacher_note,
            "must_topics": list(self.must_topics),
            "weak_topics": list(self.weak_topics),
            "ban_topics": list(self.ban_topics),
            "only_topics": list(self.only_topics),
            "literal_bans": list(self.literal_bans),
            "required_pages": list(self.required_pages),
        }


def default_constraints(task: str, **kwargs) -> TaskConstraints:
    """服务层直接调用（没有 API options）时的默认约束。"""
    answer_mode = "optional"
    if task == "exam":
        answer_mode = "required" if kwargs.get("with_answer", True) else "forbidden"
    elif task == "extract" and kwargs.get("extract_type") == "questions":
        answer_mode = "required" if kwargs.get("with_answer", True) else "forbidden"
    return TaskConstraints(
        task=task,
        answer_mode=answer_mode,
        extract_type=str(kwargs.get("extract_type") or ""),
        material_kind=kwargs.get("material_kind", "exam"),
        exclude_terms=list(kwargs.get("exclude_terms") or []),
        page_start=kwargs.get("page_start"),
        page_end=kwargs.get("page_end"),
        sections=_clean_sections(kwargs.get("sections")),
        strict=bool(kwargs.get("strict", True)),
    )


def _as_page(value) -> int | None:
    try:
        page = int(value)
    except (TypeError, ValueError):
        return None
    return page if page >= 1 else None


def _clean_terms(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        chunks = re.split(r"[,，;；、\s]+", value)
    else:
        chunks = [str(v) for v in value]
    out: list[str] = []
    for term in chunks:
        term = term.strip()
        if not term or len(term) > MAX_TERM_CHARS:
            continue
        if term not in out:
            out.append(term)
    return out[:MAX_EXCLUDE_TERMS]


def _clean_sections(value) -> list[dict]:
    if not isinstance(value, (list, tuple)):
        return []
    out: list[dict] = []
    for item in value:
        if isinstance(item, dict):
            name = str(item.get("name") or item.get("type") or "").strip()
            count = item.get("count")
            points = item.get("points")
        else:
            try:
                name, count, points = item
            except (TypeError, ValueError):
                continue
            name = str(name or "").strip()
        try:
            count = max(1, min(100, int(count)))
            points = max(1.0, min(100.0, float(points)))
        except (TypeError, ValueError):
            continue
        if not name:
            continue
        out.append({"name": name, "count": count, "points": points})
    return out


def _answer_mode(task: str, merged: dict, options: dict) -> str:
    explicit = str(merged.get("answer_mode") or "").strip().lower()
    if explicit in ANSWER_MODES:
        return explicit
    if task == "exam":
        raw = merged.get("exam_answer", merged.get("with_answer", True))
        return "required" if raw else "forbidden"
    if task == "extract":
        extract_type = merged.get("extract_type") or options.get("extract_type")
        if extract_type == "questions":
            raw = merged.get("with_answer", True)
            return "required" if raw else "forbidden"
    return "optional"


# --------------------------------------------------------------------------- #
# 提示词：把任务约束写进 system prompt
# --------------------------------------------------------------------------- #
def render_prompt(c: TaskConstraints) -> str:
    """按任务渲染约束段。返回空串表示没有额外约束。"""
    lines: list[str] = []

    if c.has_scope:
        lines.append(
            f"【范围硬约束】本次只处理{c.scope_label()}的内容：只允许引用范围内的页码与知识点；"
            "范围外的内容一律不得出现，更不得凭记忆补写。")

    if c.exclude_terms:
        lines.append("【排除项硬约束】以下内容不得作为考点、标题或题目出现"
                     "（正文顺带提及不要展开，也不要放进【延伸】）："
                     + "、".join(c.exclude_terms)
                     + "。资料本身没有这些内容时，更不得补写。")

    # 老师重点：只考白名单 / 必考 / 不考 / 字面禁用 / 点名页码
    if c.only_topics:
        lines.append("【老师只考】本次只允许以下考点：" + "、".join(c.only_topics)
                     + "。白名单之外的知识点不得作为考点、章节标题或题目出现；"
                       "正文顺带提及不要展开、不要举例。")
    if c.must_topics:
        lines.append("【老师必考】必须覆盖并在考点/标题/题目中明确写出："
                     + "、".join(c.must_topics) + "。漏掉即不合格。")
    if c.weak_topics:
        lines.append("【学生薄弱点·必须加讲】以下主题不能只提一句：先补前置知识，"
                     "再从定义/直觉讲起，给 2–3 个由浅入深的例子，指出常见错误；"
                     "篇幅要明显高于普通小节：" + "、".join(c.weak_topics) + "。")
    if c.ban_topics:
        lines.append("【老师不考】以下内容不得作为考点、章节标题或题目出现："
                     + "、".join(c.ban_topics) + "。")
    if c.literal_bans:
        lines.append("【老师禁用符号/词】正文与题目中不得出现：" + "、".join(c.literal_bans) + "。")
    if c.required_pages:
        lines.append("【老师点名页码】必须覆盖并引用：" +
                     "、".join(f"第 {n} 页" for n in c.required_pages)
                     + "。找不到对应内容时也必须在该页位置说明“该页仅含图示/无新增考点”。")

    if c.task == "guide":
        lines.append(
            "【讲义任务约束】只依据资料讲；页码只能引用资料里真实存在的页；"
            "不得把资料外的结论写成正文（补充内容必须标【延伸】）。")
        if c.material_kind == "lecture":
            lines.append("【资料类型】这是课堂讲义而不是考试重点：不强行输出考点/分值/应试套路。")
    elif c.task == "extract":
        lines.append(
            "【提取任务约束】只从资料中提取，不得新增资料外的知识或讲解；"
            "每个考点/名词后面必须写 `[出处：《文件名》第X页]`，页码必须来自资料页头，"
            "找不到页码就照实写“资料未标注页码”，不得编号码。")
        if c.answer_mode == "forbidden":
            lines.append("【答案要求】只输出题目，绝对不要给答案或解析。")
        elif c.answer_mode == "required":
            lines.append("【答案要求】每道题下方必须带【答案】与【解析】。")
    elif c.task == "exam":
        if c.sections:
            lines.append("【试卷结构硬约束】题型、题数、分值必须严格按下列结构，不得增删题型，不得改题数：\n"
                         + render_sections(c.sections)
                         + f"\n- 合计：{c.paper_total:g} 分")
        lines.append(
            "【试卷任务约束】题目必须是新编的：严禁写“参考原资料第X页”之类的页码；"
            "每个大题必须用二级标题，小题用 1. 编号，每题末尾标【考点：xxx】。")
        if c.answer_mode == "forbidden":
            lines.append("【答案要求】只输出题目，不要输出答案，也不要写“# 答案与解析”。")
        elif c.answer_mode == "required":
            lines.append("【答案要求】最后必须单独输出 `# 答案与解析`，按题号覆盖整套试卷。")
    elif c.task == "analysis":
        lines.append("【分析任务约束】只依据资料梳理结构与因果，不补充资料外内容；页码必须真实。")

    return "\n".join(lines)


def render_sections(sections: list[dict]) -> str:
    lines = []
    for sec in sections:
        count, points = sec["count"], sec["points"]
        lines.append(f"- {sec['name']}：{count} 题 × {points:g} 分 = {count * points:g} 分")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# 范围过滤
# --------------------------------------------------------------------------- #
def page_no(page: str) -> int | None:
    m = re.search(r"第\s*(\d+)\s*页", page or "")
    return int(m.group(1)) if m else None


def source_pages(text: str) -> set[int]:
    """资料页头里的页码集合（只认【…第 N 页】页头，避免把正文引用当页头）。"""
    return {int(m.group(1)) for m in _PAGE_HEADER_RE.finditer(text or "")}


def cited_pages(text: str) -> set[int]:
    """正文里出现的页码引用（第 N 页 / P.N / （P.N））。图片标签不算。"""
    body = _IMAGE_TAG_RE.sub("", text or "")
    pages = {int(m.group(1)) for m in _PAGE_CITE_RE.finditer(body)}
    for m in _P_CITE_RE.finditer(body):
        value = m.group(1) or m.group(2)
        if value:
            pages.add(int(value))
    return pages


def scope_pages(pages: list[str], c: TaskConstraints) -> list[str]:
    """按页码范围筛选解析后的页；无页码的页保持原样（无法判断就不过滤掉内容）。"""
    if not c.has_scope:
        return list(pages)
    kept = [p for p in pages if c.in_scope(page_no(p))]
    return kept


# --------------------------------------------------------------------------- #
# 校验报告
# --------------------------------------------------------------------------- #
@dataclass
class ValidationReport:
    task: str = "guide"
    issues: list[str] = field(default_factory=list)     # 硬违规
    warnings: list[str] = field(default_factory=list)   # 软信号
    metrics: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.issues

    def add(self, message: str) -> None:
        if message not in self.issues:
            self.issues.append(message)

    def warn(self, message: str) -> None:
        if message not in self.warnings:
            self.warnings.append(message)

    def merge(self, other: "ValidationReport", prefix: str = "") -> None:
        for item in other.issues:
            self.add(f"{prefix}{item}" if prefix else item)
        for item in other.warnings:
            self.warn(f"{prefix}{item}" if prefix else item)
        self.metrics.update(other.metrics)

    def feedback(self, hard_limit: int = 6, soft_limit: int = 3) -> str:
        """重试时回灌给模型的修正说明。"""
        items = list(self.issues[:hard_limit])
        if len(self.issues) > hard_limit:
            items.append(f"（同类硬违规另有 {len(self.issues) - hard_limit} 条）")
        items.extend(self.warnings[:soft_limit])
        if not items:
            return ""
        return ("【上一版输出未通过生成后校验，请只针对下列问题修正后重新输出】\n- "
                + "\n- ".join(items)
                + "\n修正时保持原有格式与结构，不要新增无关内容。")

    def summary(self) -> str:
        if self.ok and not self.warnings:
            return "校验通过"
        parts = []
        if self.issues:
            parts.append(f"硬违规 {len(self.issues)} 条")
        if self.warnings:
            parts.append(f"提示 {len(self.warnings)} 条")
        return "；".join(parts)

    def to_dict(self) -> dict:
        return {"task": self.task, "ok": self.ok,
                "issues": list(self.issues), "warnings": list(self.warnings),
                "metrics": dict(self.metrics), "summary": self.summary()}


# --------------------------------------------------------------------------- #
# 生成后硬校验
# --------------------------------------------------------------------------- #
def validate_output(
    markdown: str,
    constraints: TaskConstraints,
    *,
    source_text: str = "",
    allowed_pages: set[int] | list[int] | None = None,
    stage: str = "final",
) -> ValidationReport:
    """复核一次生成结果。

    - ``allowed_pages``：本段内容允许引用的页码（按章 / 按块）；为空时用
      约束里的页码范围（再退回到资料页头集合）。
    - ``stage``：``chunk``/``chapter`` 用于分块生成（跳过整篇级检查），
      ``final`` 用于最终合并结果。
    """
    report = ValidationReport(task=constraints.task)
    text = markdown or ""

    if not text.strip():
        report.add("生成结果为空")
        return report
    if len(text.strip()) < 20:
        report.warn(f"生成结果过短（{len(text.strip())} 字），疑似截断")

    for issue in syntax_issues(text):
        report.add(issue)

    # 1. 排除项：token 级字面 + 中文考点级 ------------------------------- #
    body = _strip_citations_images(text)
    literal_terms = [t for t in constraints.exclude_terms if _looks_like_token(t)]
    topic_bans = [t for t in constraints.exclude_terms if not _looks_like_token(t)]
    hits = contains_terms(body, literal_terms + constraints.literal_bans)
    if hits:
        report.add("出现老师禁用符号/词：" +
                   "、".join(f"{term}（{count} 处）" for term, count in hits[:5]))
    _check_teacher_rules(report, text, constraints, stage, extra_bans=topic_bans)

    # 2. 页码 ------------------------------------------------------------ #
    src = source_pages(source_text)
    cited = cited_pages(text)
    allowed = _allowed_page_set(constraints, src, allowed_pages)
    if cited and allowed is not None:
        bad = sorted(p for p in cited if p not in allowed)
        if bad:
            report.add("页码不在允许范围内：" + "、".join(f"第{p}页" for p in bad[:8]))
    report.metrics["pages_cited"] = len(cited)

    # 3. 按任务检查 ------------------------------------------------------ #
    if constraints.task == "guide":
        _check_guide(report, text, constraints, source_text, cited, stage)
    elif constraints.task == "extract":
        _check_extract(report, text, constraints, src, stage, source_text)
    elif constraints.task == "exam":
        _check_exam(report, text, constraints, stage)
    elif constraints.task == "analysis":
        _check_analysis(report, text, stage)

    # 4. 答案要求（通用兜底） -------------------------------------------- #
    _check_answer_mode(report, text, constraints, stage)

    return report


def _allowed_page_set(c: TaskConstraints, src: set[int],
                      allowed_pages: set[int] | list[int] | None) -> set[int] | None:
    if allowed_pages:
        return set(allowed_pages)
    if c.has_scope:
        upper = c.page_end or (max(src) if src else None)
        lower = c.page_start or 1
        if upper is None:
            return None
        return {p for p in range(lower, upper + 1)}
    return src or None


def syntax_issues(text: str) -> list[str]:
    issues: list[str] = []
    stripped = _IMAGE_TAG_RE.sub("", text).replace("$$", "")
    if stripped.count("$") % 2:
        issues.append("行内 $ 公式未闭合")
    if text.count("$$") % 2:
        issues.append("$$ 公式块未闭合")
    if text.count("```") % 2:
        issues.append("``` 代码块未闭合")
    leftovers = _SYNTAX_PLACEHOLDER_RE.findall(text)
    if leftovers:
        issues.append(f"占位符残留 {len(leftovers)} 个")
    bad_tag = any("[[[IMAGE:" in line and "]]]" not in line for line in text.splitlines())
    if bad_tag:
        issues.append("图片标签未闭合")
    return issues


def contains_terms(text: str, terms: list[str]) -> list[tuple[str, int]]:
    """返回 [(排除词, 出现次数)]。中文按原样匹配，英文忽略大小写。"""
    hits: list[tuple[str, int]] = []
    haystack = text or ""
    lowered = haystack.lower()
    for term in terms:
        term = (term or "").strip()
        if not term:
            continue
        if term.isascii():
            count = lowered.count(term.lower())
        else:
            count = haystack.count(term)
        if count:
            hits.append((term, count))
    return hits


def _looks_like_token(term: str) -> bool:
    """化学基团/缩写按字面校验；中文知识点按考点级校验。"""
    term = (term or "").strip()
    if not term:
        return False
    if term[0] in "-+":
        return True
    return term.isascii() and len(term) <= 16


def _strip_citations_images(text: str) -> str:
    """字面 token 检查前去掉引用、图片标签、页码，避免误杀。"""
    text = _IMAGE_TAG_RE.sub("", text or "")
    text = re.sub(r"\[出处：[^\]]*\]", "", text)
    text = re.sub(r"[（(]\s*P\.?\s*\d+\s*[)）]", "", text)
    text = re.sub(r"第\s*\d+\s*页", "", text)
    return text


def _strip_topic_disclaimer(topic: str) -> str:
    """考点标题里带“不考具体命名”这类免责说明时，不把它当成命中禁用项。"""
    topic = re.sub(r"[（(][^）)]*(?:不考|不要求|无需|跳过|不涉及)[^）)]*[）)]", "", topic or "")
    topic = re.sub(r"(?:不考|不要求|无需|跳过|不涉及).*$", "", topic)
    return topic.strip()


def _topic_terms_for_task(text: str, task: str) -> list[str]:
    if task == "guide":
        return guide_topic_terms(text)
    if task == "extract":
        return extract_topic_terms(text)
    if task == "exam":
        return exam_topic_terms(text)
    return []


def _check_teacher_rules(report: ValidationReport, text: str, c: TaskConstraints,
                         stage: str, extra_bans: list[str] | None = None) -> None:
    """考点级复核：只考白名单 / 不考 / 必考 / 点名页码。

    正文顺带提及不判硬违规：判的是考点、标题、题目标签。
    """
    from core.quality.teacher_note import topic_matches
    topics = [t for t in (_strip_topic_disclaimer(x) for x in _topic_terms_for_task(text, c.task)) if t]
    if topics:
        report.metrics["topics"] = topics[:20]

    bans = list(c.ban_topics) + list(extra_bans or [])
    if c.only_topics and topics:
        bad = [t for t in topics
               if not any(topic_matches(t, allowed) for allowed in c.only_topics)]
        if bad:
            report.add("考点不在老师只考范围：" + "、".join(bad[:6]))
    if bans and topics:
        bad = [t for t in topics if any(topic_matches(t, b) for b in bans)]
        if bad:
            report.add("命中老师不考内容：" + "、".join(bad[:6]))
    # 老师说不考的内容不能只在“考点层”消失、正文还在讲。
    _body = _strip_citations_images(text)
    _body_hits = [b for b in c.ban_topics if len(re.sub(r"\s+", "", b)) >= 2
                  and b in _body]
    if _body_hits:
        report.add("正文仍出现老师不考内容：" + "、".join(_body_hits[:6]))

    if stage != "final":
        return
    if c.must_topics:
        missing = [m for m in c.must_topics
                   if not any(topic_matches(t, m) for t in topics)]
        if missing:
            report.add("老师必考内容缺失：" + "、".join(missing[:6]))
    if c.required_pages and c.task in ("guide", "extract"):
        cited = cited_pages(text)
        missing_pages = [p for p in c.required_pages if p not in cited]
        if missing_pages:
            report.add("老师点名页码未覆盖：" +
                       "、".join(f"第{p}页" for p in missing_pages[:8]))
    if c.weak_topics:
        missing = [w for w in c.weak_topics
                   if not any(topic_matches(t, w) for t in topics)
                   and re.sub(r"\s+", "", w) not in re.sub(r"\s+", "", text or "")]
        if missing:
            report.add("学生薄弱点未覆盖：" + "、".join(missing[:4]))


def _check_guide(report: ValidationReport, text: str, c: TaskConstraints,
                 source_text: str, cited: set[int], stage: str) -> None:
    if source_text:
        terms = guide_topic_terms(text)
        unsupported = unsupported_terms(terms, source_text)
        if unsupported:
            report.warn("疑似资料中没有的考点：" + "、".join(unsupported[:6]))
            report.metrics["ungrounded_terms"] = unsupported[:20]

    if stage == "chapter":
        return

    chapters = len(re.findall(r"(?m)^##\s+\S", text))
    report.metrics["chapters"] = chapters
    if chapters == 0:
        report.add("缺少 ## 级章节标题")
    if c.material_kind == "lecture" and "【考点" in text:
        report.warn("课堂讲义模式仍出现【考点】式应试标题")


def _check_extract(report: ValidationReport, text: str, c: TaskConstraints,
                   src: set[int], stage: str, source_text: str = "") -> None:
    extract_type = c.extract_type or ""
    # 考点/名词必须带出处（资料有页头、且不是"原题"提取时）
    if src and extract_type != "questions":
        blocks = re.split(r"(?m)^###\s*考点[:：]", text)[1:]
        missing = sum(1 for block in blocks if not _has_page_cite(block))
        if missing:
            report.add(f"有 {missing} 个考点缺少有效出处页码")
        if blocks:
            report.metrics["extract_points"] = len(blocks)
        elif extract_type == "nouns":
            # 名词提取：每个条目都应有 [出处：…]
            bullets = [ln for ln in text.splitlines() if ln.lstrip().startswith(("-", "*"))]
            if len(bullets) >= 3:
                cited_bullets = sum(1 for ln in bullets if _has_page_cite(ln))
                if cited_bullets == 0:
                    report.add("名词条目全部缺少出处页码")
                elif cited_bullets / len(bullets) < 0.5:
                    report.warn(f"只有 {cited_bullets}/{len(bullets)} 条名词带出处页码")
                report.metrics["extract_points"] = len(bullets)

        if "资料未标注页码" in text:
            report.add("资料有页头，但输出写了“资料未标注页码”")

    questions = len(_QUESTION_RE.findall(text))
    report.metrics["questions"] = questions
    if stage == "final" and extract_type == "questions":
        # 原题提取：资料里有题号就必须真的提出题来
        if questions == 0:
            source_questions = len(_QUESTION_RE.findall(source_text or ""))
            if source_questions:
                report.add(f"资料里有 {source_questions} 处题号，但输出没有识别到任何题目")
            else:
                report.warn("没有识别到题目（资料里也没有题号）")


def _check_exam(report: ValidationReport, text: str, c: TaskConstraints,
                stage: str) -> None:
    from core.generate.exam_builder import blueprint_from_sections, validate_paper

    blueprint = blueprint_from_sections(c.sections) if c.sections else None
    paper = validate_paper(text, blueprint, strict_counts=True,
                           require_answers=(c.answer_mode != "forbidden"))
    for issue in paper.issues:
        if issue.startswith("[error]"):
            report.add("试卷结构：" + issue[7:].strip())
        elif issue.startswith("[warn]"):
            report.warn("试卷结构：" + issue[6:].strip())
        else:
            report.warn("试卷结构：" + issue)
    report.metrics.update(paper.metrics)
    report.metrics["sections"] = paper.metrics.get("sections", {})

    # 新编试卷不得引用原资料页码（图片标签里的图注不算）
    body = _IMAGE_TAG_RE.sub("", text)
    pages = sorted(cited_pages(body))
    if pages:
        report.add("试卷里出现原资料页码：" + "、".join(f"第{p}页" for p in pages[:6]))

    if stage != "final":
        return

    # 只允许约束里的题型；额外标题（考试说明等）只提示，不误杀
    if c.sections:
        allowed = {s["name"] for s in c.sections}
        extra = []
        for title in _section_titles(text):
            if not any(name in title or title in name or _keyword(name) in title
                       for name in allowed):
                extra.append(title)
        if extra:
            type_words = ("选择题", "填空题", "判断题", "名词解释", "简答题", "计算题",
                          "推断题", "综合题", "证明题", "翻译题", "写作题", "阅读理解",
                          "完形填空", "编程题", "案例分析题", "论述题")
            extra_types = [t for t in extra if any(w in t for w in type_words)]
            if extra_types:
                report.add("出现未允许的题型：" + "、".join(extra_types[:4]))
            else:
                report.warn("试卷含额外标题（按说明处理）：" + "、".join(extra[:4]))

    if "【考点：" not in text and "【考点:" not in text:
        report.warn("题目缺少【考点：xxx】标注")

    # 答案自洽：题号重复/缺失（只看答案分区）
    _body, answers = _split_answer(text)
    if answers:
        nums = [int(n) for n in re.findall(r"(?m)^\s*(\d{1,3})\s*[.、．)）]", answers)]
        if nums:
            dups = sorted({n for n in nums if nums.count(n) > 1})
            # 答案按大题分节时，每节从 1 开始编号是合法的，不算重复
            sectioned = bool(re.search(r"(?m)^##\s+", answers))
            if dups and not sectioned:
                report.warn("答案题号重复：" + "、".join(str(n) for n in dups[:6]))
            report.metrics["answer_numbers"] = len(nums)


def _check_analysis(report: ValidationReport, text: str, stage: str) -> None:
    if not re.search(r"(?m)^##\s+\S", text):
        report.add("缺少 ## 级结构标题")
    if "```mermaid" in text and "```" not in text.split("```mermaid", 1)[1]:
        report.add("mermaid 代码块未闭合")


def _check_answer_mode(report: ValidationReport, text: str, c: TaskConstraints,
                       stage: str) -> None:
    if c.answer_mode == "forbidden":
        if (_ANSWER_SECTION_RE.search(text)
                or re.search(r"【答案】|【解析】", text)
                or re.search(r"(?m)^\s*(?:\*\*)?(?:答案|解析)[:：]", text)):
            report.add("要求只出题不给答案，但输出里出现了答案/解析")
        return
    if c.answer_mode != "required":
        return

    if c.task == "exam":
        # 只允许一个答案分区；模型偶尔会把“答案 + 第二套题”一起吐出来，
        # 旧逻辑只 split 第一个答案分区，会把后面的题目算成答案，误判通过。
        heads = re.findall(r"(?m)^#{1,3}\s*(?:答案|参考答案|答案与解析|答案及解析)", text or "")
        if len(heads) > 1:
            report.add(f"出现 {len(heads)} 个答案分区，试卷混入了第二套题")
        body, answers = _split_answer(text)
        if not answers:
            report.add("缺少「# 答案与解析」分区")
            return
        if re.search(r"(?m)^##\s*\S+?（\s*\d+\s*题[^）]*）", answers):
            report.add("答案分区后混入了题目（第二套题）")
        questions = len(_QUESTION_RE.findall(body))
        answered = len(_QUESTION_RE.findall(answers))
        report.metrics["answered"] = answered
        if questions and answered == 0:
            report.add("「答案与解析」分区没有按题号作答")

        # 可发布标准：每一题都必须有答案，不再允许 80% 覆盖。
        # 先按大题分节核对；答案没有分节时才退回总数核对。
        paper_secs = _exam_sections(body)
        ans_secs = _exam_sections(_strip_answer_heading(answers))
        if len(paper_secs) > 1 and len(ans_secs) > 1:
            missing_sections = []
            for title, content in paper_secs:
                qn = len(_QUESTION_RE.findall(content))
                if qn == 0:
                    continue
                key = _section_key(title)
                matched = next(((t, c) for t, c in ans_secs
                                if key and (key in _section_key(t) or _section_key(t) in key)), None)
                if matched is None:
                    missing_sections.append(title)
                    continue
                an = len(_QUESTION_RE.findall(matched[1]))
                if an < qn:
                    report.add(f"「{title}」答案不足：{an}/{qn} 题")
            if missing_sections:
                report.add("答案缺少大题：" + "、".join(missing_sections[:4]))
        if questions and answered < questions:
            report.add(f"答案不完整：{answered}/{questions} 题；每道题都必须有答案")
        _check_choice_letters(report, body, answers)
        # 题号后必须真的有答案内容，不能只写 "1."
        empty_lines = [ln for ln in answers.splitlines()
                       if re.match(r"^\s*\d{1,3}\s*[.、．)）]\s*$", ln)]
        if empty_lines:
            report.add(f"答案题号后为空：{len(empty_lines)} 处")
        if len(re.sub(r"\s+", "", answers)) < 10:
            report.add("「答案与解析」分区内容为空")
    elif c.task == "extract" and stage == "final" and c.extract_type == "questions":
        questions = len(_QUESTION_RE.findall(text))
        answers = len(_ANSWER_MARK_RE.findall(text))
        report.metrics["answered"] = answers
        if questions and answers == 0:
            report.add("要求带答案，但输出里没有【答案】/答案：")
        elif questions and answers / questions < 0.5:
            report.warn(f"答案只覆盖 {answers}/{questions} 题")


# --------------------------------------------------------------------------- #
# 工具
# --------------------------------------------------------------------------- #
def _section_titles(text: str) -> list[str]:
    body, _ = _split_answer(text)
    return [re.sub(r"\s+", "", m.group(1)).strip()
            for m in re.finditer(r"(?m)^##+\s*(.+)$", body)]


def _numbered_blocks(content: str) -> list[tuple[int, str]]:
    matches = list(re.finditer(r"(?m)^\s*(\d{1,2})\s*[.、．)）]\s*", content or ""))
    out: list[tuple[int, str]] = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        out.append((int(m.group(1)), content[m.end():end]))
    return out


def _option_letters(block: str) -> set[str]:
    found = set(re.findall(r"(?m)^\s*([A-DＡ-Ｄ])\s*[.、．)）]", block or ""))
    if len(found) < 2:
        found |= set(re.findall(r"(?:^|\s)([A-DＡ-Ｄ])\s*[.、．)）]", block or ""))
    return {chr(ord(x) - 0xFEE0) if ord(x) >= 0xFF21 else x for x in found}


def _check_choice_letters(report, body: str, answers: str) -> None:
    """选择题答案必须是题干里真实存在的选项字母；不做“答案可能对”的模糊判断。"""
    paper_secs = _exam_sections(body)
    ans_secs = _exam_sections(_strip_answer_heading(answers))
    if not paper_secs:
        paper_secs = [("", body)]
    checked = 0
    for title, content in paper_secs:
        key = _section_key(title)
        ans_content = ""
        if len(ans_secs) > 1:
            matched = next(((t, c) for t, c in ans_secs
                            if key and (key in _section_key(t) or _section_key(t) in key)), None)
            if not matched:
                continue
            ans_content = matched[1]
        else:
            ans_content = ans_secs[0][1] if ans_secs else _strip_answer_heading(answers)
        ans_map = {n: b for n, b in _numbered_blocks(ans_content)}
        for num, block in _numbered_blocks(content):
            opts = _option_letters(block)
            if len(opts) < 2:
                continue
            checked += 1
            ab = ans_map.get(num, "")
            m = re.search(r"[A-Za-zＡ-Ｚａ-ｚ]", ab[:80])
            if not m:
                report.add(f"选择题第 {num} 题的答案不是选项字母")
                continue
            letter = m.group(0).upper()
            if ord(letter) >= 0xFF21:
                letter = chr(ord(letter) - 0xFEE0)
            if letter not in opts:
                report.add(f"选择题第 {num} 题答案 {letter} 不在选项 {''.join(sorted(opts))} 中")
    report.metrics["choice_checked"] = checked


def _strip_answer_heading(answers: str) -> str:
    return re.sub(r"(?m)^#{1,3}\s*(?:答案|参考答案|答案与解析|答案及解析)[^\n]*\n?", "", answers or "", count=1)


def _exam_sections(text: str) -> list[tuple[str, str]]:
    parts = re.split(r"^#{1,3}\s*(.+)$", text or "", flags=re.MULTILINE)
    out: list[tuple[str, str]] = []
    for i in range(1, len(parts), 2):
        title = parts[i].strip()
        if not title or re.match(r"^(?:答案|参考答案|答案与解析|答案及解析)", title):
            continue
        out.append((title, parts[i + 1] if i + 1 < len(parts) else ""))
    return out


def _section_key(title: str) -> str:
    return re.sub(r"[\s一二三四五六七八九十、，,。.：:（）()0-9]", "", title or "")


def _split_answer(text: str) -> tuple[str, str]:
    """把试卷拆成（题目部分, 答案部分）。标题可带“（详解）”等后缀。"""
    m = re.search(r"(?m)^#{1,3}\s*(?:答案|参考答案|答案与解析|答案及解析)[^\n]*$", text or "")
    if not m:
        return text or "", ""
    return text[:m.start()], text[m.start():]


def _keyword(name: str) -> str:
    return name.strip("一二三四五六七八九十、 ").strip()


def _has_page_cite(text: str) -> bool:
    return bool(_PAGE_CITE_RE.search(text) or _P_CITE_RE.search(text))


# --------------------------------------------------------------------------- #
# 资料依据（软信号）
# --------------------------------------------------------------------------- #
def guide_topic_terms(text: str) -> list[str]:
    terms = _KEYWORD_RE.findall(text)
    for m in re.finditer(r"(?m)^#{3,4}\s+(.+)$", text):
        heading = re.sub(r"^\d+(?:\.\d+)*\s*", "", m.group(1)).strip()
        heading = heading.strip(".:： ")
        if heading:
            terms.append(heading)
    return _dedupe_terms(terms)


def extract_topic_terms(text: str) -> list[str]:
    return _dedupe_terms(_EXTRACT_POINT_RE.findall(text))


def exam_topic_terms(text: str) -> list[str]:
    return _dedupe_terms(_EXAM_POINT_RE.findall(text))


def _dedupe_terms(terms: list[str]) -> list[str]:
    out: list[str] = []
    seen = set()
    for term in terms:
        cleaned = _normalize_term(term)
        if not cleaned or cleaned in GENERIC_HEADINGS or cleaned in seen:
            continue
        seen.add(cleaned)
        out.append(cleaned)
    return out


def _normalize_term(term: str) -> str:
    term = _MATH_RE.sub("", term or "")
    term = re.sub(r"^[\d.\s、:：\-—•·]+", "", term)
    term = re.sub(r"[（）()【】\[\]《》\"'“”‘’]", "", term)
    return term.strip()


def _plain(text: str) -> str:
    text = _MATH_RE.sub("", text or "")
    return re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", text)


def unsupported_terms(terms: list[str], source_text: str,
                      *, top: int = 12) -> list[str]:
    """哪些术语在资料里找不到依据（最长公共子串 / 3-gram 覆盖率都过低）。"""
    index = _SourceIndex(source_text)
    if not index.text:
        return []
    out: list[str] = []
    for term in terms:
        if _term_length(term) < 2:
            continue
        if not index.supported(term):
            out.append(term)
        if len(out) >= top:
            break
    return out


class _SourceIndex:
    """资料文本索引：够小就建 4-gram 集合，超大文档退化为子串查找。"""

    MAX_INDEX_CHARS = 400_000

    def __init__(self, text: str):
        self.text = _plain(text)[: self.MAX_INDEX_CHARS]
        self.g4 = None
        if 4 <= len(self.text) <= self.MAX_INDEX_CHARS:
            self.g4 = {self.text[i:i + 4] for i in range(len(self.text) - 3)}

    def supported(self, term: str) -> bool:
        normalized = _plain(term)
        if len(normalized) < 2:
            return True
        if normalized in self.text:
            return True
        if len(normalized) < 4:
            return False
        if self.g4 is not None:
            grams4 = {normalized[i:i + 4] for i in range(len(normalized) - 3)}
            if grams4 & self.g4:
                return True
        else:
            for i in range(len(normalized) - 3):
                if normalized[i:i + 4] in self.text:
                    return True
        grams3 = [normalized[i:i + 3] for i in range(len(normalized) - 2)]
        hit = sum(1 for gram in grams3 if gram in self.text)
        return hit / len(grams3) >= 0.5


def _term_length(term: str) -> int:
    return len(_plain(term))

"""智能组卷：先定蓝图（题型×数量×分值），再让 AI 填空，最后自动验卷。

旧实现是"给段文字，让 AI 自己出几套题"，难度、分值、覆盖面全靠运气。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

DEFAULT_SECTIONS = [
    ("一、选择题", 10, 3.0),
    ("二、填空题", 5, 4.0),
    ("三、计算题", 3, 10.0),
    ("四、综合题", 1, 20.0),
]


@dataclass
class Section:
    name: str
    count: int
    each: float

    @property
    def subtotal(self) -> float:
        return round(self.count * self.each, 1)


@dataclass
class Blueprint:
    sections: list[Section]
    lang: str = "中文"

    @property
    def total(self) -> float:
        return round(sum(s.subtotal for s in self.sections), 1)

    def render(self) -> str:
        lines = [f"- {s.name}：{s.count} 题 × {s.each:g} 分 = {s.subtotal:g} 分"
                 for s in self.sections]
        return "\n".join(lines) + f"\n- 合计：{self.total:g} 分"


def blueprint_from_sections(sections, lang: str = "中文") -> Blueprint | None:
    """把 UI 自定义的题型结构变成校验用蓝图（生成与校验共用同一份，避免两套题数）。"""
    cleaned: list[Section] = []
    for item in sections or []:
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
        if name:
            cleaned.append(Section(name, count, points))
    return Blueprint(cleaned, lang) if cleaned else None


def build_blueprint(difficulty: int = 3, target_score: int = 80, lang: str = "中文") -> Blueprint:
    """按目标分微调结构：目标越高，计算/综合占比越大。"""
    if target_score >= 90:
        sections = [
            Section("一、选择题", 8, 3.0),
            Section("二、填空题", 4, 4.0),
            Section("三、计算题", 4, 10.0),
            Section("四、综合题", 1, 24.0),
        ]
    elif target_score <= 65:
        sections = [
            Section("一、选择题", 12, 2.5),
            Section("二、填空题", 6, 5.0),
            Section("三、简答题", 2, 15.0),
            Section("四、计算题", 2, 10.0),
        ]
    else:
        sections = [Section(name, count, each) for name, count, each in DEFAULT_SECTIONS]
    return Blueprint(sections, lang)


@dataclass
class PaperReport:
    ok: bool = True
    issues: list[str] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)

    def add(self, level: str, msg: str) -> None:
        self.issues.append(f"[{level}] {msg}")
        if level == "error":
            self.ok = False


# --------------------------------------------------------------------------- #
# 解析
# --------------------------------------------------------------------------- #
def _split_sections(markdown: str) -> dict[str, str]:
    """按大题标题切段（只看答案之前的部分）。"""
    body = re.split(r"(?m)^#{1,3}\s*(?:答案|参考答案|答案与解析|答案及解析)", markdown)[0]
    parts = re.split(r"^#{1,3}\s*(.+)$", body, flags=re.MULTILINE)
    sections: dict[str, str] = {}
    for i in range(1, len(parts), 2):
        sections[parts[i].strip()] = parts[i + 1] if i + 1 < len(parts) else ""
    return sections


QUESTION_RE = re.compile(r"^\s*(?:\*\*|__)?\s*(\d{1,2})\s*[.、．)）]\s*(?:\*\*)?\s*", re.MULTILINE)


def _count_questions(content: str) -> int:
    """兼容 `1.` / `**1.**` / `1、` / `1）` 等常见题号写法。"""
    return len(QUESTION_RE.findall(content))


def _stem_of(block: str) -> str:
    first = block.strip().splitlines()[0]
    first = re.sub(r"（\s*）|\(\s*\)", "", first)
    return re.sub(r"\s+", "", first)[:80]


def _stems(markdown: str) -> list[str]:
    body = re.split(r"(?m)^#{1,3}\s*(?:答案|参考答案|答案与解析|答案及解析)", markdown)[0]
    stems = []
    for block in QUESTION_RE.split(body):
        block = block.strip()
        stem = _stem_of(block) if block else ""
        if len(stem) >= 12:
            stems.append(stem)
    return stems


def _ngrams(text: str, n: int = 5) -> set[str]:
    return {text[i:i + n] for i in range(max(0, len(text) - n))}


def _check_syntax(markdown: str) -> list[str]:
    issues = []
    if markdown.count("$$") % 2:
        issues.append("$$ 未闭合")
    rest = re.sub(r"\$\$.*?\$\$", "", markdown, flags=re.DOTALL)
    if rest.count("$") % 2:
        issues.append("行内 $ 未闭合")
    if markdown.count("```") % 2:
        issues.append("``` 未闭合")
    leftovers = re.findall(r"@@\w+@@", markdown)
    if leftovers:
        issues.append(f"占位符残留 {len(leftovers)}")
    return issues


# --------------------------------------------------------------------------- #
# 验卷
# --------------------------------------------------------------------------- #
def validate_paper(markdown: str, blueprint: Blueprint | None = None,
                   strict_counts: bool = False, require_answers: bool = True) -> PaperReport:
    """验卷。

    strict_counts=True 时，题数与蓝图不一致按 error 处理（用户明确设定了结构，
    不能只是"提示一下"就交付）。默认仍按 warn，保持旧调用行为。
    require_answers=False 用于“只要题目、不要答案”的任务。
    """
    report = PaperReport()
    markdown = markdown or ""

    for issue in _check_syntax(markdown):
        report.add("error", issue)

    if require_answers and not re.search(
            r"(?m)^#{1,3}\s*(?:答案|参考答案|答案与解析|答案及解析)", markdown):
        report.add("error", "缺少「答案与解析」分区")

    sections = _split_sections(markdown)
    found_total = 0.0
    detail: dict[str, dict] = {}

    if blueprint:
        for sec in blueprint.sections:
            keyword = sec.name.strip("一二三四五六、")
            matched = next((c for title, c in sections.items() if keyword and keyword in title), None)
            if matched is None:
                report.add("error", f"缺少大题：{sec.name}")
                continue
            count = _count_questions(matched)
            found_total += count * sec.each
            detail[sec.name] = {"expected": sec.count, "found": count}
            if count == 0:
                report.add("error", f"{sec.name} 未识别到题号")
            elif count != sec.count:
                report.add("error" if strict_counts else "warn",
                           f"{sec.name} 题数 {count} ≠ 计划 {sec.count}")
        if abs(found_total - blueprint.total) > 0.5:
            report.add("error", f"实际分值合计 {found_total:g} ≠ 计划 {blueprint.total:g}")
    else:
        found = re.findall(r"共\s*(\d+)\s*分", markdown)
        found_total = float(sum(int(x) for x in found[:4])) if found else 0.0

    # 重复题检测：只看题干首行，阈值 0.75
    stems = _stems(markdown)
    grams = [_ngrams(s) for s in stems]
    dup_pairs = 0
    for i in range(len(grams)):
        for j in range(i + 1, len(grams)):
            if not grams[i] or not grams[j]:
                continue
            if len(grams[i] & grams[j]) / len(grams[i] | grams[j]) > 0.75:
                dup_pairs += 1
    if dup_pairs:
        report.add("warn", f"疑似重复题目 {dup_pairs} 对")

    point_tags = len(re.findall(r"【考点[:：]", markdown))
    if stems and point_tags < len(stems) * 0.6:
        report.add("warn", f"考点标注不足 {point_tags}/{len(stems)}")

    images = len(re.findall(r"\[\[\[IMAGE:", markdown))
    report.metrics = {
        "questions": len(stems),
        "score_total": found_total,
        "sections": detail,
        "point_tags": point_tags,
        "duplicate_pairs": dup_pairs,
        "images": images,
        "chars": len(re.sub(r"\s+", "", markdown)),
    }
    return report

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
    body = markdown.split("# 答案与解析")[0]
    parts = re.split(r"^#{1,3}\s*(.+)$", body, flags=re.MULTILINE)
    sections: dict[str, str] = {}
    for i in range(1, len(parts), 2):
        sections[parts[i].strip()] = parts[i + 1] if i + 1 < len(parts) else ""
    return sections


def _count_questions(content: str) -> int:
    return len(re.findall(r"^\s*\d+[.、]", content, flags=re.MULTILINE))


def _stem_of(block: str) -> str:
    first = block.strip().splitlines()[0]
    first = re.sub(r"（\s*）|\(\s*\)", "", first)
    return re.sub(r"\s+", "", first)[:80]


def _stems(markdown: str) -> list[str]:
    body = markdown.split("# 答案与解析")[0]
    stems = []
    for block in re.split(r"(?=^\s*\d+[.、])", body, flags=re.MULTILINE):
        block = block.strip()
        if not block or not re.match(r"^\d+[.、]", block):
            continue
        stem = _stem_of(block)
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
def validate_paper(markdown: str, blueprint: Blueprint | None = None) -> PaperReport:
    report = PaperReport()
    markdown = markdown or ""

    for issue in _check_syntax(markdown):
        report.add("error", issue)

    if "# 答案与解析" not in markdown:
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
                report.add("warn", f"{sec.name} 题数 {count} ≠ 计划 {sec.count}")
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

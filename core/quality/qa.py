"""生成结果的自动校验（不依赖网络）。

目标：把"这次生成到底行不行"从主观感觉变成可打印的指标。
任何一项不通过都写进 issues，供上层决定是否重写该章。
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

# 精简/全量 的单章字数区间（去空白字符计）
CHAR_RANGE = {
    "key": (600, 2200),
    "full": (1000, 3600),
}

AI_META_PATTERNS = [
    r"作为(一个)?AI", r"以下是", r"希望对你有帮助", r"如需", r"抱歉",
    r"我无法", r"注意：以上", r"^好的[，,]", r"当然[，,]可以",
]


@dataclass
class QAReport:
    ok: bool = True
    issues: list[str] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)

    def add(self, level: str, message: str) -> None:
        self.issues.append(f"[{level}] {message}")
        if level in ("error", "fatal"):
            self.ok = False

    def merge(self, other: "QAReport", prefix: str = "") -> None:
        for issue in other.issues:
            self.issues.append(f"{prefix}{issue}" if prefix else issue)
        self.metrics.update(other.metrics)
        self.ok = self.ok and other.ok


def _strip_image_tags(text: str) -> str:
    return re.sub(r"\[\[\[IMAGE:.*?\]\]\]", "", text)


def _normalized_paragraphs(text: str) -> list[str]:
    parts = re.split(r"\n\s*\n", _strip_image_tags(text))
    return [re.sub(r"\s+", "", p) for p in parts if len(re.sub(r"\s+", "", p)) >= 12]


def check_markdown(
    markdown: str,
    *,
    mode: str = "full",
    lang: str = "中文",
    expected_images: list[str] | None = None,
    min_keywords: int = 3,
    require_heading: bool = True,
) -> QAReport:
    report = QAReport()
    text = markdown or ""
    plain = _strip_image_tags(text)

    # 1. 公式闭合
    display_pairs = text.count("$$")
    if display_pairs % 2:
        report.add("error", f"$$ 未闭合（出现 {display_pairs} 次）")
    rest = re.sub(r"\$\$.*?\$\$", "", text, flags=re.DOTALL)
    inline = rest.count("$")
    if inline % 2:
        report.add("error", f"行内 $ 未闭合（出现 {inline} 次）")

    # 2. 占位符残留
    leftovers = re.findall(r"@@\w+@@", text)
    if leftovers:
        report.add("error", f"占位符残留 {len(leftovers)} 个：{leftovers[:3]}")

    # 3. 代码块闭合
    fences = text.count("```")
    if fences % 2:
        report.add("error", f"``` 代码块未闭合（{fences} 个）")

    # 4. 图片标记是否保住
    expected_images = expected_images or []
    missing = [tag for tag in expected_images if tag not in text]
    if missing:
        report.add("error", f"图片标记丢失 {len(missing)} 个")

    # 5. 字数
    chars = len(re.sub(r"\s+", "", plain))
    lo, hi = CHAR_RANGE.get(mode, CHAR_RANGE["full"])
    if chars < lo:
        report.add("warn", f"篇幅偏短 {chars} < {lo}")
    elif chars > hi:
        report.add("warn", f"篇幅偏长 {chars} > {hi}")

    # 6. 名词高亮
    keywords = re.findall(r"\[\[(?!\[)[^\]]+\]\]", plain)
    if len(keywords) < min_keywords:
        report.add("warn", f"名词高亮偏少 {len(keywords)} < {min_keywords}")

    # 7. 章节标题
    if require_heading and not re.search(r"^##\s+\S", text, flags=re.MULTILINE):
        report.add("error", "缺少 ## 级标题，目录会为空")

    # 8. 段落重复率
    paras = _normalized_paragraphs(text)
    if paras:
        counter = Counter(paras)
        dup = sum(c - 1 for c in counter.values() if c > 1)
        ratio = dup / len(paras)
        if ratio > 0.15:
            report.add("warn", f"段落重复率 {ratio:.0%}")

    # 9. AI 废话
    for pattern in AI_META_PATTERNS:
        if re.search(pattern, plain):
            report.add("warn", f"疑似 AI 废话：{pattern}")
            break

    # 10. 截断迹象（末尾突然断句）
    stripped = text.rstrip()
    if stripped and stripped[-1] not in "。！？!?：:】)）\"'`$":
        report.add("warn", "结尾疑似截断")

    report.metrics = {
        "chars": chars,
        "formulas": display_pairs // 2 + inline // 2,
        "keywords": len(keywords),
        "images": len(re.findall(r"\[\[\[IMAGE:", text)),
        "chapters": len(re.findall(r"^##\s+\S", text, flags=re.MULTILINE)),
        "paragraphs": len(paras),
    }
    return report


@dataclass
class ChaptersReport:
    ok: bool = True
    reports: list[QAReport] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)

    def summary(self) -> str:
        failed = [i for i, r in enumerate(self.reports) if not r.ok]
        return (f"章节 {len(self.reports)} 章 / 不通过 {len(failed)} 章"
                f" | 总字数 {self.metrics.get('chars', 0)}")


def check_chapters(
    chapters: list[tuple[str, str]],
    *,
    mode: str = "full",
    lang: str = "中文",
) -> ChaptersReport:
    """chapters: [(标题, markdown), ...]"""
    out = ChaptersReport()
    total_chars = 0
    for idx, (title, md) in enumerate(chapters):
        report = check_markdown(md, mode=mode, lang=lang, require_heading=False)
        out.reports.append(report)
        out.metrics.setdefault("chapters", []).append(
            {"title": title, **report.metrics, "ok": report.ok}
        )
        total_chars += report.metrics.get("chars", 0)
        if not report.ok:
            out.ok = False
            out.issues.append(f"{title}: " + "; ".join(report.issues))
    out.metrics["chars"] = total_chars
    return out

"""内容体检：乱码、未渲染公式、复杂公式、空段/重复段。

这是确定性门禁；不替代逐页覆盖审计和学科复核。
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from tfv2.domain.lecture import LectureSpec
from tfv2.domain.page import PageLedger

# 替换符、常见 mojibake、私用区、控制字符
_MOJIBAKE = re.compile(r"(\ufffd|锟斤拷|烫烫|屯屯|Ã.|Â.|â€|ï¿½)")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ue000-\uf8ff]")
# 文本里不应残留的 TeX 命令（公式块除外，公式块由渲染器处理）
_RAW_TEX = re.compile(r"\\(frac|sqrt|text|begin|ce|xrightarrow|overset|underset|substack|displaystyle)\b")
_FORMULA_BLOCK = re.compile(r"\$\$(.+?)\$\$|\$(.+?)\$", re.S)


class ContentIssue(BaseModel):
    code: str
    message: str
    severity: Literal["hard", "warn"] = "hard"
    location: str = ""


class ContentReport(BaseModel):
    issues: list[ContentIssue] = Field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(x.severity == "hard" for x in self.issues)

    def summary(self) -> str:
        hard = sum(1 for x in self.issues if x.severity == "hard")
        warn = len(self.issues) - hard
        return f"内容体检通过（{warn} 条提醒）" if self.passed else f"内容体检失败：{hard} 条硬伤，{warn} 条提醒"


def _add(issues: list[ContentIssue], code: str, message: str, *, severity: Literal["hard", "warn"] = "hard", location: str = "") -> None:
    issues.append(ContentIssue(code=code, message=message, severity=severity, location=location))


def _check_text(text: str, where: str, issues: list[ContentIssue]) -> None:
    if _MOJIBAKE.search(text):
        _add(issues, "text.mojibake", "出现乱码/替换符/mojibake", location=where)
    if _CONTROL.search(text):
        _add(issues, "text.control", "出现控制字符/私用区字符", location=where)
    # 公式块之外出现 TeX 命令，说明没被标记为公式或解析残留
    stripped = _FORMULA_BLOCK.sub("", text)
    if _RAW_TEX.search(stripped):
        _add(issues, "text.raw_tex", "公式块之外出现 TeX 命令", location=where)


def _check_formula(formula: str, where: str, issues: list[ContentIssue]) -> None:
    if len(formula) > 220:
        _add(issues, "formula.too_long", f"公式过长（{len(formula)} 字符），建议拆成多步", severity="warn", location=where)
    if formula.count("\\frac") >= 3 or formula.count("\\begin{") > 0:
        _add(issues, "formula.complex", "公式嵌套/矩阵过多，零基础阅读成本高", severity="warn", location=where)
    if formula.count("\\sqrt") >= 3:
        _add(issues, "formula.complex_sqrt", "根式过多，建议分步", severity="warn", location=where)


def scan_lecture(spec: LectureSpec) -> ContentReport:
    issues: list[ContentIssue] = []
    seen: dict[str, str] = {}
    for sec in spec.sections:
        if not sec.blocks:
            _add(issues, "section.empty", f"小节「{sec.title}」没有内容", location=sec.title)
        if not sec.source_refs:
            _add(issues, "section.no_source", f"小节「{sec.title}」没有出处", location=sec.title)
        for block in sec.blocks:
            text = (block.text or "").strip()
            if block.kind.value != "figure" and len(text) < 8:
                _add(issues, "block.empty", f"小节「{sec.title}」有空白/过短 block", location=block.id)
            _check_text(text, f"{sec.title}/{block.id}", issues)
            for m in _FORMULA_BLOCK.finditer(text):
                _check_formula(m.group(1) or m.group(2) or "", f"{sec.title}/{block.id}", issues)
            key = text[:80]
            if len(text) >= 40 and key in seen and seen[key] != block.id:
                _add(issues, "block.duplicate", f"小节「{sec.title}」出现重复段落", severity="warn", location=block.id)
            if len(text) >= 40:
                seen[key] = block.id
    return ContentReport(issues=issues)


def scan_pages(ledger: PageLedger) -> ContentReport:
    issues: list[ContentIssue] = []
    for page in ledger.pages:
        _check_text(page.text or "", f"第 {page.page_no} 页", issues)
    return ContentReport(issues=issues)


def _pdf_text_for_scan(text: str) -> str:
    """去掉 PDF 文本层里的 KaTeX 字形控制符，再做乱码/TeX 检查。

    KaTeX 的部分数学符号在 PDF 里以私用区字形（Co）或零宽控制符（Cf）
    写入文本层，视觉由字体渲染正常，不是乱码。直接拿原始文本层做
    PUA 检查会误报；这里只对 PDF 扫描去掉 Cf/Co，保留可见字符和
    真正的控制字符（Cc）交给 _check_text。
    """
    return "".join(
        ch for ch in text
        if unicodedata.category(ch) not in ("Cf", "Co")
    )


def scan_pdf_text(pdf_path: str | Path) -> ContentReport:
    """检查最终 PDF 里是否还有未渲染 TeX/乱码。"""
    import pymupdf

    issues: list[ContentIssue] = []
    doc = pymupdf.open(str(pdf_path))
    for page in doc:
        raw = page.get_text("text")
        text = _pdf_text_for_scan(raw)
        _check_text(text, f"PDF 第 {page.number + 1} 页", issues)
        if "$$" in text or "\\frac" in text or "\\text" in text:
            _add(issues, "pdf.raw_tex", f"PDF 第 {page.number + 1} 页仍有未渲染公式", location=f"page {page.number + 1}")
    doc.close()
    return ContentReport(issues=issues)


def report_markdown(reports: dict[str, ContentReport]) -> str:
    lines = ["# 内容体检报告", ""]
    for name, r in reports.items():
        lines += [f"## {name}", "", f"- 结果：{r.summary()}"]
        for x in r.issues:
            lines.append(f"- `{x.code}`（{x.severity}）{x.message} {x.location}")
        lines.append("")
    return "\n".join(lines)

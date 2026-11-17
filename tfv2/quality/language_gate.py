"""语言四角色检查：源语言术语保留、生成语言、乱码。

不是翻译质量评分；只查“英文资料是否被强行全译成中文、术语是否丢失”。
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Literal

from pydantic import BaseModel, Field

from tfv2.domain.lecture import LanguagePolicy, LectureSpec
from tfv2.domain.page import PageLedger

_TOKEN = re.compile(r"\b[A-Za-z][A-Za-z\-]{2,}\b")
_STOP = {"the", "and", "for", "with", "that", "this", "from", "into", "when", "then", "than", "are", "was", "were", "has", "have", "not", "can", "will", "may", "its", "their", "which", "such", "using", "used"}


class LanguageIssue(BaseModel):
    code: str
    message: str
    severity: Literal["hard", "warn"] = "warn"


class LanguageReport(BaseModel):
    source_lang: str | None = None
    gen_lang: str = "中文"
    ui_lang: str = "zh"
    preserved_terms: list[str] = Field(default_factory=list)
    missing_terms: list[str] = Field(default_factory=list)
    issues: list[LanguageIssue] = Field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(x.severity == "hard" for x in self.issues)


def _terms(text: str) -> list[str]:
    counts = Counter(x.lower() for x in _TOKEN.findall(text or "") if x.lower() not in _STOP)
    return [w for w, _ in counts.most_common(40) if len(w) >= 3]


def check_language(spec: LectureSpec, ledger: PageLedger | None = None) -> LanguageReport:
    policy: LanguagePolicy = spec.language_policy
    lecture = "\n".join(b.text for s in spec.sections for b in s.blocks if b.kind.value != "figure")
    source = "\n".join(p.text for p in ledger.pages) if ledger is not None else ""
    report = LanguageReport(source_lang=policy.source_lang, gen_lang=policy.gen_lang, ui_lang=policy.ui_lang)
    if not lecture.strip():
        report.issues.append(LanguageIssue(code="language.empty", message="讲义没有正文", severity="hard"))
        return report
    if policy.source_lang and policy.source_lang.lower().startswith("en") and policy.gen_lang.startswith("中"):
        source_terms = _terms(source)
        lecture_lower = lecture.lower()
        for term in source_terms:
            if term in lecture_lower:
                report.preserved_terms.append(term)
            else:
                report.missing_terms.append(term)
        if source_terms and len(report.preserved_terms) / len(source_terms) < 0.5:
            report.issues.append(LanguageIssue(
                code="language.terms_lost",
                message=f"英文术语保留率过低：{len(report.preserved_terms)}/{len(source_terms)}",
                severity="hard",
            ))
        elif report.missing_terms:
            report.issues.append(LanguageIssue(
                code="language.terms_missing",
                message="部分英文术语未在讲义中出现：" + ", ".join(report.missing_terms[:8]),
                severity="warn",
            ))
    if str(policy.gen_lang).lower().startswith("english"):
        cjk = len(re.findall(r"[\u4e00-\u9fff]", lecture))
        latin = len(re.findall(r"[A-Za-z]", lecture))
        if cjk + latin and cjk / (cjk + latin) > 0.5:
            report.issues.append(LanguageIssue(
                code="language.gen_not_english",
                message=f"生成语言是 English，但正文中文占比 {cjk/(cjk+latin):.0%}；讲解应翻译成英文，原文引用保留",
                severity="hard",
            ))
    if str(policy.gen_lang).startswith("繁"):
        simplified = "这个们学习图页电时间问题计"
        hits = [c for c in simplified if c in lecture]
        if hits:
            report.issues.append(LanguageIssue(
                code="language.hant_simplified",
                message="繁體生成正文含常用简体字：" + "、".join(hits[:8]) + "（原文引用可能例外）",
                severity="warn",
            ))
    # 常见 mojibake / 替换符
    if re.search(r"(\ufffd|锟斤拷|Ã.|Â.)", lecture):
        report.issues.append(LanguageIssue(code="language.mojibake", message="讲义出现乱码/替换符", severity="hard"))
    return report


def report_markdown(report: LanguageReport) -> str:
    lines = ["# 语言检查报告", "", f"- 源语言：{report.source_lang or '未标注'}",
             f"- 生成语言：{report.gen_lang}", f"- 界面语言：{report.ui_lang}",
             f"- 术语保留：{len(report.preserved_terms)} 个",
             f"- 术语缺失：{len(report.missing_terms)} 个", ""]
    if report.missing_terms:
        lines += ["## 未出现的英文术语", "", ", ".join(report.missing_terms), ""]
    for x in report.issues:
        lines.append(f"- `{x.code}`（{x.severity}）{x.message}")
    return "\n".join(lines)

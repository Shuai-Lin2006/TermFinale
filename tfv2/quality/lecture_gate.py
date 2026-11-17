"""v2 讲义硬门禁。

只做确定性检查；语义质量（讲得好不好）留给人工 rubric。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from tfv2.domain.lecture import BlockKind, LectureSpec

INLINE_PAGE_RE = re.compile(r"\bP\.\s*\d+\b")
FULL_COVERAGE_LIMIT = 150


@dataclass(frozen=True)
class GateIssue:
    code: str
    message: str
    hard: bool = True


@dataclass
class LectureGateReport:
    passed: bool
    issues: list[GateIssue] = field(default_factory=list)

    @property
    def hard_issues(self) -> list[GateIssue]:
        return [x for x in self.issues if x.hard]

    def summary(self) -> str:
        if self.passed:
            return "讲义门禁通过"
        return "；".join(f"[{x.code}] {x.message}" for x in self.hard_issues[:8])


def validate_lecture(spec: LectureSpec) -> LectureGateReport:
    issues: list[GateIssue] = []

    def add(code: str, msg: str, hard: bool = True) -> None:
        issues.append(GateIssue(code=code, message=msg, hard=hard))

    # 标头
    if not spec.header.title.strip():
        add("header.title", "缺少讲义标题")
    if not spec.header.course.strip():
        add("header.course", "缺少课程名")

    # 目录
    if not spec.toc:
        add("toc.empty", "缺少教材式目录")
    anchors = [x.anchor for x in spec.toc]
    if len(anchors) != len(set(anchors)):
        add("toc.anchor", "目录锚点重复")
    toc_pages = [x.page_no for x in spec.toc]
    if toc_pages != sorted(toc_pages):
        add("toc.order", "目录页码不是递增顺序", hard=False)

    # 摘要
    if not spec.summary.overview.strip():
        add("summary.overview", "缺少全篇摘要")
    if not spec.summary.knowledge_map:
        add("summary.map", "全篇摘要缺少知识地图", hard=False)

    # 正文
    if not spec.sections:
        add("sections.empty", "讲义没有正文小节")
    titles = [s.title.strip() for s in spec.sections]
    if len(titles) != len(set(titles)):
        add("sections.duplicate", "存在重复小节标题")
    for sec in spec.sections:
        if not sec.title.strip():
            add("section.title", "存在空标题小节")
            continue
        if not sec.blocks:
            add("section.empty", f"小节「{sec.title}」没有正文")
        if not sec.source_refs:
            add("section.source", f"小节「{sec.title}」缺少资料出处")
        for src in sec.source_refs:
            if src.page_end is not None and src.page_end > spec.page_count:
                add("source.range", f"小节「{sec.title}」出处页超出资料总页数")
            elif src.page_start > spec.page_count:
                add("source.range", f"小节「{sec.title}」出处页超出资料总页数")
        if not getattr(sec, "objectives", None):
            add("section.objectives", f"小节「{sec.title}」缺少学习目标", hard=False)
        if not getattr(sec, "key_terms", None):
            add("section.key_terms", f"小节「{sec.title}」缺少关键术语", hard=False)
        if not getattr(sec, "self_test", None):
            add("section.self_test", f"小节「{sec.title}」缺少自测", hard=False)
        for block in sec.blocks:
            if block.kind == BlockKind.FIGURE:
                if block.figure is None:
                    add("figure.missing", f"小节「{sec.title}」图片块没有 FigureRef")
                else:
                    if not block.figure.caption.strip():
                        add("figure.caption", f"小节「{sec.title}」图片缺少图注")
                    if block.figure.after_block_id != block.id:
                        add("figure.anchor", f"小节「{sec.title}」图片挂载点不一致", hard=False)
            if block.kind != BlockKind.FIGURE and (block.text or "").strip() and not block.source_refs:
                add("block.source", f"小节「{sec.title}」有正文块缺少资料出处")
            if INLINE_PAGE_RE.search(block.text):
                add("body.px", f"小节「{sec.title}」正文出现 P.x；出处应放小节末尾")
            if block.text.count("【延伸】") > 1:
                add("block.extension_dup", f"小节「{sec.title}」出现重复的【延伸】标记")

    # 覆盖/概览。scope_pages 非空时按“实际引用页 ∩ scope”计算，不信任自报百分比。
    if spec.scope_pages:
        scope = sorted(set(spec.scope_pages))
        if len(scope) != len(spec.scope_pages):
            add("coverage.scope", "scope_pages 有重复页码")
        if any(p < 1 or p > spec.page_count for p in scope):
            add("coverage.scope", "scope_pages 超出资料总页数")
        covered: set[int] = set()
        block_covered: set[int] = set()
        for sec in spec.sections:
            refs = list(sec.source_refs)
            block_refs = []
            for block in sec.blocks:
                block_refs.extend(block.source_refs)
                if block.figure is not None:
                    block_refs.append(block.figure.source)
            refs.extend(block_refs)
            for ref in refs:
                end = ref.page_end or ref.page_start
                covered.update(p for p in range(ref.page_start, end + 1) if p in scope)
            for ref in block_refs:
                end = ref.page_end or ref.page_start
                block_covered.update(p for p in range(ref.page_start, end + 1) if p in scope)
        coverage = (len(covered) / len(scope) * 100) if scope else 0.0
        block_coverage = (len(block_covered) / len(scope) * 100) if scope else 0.0
        if len(scope) <= FULL_COVERAGE_LIMIT and block_coverage < 80 and coverage >= 98:
            add("coverage.blocks",
                f"正文块只引用 {block_coverage:g}%（{len(block_covered)}/{len(scope)}），小节引用 {coverage:g}%；疑似用大范围引用补覆盖")
    else:
        scope = list(range(1, spec.page_count + 1))
        coverage = spec.coverage_percent

    if len(scope) <= FULL_COVERAGE_LIMIT:
        if spec.overview_mode:
            add("coverage.overview", f"{len(scope)} 页资料不能只做概览")
        if coverage < 98:
            add("coverage.low", f"覆盖 {coverage:g}% < 98%")
    else:
        if not spec.overview_mode:
            add("coverage.mode", f"{len(scope)} 页资料必须明确概览模式")
        if coverage >= 98:
            add("coverage.claim", ">150 页不应声称逐页 98% 覆盖", hard=False)

    # 结语/页脚
    if not spec.closing.text.strip():
        add("closing.empty", "缺少文末结语")
    if not spec.footer.agent_name.strip():
        add("footer.agent", "页脚缺少生成智能体名称")
    if not spec.footer.material_label.strip():
        add("footer.material", "页脚缺少资料名")
    if not spec.footer.disclaimer.strip():
        add("footer.disclaimer", "页脚缺少免责声明")
    if abs(spec.footer.coverage_percent - spec.coverage_percent) > 1:
        add("footer.coverage", "页脚覆盖率和正文覆盖率不一致", hard=False)
    if not spec.language_policy.gen_lang.strip():
        add("language.gen", "缺少生成语言")

    return LectureGateReport(passed=not any(x.hard for x in issues), issues=issues)

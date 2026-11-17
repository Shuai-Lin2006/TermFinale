"""逐页知识点覆盖审计：页码被引用 ≠ 内容被讲全。

对每个有文字的 PPT 页，让模型列出该页知识点，并对照引用该页的讲义段落，
标出 covered / partial / missing。图片页单独标 visual，交人工/视觉核对。
"""
from __future__ import annotations

import re

from typing import Literal, Protocol

from pydantic import BaseModel, Field

from tfv2.domain.lecture import LectureSection
from tfv2.domain.page import Page


class CoverageClient(Protocol):
    def json(self, system: str, user: str, *, max_tokens: int = 4096,
             temperature: float = 0.35) -> dict: ...


class PointCoverage(BaseModel):
    point: str
    covered: bool
    evidence: str | None = None


class PageCoverage(BaseModel):
    page_no: int
    status: Literal["covered", "partial", "missing", "visual", "empty", "overview", "unverified"]
    points: list[PointCoverage] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    note: str | None = None


SYSTEM = """你是课程内容核对员。只依据用户给出的“资料页原文”和“讲义对应段落”判断。
任务：
1. 从资料页原文中列出所有可讲/可考的知识点（定义、分类、规则、公式、反应、条件、例子、结论）；不要引入资料外内容。
2. 逐条判断讲义是否讲到：covered=true 表示有明确解释/步骤/结论；只出现关键词不算。
3. 列出没讲到的点。
4. evidence 用普通短句，不要写 LaTeX 反斜杠或公式源码。
只输出 JSON：
{"points":[{"point":"...","covered":true,"evidence":"讲义里的短句"}],
 "missing":["..."],
 "note":"可选"}
如果资料页没有文字或只有图片，输出 {"points":[],"missing":[],"note":"图片页"}。
不要输出 Markdown。"""


_PRACTICE = re.compile(
    r"(思考题|习题|练习题|课后题|复习题|简答题|问答题|计算题|题\s*\d+\s*图|试求|试画|试确定|画出.*波形|简述|试述|电路如图)"
)


def is_practice_page(text: str) -> bool:
    """Exercise pages are practice material, not missing lecture content."""
    t = text or ""
    if not _PRACTICE.search(t):
        return False
    if re.search(r"(思考题|习题|练习题|课后题|复习题|简答题|问答题|简述|试述)", t):
        return True
    lines = [x.strip() for x in t.splitlines() if x.strip()]
    numbered = sum(1 for x in lines if re.match(r"^\d{1,3}[.、．)]", x))
    asks = sum(1 for x in lines if re.search(r"(求|试|画|已知|为什么|说明|判断)", x))
    return numbered >= 2 or asks >= 4


def _refs_page(refs, page_no: int) -> bool:
    return any(
        ref.page_start <= page_no <= (ref.page_end or ref.page_start)
        for ref in refs
    )


def lecture_text_for_page(sections: list[LectureSection], page_no: int, *, limit: int = 6000) -> str:
    """取“真正引用这一页”的段落，而不是整节全部内容。

    旧实现只要小节里任一 block 引用该页，就把整节（含无关段落）塞给审计，
    长小节还会被 3000 字截断，导致新增的页级内容根本进不了审计上下文。
    这里按 block 的 source_refs 精确取；只有小节级出处命中、没有页级 block
    时才退回整节。图片图注也作为页级证据一并给出。
    """
    chunks: list[str] = []
    for sec in sections:
        page_blocks = [
            block for block in sec.blocks
            if block.kind.value != "figure" and _refs_page(block.source_refs, page_no)
        ]
        figure_blocks = [
            block for block in sec.blocks
            if block.kind.value == "figure" and block.figure is not None
            and _refs_page([block.figure.source], page_no)
        ]
        if page_blocks or figure_blocks:
            chunks.append(f"【{sec.title}】")
            chunks.extend(block.text for block in page_blocks)
            for block in figure_blocks:
                chunks.append(f"【图注】{block.figure.caption}")
            continue
        if _refs_page(sec.source_refs, page_no):
            # 只有小节级出处：保留旧行为，作为兜底上下文。
            chunks.append(f"【{sec.title}】")
            chunks.extend(
                block.text for block in sec.blocks
                if block.kind.value != "figure"
            )
    text = "\n".join(chunks)
    return text[:limit]


def audit_page(client: CoverageClient, page: Page, sections: list[LectureSection], *, overview: bool = False) -> PageCoverage:
    text = (page.text or "").strip()
    if overview:
        return PageCoverage(page_no=page.page_no, status="overview",
                            note="目录/提纲页；章节内容由后续小节覆盖")
    if not text:
        return PageCoverage(page_no=page.page_no, status="visual", note="图片页/空页，需人工视觉核对")
    if is_practice_page(text):
        return PageCoverage(page_no=page.page_no, status="overview",
                            note="习题/练习页：不计入讲授覆盖率")
    context = lecture_text_for_page(sections, page.page_no)
    if not context.strip():
        return PageCoverage(page_no=page.page_no, status="missing", missing=["整页未被讲义引用或讲解"])
    user = (
        f"资料第 {page.page_no} 页原文：\n{text[:5000]}\n\n"
        f"讲义中引用/讲解这一页的段落：\n{context}\n\n"
        "请按系统要求输出 JSON。"
    )
    data = None
    last = None
    for _ in range(1):
        try:
            data = client.json(SYSTEM, user, max_tokens=6000, temperature=0.0)
            break
        except Exception as exc:
            last = exc
    if data is None:
        raise last or RuntimeError('audit failed')
    points = [
        PointCoverage(point=str(x.get("point", "")), covered=bool(x.get("covered")),
                      evidence=x.get("evidence") or None)
        for x in (data.get("points") or []) if str(x.get("point", "")).strip()
    ]
    missing = [str(x) for x in (data.get("missing") or []) if str(x).strip()]
    if not points and not missing:
        # 有正文却一条知识点都没返回，多半是复核输出坏了，不是“内容为空”。
        # 把它记成 unverified（待复核），不要当成内容缺失去判未通过。
        if len(text) >= 80:
            return PageCoverage(page_no=page.page_no, status="unverified",
                                note=data.get("note") or "复核模型没返回知识点（输出可能不完整）")
        return PageCoverage(page_no=page.page_no, status="empty", note=data.get("note") or "模型未返回知识点")
    status: Literal["covered", "partial", "missing"] = "covered"
    if missing and len(missing) >= max(1, len(points)):
        status = "missing"
    elif missing:
        status = "partial"
    return PageCoverage(page_no=page.page_no, status=status, points=points, missing=missing,
                        note=data.get("note") or None)

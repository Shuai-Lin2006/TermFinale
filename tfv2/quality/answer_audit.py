"""例题/答案审计：只依据资料页，先查“有没有依据”，再查“推导/答案对不对”。

这是 LLM 辅助审计，不是形式化证明；结果必须人工复核后才能改稿。
"""
from __future__ import annotations

from typing import Literal, Protocol

from pydantic import BaseModel, Field

from tfv2.authoring.lecture import build_evidence_packet
from tfv2.domain.lecture import BlockKind, LectureSection
from tfv2.domain.page import PageLedger


class AuditClient(Protocol):
    def json(self, system: str, user: str, *, max_tokens: int = 4096,
             temperature: float = 0.35) -> dict: ...


class AnswerAudit(BaseModel):
    section_title: str
    block_id: str
    source_pages: list[int]
    text: str
    verdict: Literal["ok", "ok_extension", "fix", "unsupported", "uncertain"]
    confidence: float = Field(ge=0, le=1)
    reason: str
    corrected_text: str | None = None
    evidence: str | None = None


SYSTEM = """你是大学有机化学阅卷人。你的任务不是重写讲义，而是核对例题/答案。
只依据用户给出的资料页和题目本身判断；不要引入资料外的页码、定理或反应条件。
判断标准：
- ok：答案/推导正确，且资料页能支持关键结论。
- ok_extension：题目标了【延伸】，资料没有直接例题，但推导自洽、化学上正确。
- fix：答案/推导有错、与资料矛盾，或漏了关键条件；在 corrected_text 给最小修正。
- unsupported：资料没有依据，且没有【延伸】标记，不能冒充资料原题。
- uncertain：资料页是图片/空页，无法核对；不要猜。
只输出 JSON，不要 Markdown。格式：
{"verdict":"ok|ok_extension|fix|unsupported|uncertain","confidence":0.0,
 "reason":"一句话","corrected_text":"只给需要改的整段；不需要则 null",
 "evidence":"引用资料页里的短句；没有则 null"}
"""


def audit_example(client: AuditClient, ledger: PageLedger, section: LectureSection,
                  block_id: str, text: str, pages: list[int]) -> AnswerAudit:
    packet = build_evidence_packet(ledger, pages, max_chars=3600)
    user = (
        f"小节：{section.title}\n"
        f"资料页：{pages}\n"
        f"资料原文（带页码）：\n{packet}\n\n"
        f"待审例题/答案：\n{text}\n\n"
        "请判断并给 JSON。"
    )
    data = client.json(SYSTEM, user, max_tokens=1200, temperature=0.1)
    return AnswerAudit(
        section_title=section.title,
        block_id=block_id,
        source_pages=pages,
        text=text,
        verdict=data.get("verdict", "uncertain"),
        confidence=float(data.get("confidence", 0) or 0),
        reason=str(data.get("reason", "") or ""),
        corrected_text=data.get("corrected_text") or None,
        evidence=data.get("evidence") or None,
    )


def audit_sections(client: AuditClient, ledger: PageLedger,
                   sections: list[LectureSection]) -> list[AnswerAudit]:
    results: list[AnswerAudit] = []
    for sec in sections:
        for block in sec.blocks:
            if block.kind != BlockKind.EXAMPLE:
                continue
            pages: list[int] = []
            for ref in block.source_refs:
                pages.extend(range(ref.page_start, (ref.page_end or ref.page_start) + 1))
            pages = sorted(set(pages))
            results.append(audit_example(client, ledger, sec, block.id, block.text, pages))
    return results

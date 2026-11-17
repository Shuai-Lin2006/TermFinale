"""审计驱动的逐点补讲：把复核判成 partial/missing 的页，按缺的知识点补讲。

为什么这样做：
- 现在一节写 4 页，密集定理页常漏点；复核逐页列出“没讲到的知识点”；
- 与其整节重写（慢、贵、还会丢页），不如只针对缺的点补几段短讲解，挂到该页所在小节；
- 补讲一律标「补讲（第 N 页）」并带出处，不冒充原来成文。

成本控制：只补有缺口的页，每页最多 max_points 条；复核与补讲都可单独调用。
"""
from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from tfv2.domain.lecture import BlockKind, LectureBlock, LectureSection, SourceRef
from tfv2.domain.page import Page, PageQuality
from tfv2.llm.client import DeepSeekClient
from tfv2.product import source_pages as source_pages_mod
from tfv2.quality import coverage_audit
from tfv2.quality.artifact_audit import audit_artifact_dir

TOPUP_SYSTEM = (
    "你是课程助教。只依据给出的资料页原文，为“讲义没讲到的知识点”各写 1–2 句讲解。"
    "要求：不引入资料外内容；每条都要能在原文里找到依据；不要写空话。"
    '只输出 JSON：{"points":[{"point":"知识点","text":"1-2 句讲解"}]}。'
)


def _load_sections(path: Path) -> list[LectureSection]:
    return [LectureSection.model_validate(x)
            for x in json.loads((path / "sections.json").read_text(encoding="utf-8"))]


def _save_sections(path: Path, sections: list[LectureSection]) -> None:
    (path / "sections.json").write_text(
        json.dumps([s.model_dump(mode="json") for s in sections], ensure_ascii=False, indent=2),
        encoding="utf-8")


def _section_for_page(sections: list[LectureSection], page_no: int) -> LectureSection | None:
    for sec in sections:
        for ref in sec.source_refs or []:
            if int(ref.page_start) <= page_no <= int(ref.page_end or ref.page_start):
                return sec
        for block in sec.blocks:
            for ref in block.source_refs or []:
                if int(ref.page_start) <= page_no <= int(ref.page_end or ref.page_start):
                    return sec
    return sections[0] if sections else None


def _page_audit(client, page: Page, sections: list[LectureSection]) -> dict:
    try:
        got = coverage_audit.audit_page(client, page, sections)
        return got.model_dump()
    except Exception as exc:  # noqa: BLE001
        return {"page_no": page.page_no, "status": "unverified", "points": [], "missing": [],
                "note": f"{type(exc).__name__}: {str(exc)[:120]}"}


def _write_points(client, *, page_no: int, text: str, missing: list[str], limit: int) -> list[dict]:
    missing = [m for m in missing if str(m).strip()][:limit]
    if not missing:
        return []
    user = (
        f"资料第 {page_no} 页原文：\n{text[:4000]}\n\n"
        "讲义没讲到的知识点：\n" + "\n".join(f"- {m}" for m in missing) +
        "\n\n请为每个知识点写 1–2 句讲解，只依据上面原文。"
    )
    data = client.json(TOPUP_SYSTEM, user, max_tokens=1800, temperature=0.2)
    out: list[dict] = []
    for item in (data.get("points") or [])[:limit]:
        point = str(item.get("point") or "").strip()
        body = str(item.get("text") or "").strip()
        if body and len(body) >= 8:
            out.append({"point": point, "text": body})
    return out


def topup_artifact(aid: str, *, artifact_path: Path | None = None, client=None,
                   max_pages: int = 12, max_points: int = 6, reaudit: bool = True,
                   progress=None) -> dict:
    """对产物做逐点补讲；返回 before/after 复核计数与补讲条数。"""
    from tfv2.product import service

    path = Path(artifact_path) if artifact_path else service.artifact_path(aid)
    if path is None or not (path / "sections.json").is_file():
        raise ValueError("产物缺少 sections.json")
    rows = (source_pages_mod.load_source_pages(path) or [])
    if not rows:
        raise ValueError("产物缺少资料页文本")
    material = "material"
    meta = path / "source_pages.json"
    if meta.is_file():
        try:
            material = str(json.loads(meta.read_text(encoding="utf-8")).get("material") or "material")
        except Exception:
            material = "material"
    sections = _load_sections(path)
    if client is None:
        # 复核/补讲用 Qwen 文本模型（快、可解析），不可用时退 DeepSeek 低思考
        try:
            from tfv2.llm.qwen_text import QwenTextClient
            client = QwenTextClient()
        except Exception:
            try:
                from tfv2.llm.kimi import KimiClient
                client = KimiClient()
            except Exception:
                client = DeepSeekClient(effort="low")

    def page_obj(row: dict) -> Page:
        return Page(material=material, page_no=int(row["page"]), text=str(row.get("text") or ""),
                    quality=PageQuality.TEXT)

    # 只补被讲义覆盖的页（没被引用的页属于覆盖问题，另行处理）
    covered_pages: list[int] = []
    for sec in sections:
        for ref in sec.source_refs or []:
            covered_pages.extend(range(int(ref.page_start), int(ref.page_end or ref.page_start) + 1))
    scoped = [r for r in rows if int(r["page"]) in set(covered_pages)][:max_pages]

    audits: dict[int, dict] = {}
    def work(row: dict) -> dict:
        return _page_audit(client, page_obj(row), sections)

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(work, row): int(row["page"]) for row in scoped}
        for fut in as_completed(futures):
            got = fut.result()
            audits[int(got.get("page_no") or 0)] = got
    before = _counts(audits.values())

    added = 0
    topup_rows: list[dict] = []
    for row in scoped:
        page_no = int(row["page"])
        audit_row = audits.get(page_no) or {}
        if audit_row.get("status") not in ("partial", "missing"):
            continue
        missing = [str(x) for x in (audit_row.get("missing") or [])]
        if not missing:
            continue
        try:
            points = _write_points(client, page_no=page_no, text=str(row.get("text") or ""),
                                   missing=missing, limit=max_points)
        except Exception:
            continue
        if not points:
            continue
        sec = _section_for_page(sections, page_no)
        if sec is None:
            continue
        for idx, item in enumerate(points, start=1):
            text = f"补讲（第 {page_no} 页 · {item['point'] or '知识点'}）：{item['text']}"
            if any(b.text == text for b in sec.blocks):
                continue
            sec.blocks.append(LectureBlock(
                id=f"topup-{page_no}-{idx}-{len(sec.blocks)}", kind=BlockKind.PARAGRAPH, text=text,
                source_refs=[SourceRef(material=material, page_start=page_no, page_end=page_no)],
                doc_page=page_no,
            ))
            added += 1
        topup_rows.append({"page": page_no, "missing": missing[:max_points], "added": len(points)})

    if added:
        _save_sections(path, sections)
        try:
            (path / "topup.json").write_text(json.dumps({"pages": topup_rows, "added": added},
                                                        ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
        # 重新渲染讲义（HTML+PDF），否则新增块只存在于 JSON
        try:
            from tfv2.build import build_project
            build_project(path / "project.json", pdf=True)
        except Exception:
            pass

    after = before
    if reaudit and added:
        try:
            rows_after = audit_artifact_dir(path)
            after = _counts(rows_after)
        except Exception:
            pass
    return {"artifact": aid, "before": before, "after": after, "added": added,
            "pages": topup_rows}


def _counts(rows) -> dict:
    out = {"covered": 0, "partial": 0, "missing": 0, "unverified": 0, "other": 0}
    for r in rows or []:
        st = str(r.get("status") or "other")
        out[st if st in out else "other"] += 1
    return out

"""Run coverage audit directly against a generated artifact directory."""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from tfv2.domain.lecture import LectureSection
from tfv2.domain.page import Page, PageQuality
from tfv2.llm.qwen_text import QwenTextClient
from tfv2.quality.coverage_audit import audit_page


def audit_artifact_dir(path: str | Path) -> list[dict]:
    out = Path(path)
    raw = json.loads((out / "source_pages.json").read_text(encoding="utf-8"))
    pages = raw.get("pages") or raw
    sections = [LectureSection.model_validate(x) for x in json.loads((out / "sections.json").read_text(encoding="utf-8"))]
    # 复核客户端按顺序尝试：Qwen 的 JSON 输出偶尔会坏，坏了就换 DeepSeek 再试，
    # 不能因为一次解析失败就把整页判成“内容缺失”。
    clients: list = []
    try:
        clients.append(QwenTextClient())
    except Exception:
        pass
    try:
        from tfv2.llm.kimi import KimiClient
        clients.append(KimiClient())
    except Exception:
        pass
    try:
        from tfv2.llm.client import DeepSeekClient
        clients.append(DeepSeekClient(model="deepseek-flash", effort="low"))
    except Exception:
        pass
    if not clients:
        raise RuntimeError("没有可用的复核模型")

    def work(row):
        page = Page(material=raw.get("material") or "material", page_no=int(row.get("page")),
                    text=row.get("text") or "", quality=PageQuality.OCR)
        last: Exception | None = None
        # 每个后端只试一次：同模型重复同一 prompt 很少能修好 JSON，换模型更有效。
        for c in clients:
            try:
                return audit_page(c, page, sections,
                                  overview=("目录" in (page.text or "")[:120])).model_dump()
            except Exception as exc:  # noqa: BLE001
                last = exc
        # 复核没跑完 ≠ 内容缺失：标 unverified，交给“待复核”，不能冒充 partial（那会判成未通过）。
        return {"page_no": page.page_no, "status": "unverified", "points": [], "missing": [],
                "note": f"复核没跑完：{type(last).__name__}: {str(last)[:120]}"}

    result: list[dict] = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        for fut in as_completed([pool.submit(work, row) for row in pages]):
            result.append(fut.result())
    result.sort(key=lambda x: x.get("page_no", 0))
    (out / "coverage_audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result

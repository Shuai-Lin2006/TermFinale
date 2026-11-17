"""公式层：MinerU 解析出的 LaTeX，用来让公式页可搜索、可出题。

底线：
- 公式来自 OCR/MinerU，**不是猜的**；
- 过不了 KaTeX 的公式不硬塞（会让 PDF 门禁挂），宁可不展示；
- 每条公式都带原资料页码，可回原文核对。
"""
from __future__ import annotations

import json
import re
from pathlib import Path


def _plain_ok(latex: str) -> bool:
    from tfv2.authoring.normalize import _formula_problem

    body = str(latex or "").strip().strip("$").strip()
    return bool(body) and not _formula_problem(body)


def load_formulas(artifact_path: Path | None) -> dict[int, list[dict]]:
    """读产物目录的 formulas.json → {页码: [{latex, display}]}；没有就空。"""
    if artifact_path is None:
        return {}
    path = Path(artifact_path) / "formulas.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    rows = data.get("formulas") if isinstance(data, dict) else data
    out: dict[int, list[dict]] = {}
    for item in rows or []:
        try:
            page = int(item.get("page"))
        except Exception:
            continue
        latex = str(item.get("latex") or "").strip()
        if page < 1 or not latex:
            continue
        out.setdefault(page, []).append({"latex": latex, "display": bool(item.get("display"))})
    return out


def formula_blocks_for_page(*, local_page: int, orig_page: int, formulas: list[dict],
                            material: str, limit: int = 6) -> list[dict]:
    """给某一页生成可渲染的公式块；过不了 KaTeX 的跳过，不制造坏 PDF。"""
    blocks: list[dict] = []
    seen: set[str] = set()
    for item in formulas or []:
        latex = re.sub(r"\s+", " ", str(item.get("latex") or "")).strip().strip("$").strip()
        if not latex or latex in seen or not _plain_ok(latex):
            continue
        seen.add(latex)
        blocks.append({
            "id": f"f{local_page}-{len(blocks) + 1}",
            "kind": "formula",
            "text": f"$${latex}$$",
            "source_refs": [{"material": material, "page_start": orig_page, "page_end": orig_page}],
            "figure": None,
            "doc_page": local_page,
        })
        if len(blocks) >= limit:
            break
    return blocks

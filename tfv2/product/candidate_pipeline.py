"""Candidate-first extraction: local candidates, batch LLM verification.

The model never reads every page. It sees 20 pages of candidates + short source
excerpts, accepts/rewrites points, and returns quoted items. Pages with no
accepted item keep local candidates and are explicitly counted as local-only.
"""
from __future__ import annotations

from . import local_extract


def _norm(text: str) -> str:
    return "".join(str(text or "").lower().split())[:200]


def verify_points(client, page_text: dict[int, str], pages: list[int], *, batch_pages: int = 5) -> dict:
    pages = sorted(pages)
    local = local_extract.extract_points(page_text, pages)
    by_page: dict[int, list[dict]] = {}
    for item in local:
        by_page.setdefault(int(item["page"]), []).append(item)
    accepted: dict[int, list[dict]] = {}
    errors = []
    for start in range(0, len(pages), batch_pages):
        batch = pages[start:start + batch_pages]
        cand = [{"id": i, "page": int(x["page"]), "point": x["point"], "detail": x["detail"], "quote": x["quote"]}
                for i, x in enumerate(local) if int(x["page"]) in set(batch)][:20]
        excerpt = "\n".join(f"[第{p}页] {str(page_text.get(p,''))[:300]}" for p in batch)
        prompt = (
            "只核验下面'候选'，不要编造候选之外的内容。输出 JSON："
            '{"items":[{"id":1,"page":2,"point":"...","detail":"...","quote":"原文一句"}]}。'
            "保留真正的定义/定理/公式/结论/步骤；删除标题、目录、页眉、空泛话。每题最多 2 条。"
        )
        user = "候选：\n" + json.dumps(cand, ensure_ascii=False)[:12000] + "\n\n资料节选：\n" + excerpt
        try:
            data = client.json(prompt, user, max_tokens=8000, temperature=0.1)
            items = data.get("items") if isinstance(data, dict) else None
            if not isinstance(items, list):
                raise ValueError("no items")
            for item in items:
                if not isinstance(item, dict):
                    continue
                try:
                    p = int(item.get("page"))
                    if p not in batch:
                        continue
                    point = str(item.get("point") or "").strip()
                    detail = str(item.get("detail") or "").strip()
                    quote = str(item.get("quote") or "").strip()
                    if len(point) < 4 or not quote:
                        continue
                    accepted.setdefault(p, []).append({
                        "point": point[:80], "detail": detail[:240], "quote": quote[:240],
                        "importance": 3, "importance_label": "理解",
                        "importance_reason": "批量核验", "page": p, "page_end": p,
                        "verified": True,
                    })
                except Exception:
                    continue
        except Exception as exc:
            errors.append(str(exc))
    final = []
    model_pages: set[int] = set()
    local_only: set[int] = set()
    missing: set[int] = set()
    for p in pages:
        if accepted.get(p):
            final.extend(accepted[p][:3])
            model_pages.add(p)
        else:
            local_items = by_page.get(p, [])[:3]
            if local_items:
                for x in local_items:
                    x = dict(x); x["local_only"] = True
                    final.append(x)
                local_only.add(p)
            else:
                missing.add(p)
    return {
        "items": final,
        "pages": len(pages),
        "model_pages": len(model_pages),
        "local_only_pages": len(local_only),
        "missing_pages": sorted(missing),
        "fallback_percent": round(len(local_only | missing) / max(1, len(pages)) * 100, 2),
        "errors": errors[:5],
    }


import json

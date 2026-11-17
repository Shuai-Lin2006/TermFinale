"""Auditable book-level report from chapter artifacts."""
from __future__ import annotations

import json
import time
from pathlib import Path

from tfv2.llm import pricing


def _load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def build(index_path: str | Path, out_path: str | Path | None = None) -> dict:
    path = Path(index_path)
    index = _load_json(path)
    chapters = []
    for c in index.get("chapters") or []:
        cdir = path.parent / c.get("id", "")
        manifest = _load_json(cdir / "manifest.json")
        # Generated artifacts live under ARTIFACT_ROOT; the worker result is
        # the direct evidence for gate status.
        worker = _load_json(cdir / "worker_result.json")
        quality = worker.get("quality") or {}
        usage = worker.get("usage") or {}
        cost = pricing.estimate(usage.get("by_model") or {})
        chapters.append({
            "id": c.get("id"),
            "title": c.get("title"),
            "pages": c.get("pages"),
            "page_count": c.get("page_count"),
            "status": c.get("status"),
            "artifact_id": c.get("artifact_id"),
            "seconds": c.get("seconds"),
            "error": c.get("error") or "",
            "gate_passed": bool(worker.get("gate_passed")),
            "content_passed": bool(quality.get("content_passed")),
            "pdf_passed": bool(quality.get("pdf_passed")),
            "usage": usage,
            "cost_cny": cost,
        })
    total = len(chapters)
    validated = sum(1 for c in chapters if c["status"] == "validated")
    failed = sum(1 for c in chapters if c["status"] == "failed")
    done = sum(1 for c in chapters if c["status"] == "done")
    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "source": index.get("source"),
        "page_count": index.get("page_count"),
        "split_source": index.get("split_source"),
        "summary": {
            "chapters": total,
            "validated": validated,
            "done": done,
            "failed": failed,
            "pending": sum(1 for c in chapters if c.get("status") in ("pending", "running")),
            "seconds": round(sum(float(c.get("seconds") or 0) for c in chapters), 2),
            "all_validated": total > 0 and validated == total,
            "cost_cny": (round(sum(c["cost_cny"] for c in chapters), 6)
                          if chapters and all(c["cost_cny"] is not None for c in chapters) else None),
            "calls": sum(int((c.get("usage") or {}).get("calls") or 0) for c in chapters),
            "total_tokens": sum(int((c.get("usage") or {}).get("total_tokens") or 0) for c in chapters),
        },
        "chapters": chapters,
    }
    if out_path is not None:
        Path(out_path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report

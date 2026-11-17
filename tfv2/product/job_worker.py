"""Minimal job worker: queued -> running -> generate 2-page previews -> done."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .job_state import JobStage, JobStore


def run_job(job_id: str, store: JobStore, *, pages: int = 2) -> dict:
    rec = store.get(job_id)
    if rec.stage != JobStage.QUEUED:
        raise ValueError(f"job is {rec.stage.value}, expected queued")
    rec = store.start(job_id)
    total = len(rec.plan.files)
    try:
        for i, f in enumerate(rec.plan.files, 1):
            store.event(job_id, "generate", f"开始 {f.name}", i - 1, total)
            if f.artifact_id:
                from .preview_generate import generate_preview
                out = generate_preview(f.artifact_id, f"{job_id}-{i}", pages=pages)
                store.event(job_id, "preview", f"{f.name} 预览完成：{out.name}", i, total)
            else:
                store.event(job_id, "skip", f"{f.name} 没有 artifact_id，跳过", i, total)
        rec = store.get(job_id)
        rec.stage = JobStage.DONE
        rec.events.append(__import__("tfv2.product.job_state", fromlist=["JobEvent"]).JobEvent(
            at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
            stage="done", message="任务完成", current=total, total=total))
        store.save(rec)
    except Exception as exc:
        rec = store.get(job_id)
        rec.stage = JobStage.FAILED
        rec.events.append(__import__("tfv2.product.job_state", fromlist=["JobEvent"]).JobEvent(
            at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
            stage="failed", message=f"{type(exc).__name__}: {str(exc)[:200]}"))
        store.save(rec)
        raise
    return store.get(job_id).model_dump()


def main() -> None:
    from core import paths
    from .job_state import JobStore
    if len(sys.argv) < 2:
        raise SystemExit("usage: python -m tfv2.product.job_worker <job_id>")
    store = JobStore(paths.data_dir() / "jobs")
    print(json.dumps(run_job(sys.argv[1], store), ensure_ascii=False)[:1200])


if __name__ == "__main__":
    main()

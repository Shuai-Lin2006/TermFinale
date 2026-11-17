"""Chapter-level artifacts with a durable checkpoint.

One PDF may contain 300 pages / 10 chapters. Each chapter gets its own PDF,
manifest and status. A runner writes status after every chapter, so a crash
resumes at the first pending/failed chapter instead of redoing the book.
"""
from __future__ import annotations

import json
import queue
import threading
import time
from pathlib import Path
from typing import Callable

import pymupdf

from . import longdoc

STATUSES = ("pending", "running", "done", "validated", "failed")


def build_index(pdf_path: str | Path, out_dir: str | Path) -> dict:
    pdf_path = Path(pdf_path)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    split = longdoc.split_pdf(pdf_path)
    src = pymupdf.open(str(pdf_path))
    chapters = []
    try:
        for i, c in enumerate(split["chapters"], start=1):
            cid = f"ch{i:02d}"
            cdir = out / cid
            cdir.mkdir(exist_ok=True)
            target = cdir / "source.pdf"
            part = pymupdf.open()
            for p in range(c["start"], c["end"] + 1):
                part.insert_pdf(src, from_page=p - 1, to_page=p - 1)
            part.save(str(target))
            part.close()
            manifest = {
                "id": cid, "title": c["title"], "pages": [c["start"], c["end"]],
                "page_count": c["end"] - c["start"] + 1,
                "source_pdf": str(target), "status": "pending", "artifact_id": "",
                "error": "",
            }
            (cdir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            chapters.append(manifest)
    finally:
        src.close()
    index = {"source": str(pdf_path), "page_count": split["page_count"],
             "split_source": split["source"], "chapters": chapters}
    (out / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    return index


def build_manual_index(pdf_path: str | Path, out_dir: str | Path, ranges: list[tuple[int, int, str]]) -> dict:
    """Build chapter artifacts from explicit page ranges (no TOC required)."""
    pdf_path = Path(pdf_path)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    src = pymupdf.open(str(pdf_path))
    page_count = len(src)
    chapters = []
    try:
        for i, (start, end, title) in enumerate(ranges, start=1):
            cid = f"ch{i:02d}"
            cdir = out / cid
            cdir.mkdir(exist_ok=True)
            target = cdir / "source.pdf"
            part = pymupdf.open()
            for p in range(start, end + 1):
                part.insert_pdf(src, from_page=p - 1, to_page=p - 1)
            part.save(str(target))
            part.close()
            manifest = {"id": cid, "title": title, "pages": [start, end],
                        "page_count": end - start + 1, "source_pdf": str(target),
                        "status": "pending", "artifact_id": "", "error": ""}
            (cdir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            chapters.append(manifest)
    finally:
        src.close()
    covered = []
    for c in chapters:
        covered.extend(range(c["pages"][0], c["pages"][1] + 1))
    if sorted(covered) != list(range(1, page_count + 1)):
        raise ValueError("手工章节范围没有完整覆盖 PDF")
    index = {"source": str(pdf_path), "page_count": page_count, "split_source": "manual", "chapters": chapters}
    (out / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    return index


def load_index(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_index(index: dict, path: str | Path) -> None:
    Path(path).write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")


def mark(index: dict, path: str | Path, chapter_id: str, status: str, *, artifact_id: str = "", error: str = "", seconds: float | None = None) -> dict:
    if status not in STATUSES:
        raise ValueError(f"未知章节状态：{status}")
    for c in index.get("chapters") or []:
        if c["id"] == chapter_id:
            c["status"] = status
            if artifact_id:
                c["artifact_id"] = artifact_id
            c["error"] = error
            if seconds is not None:
                c["seconds"] = round(float(seconds), 2)
            c["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            save_index(index, path)
            return index
    raise KeyError(chapter_id)


def run_subprocess(index_path: str | Path, *, timeout_sec: float = 300.0,
                   stop_after: int | None = None, worker_cmd: list[str] | None = None,
                   retry_unvalidated: bool = False,
                   retry_failed_once: bool = False,
                   global_budget_sec: float | None = None) -> dict:
    """Run each chapter in its own process; kill the process group on timeout."""
    import os
    import signal
    import subprocess
    import sys

    path = Path(index_path)
    index = load_index(path)
    done = 0
    deadline = time.monotonic() + global_budget_sec if global_budget_sec else None
    for c in list(index.get("chapters") or []):
        if deadline is not None and time.monotonic() >= deadline:
            break
        if c.get("status") not in ("pending", "failed") and not (retry_unvalidated and c.get("status") == "done"):
            continue
        if stop_after is not None and done >= stop_after:
            break
        started = time.time()
        mark(index, path, c["id"], "running")
        cdir = path.parent / c["id"]
        cdir.mkdir(parents=True, exist_ok=True)
        mpath = cdir / "manifest.json"
        rpath = cdir / "worker_result.json"
        mpath.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")
        rpath.unlink(missing_ok=True)
        cmd = list(worker_cmd) if worker_cmd else [sys.executable, "-m", "tfv2.product.chapter_worker"]
        cmd += [str(mpath), str(rpath)]
        log = (cdir / "worker.log").open("w", encoding="utf-8")
        proc = None
        try:
            proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            effective = max(0.01, float(timeout_sec))
            if deadline is not None:
                effective = max(0.01, min(effective, deadline - time.monotonic()))
            try:
                rc = proc.wait(timeout=effective)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except Exception:
                    proc.kill()
                proc.wait(timeout=5)
                raise TimeoutError(f"章节 {c['id']} 超过 {effective:.0f}s，已 kill 进程组")
            result = {}
            if rpath.is_file():
                try:
                    result = json.loads(rpath.read_text(encoding="utf-8"))
                except Exception:
                    result = {}
            if rc != 0 or result.get("error"):
                raise RuntimeError(result.get("error") or f"worker 退出码 {rc}")
            aid = str(result.get("artifact_id") or "")
            if not aid:
                raise RuntimeError("worker 未返回 artifact_id")
            status = "validated" if result.get("gate_passed") else "done"
            mark(index, path, c["id"], status, artifact_id=aid, seconds=time.time() - started)
        except Exception as exc:
            mark(index, path, c["id"], "failed", error=f"{type(exc).__name__}: {exc}",
                 seconds=time.time() - started)
        finally:
            log.close()
            if proc is not None and proc.poll() is None:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except Exception:
                    proc.kill()
        done += 1
    index = load_index(path)
    failed = [c for c in index.get("chapters") or [] if c.get("status") == "failed"]
    if retry_failed_once and failed:
        remaining = None
        if global_budget_sec:
            remaining = deadline - time.monotonic()
        if remaining is None or remaining > 5:
            old_qwen = os.environ.get("TERMFINALE_FORCE_QWEN")
            os.environ["TERMFINALE_FORCE_QWEN"] = "1"
            try:
                return run_subprocess(path, timeout_sec=timeout_sec, stop_after=stop_after,
                                      worker_cmd=worker_cmd, retry_unvalidated=retry_unvalidated,
                                      retry_failed_once=False, global_budget_sec=remaining)
            finally:
                if old_qwen is None:
                    os.environ.pop("TERMFINALE_FORCE_QWEN", None)
                else:
                    os.environ["TERMFINALE_FORCE_QWEN"] = old_qwen
    return index


def pending(index: dict) -> list[dict]:
    return [c for c in index.get("chapters") or [] if c.get("status") in ("pending", "failed")]


def _call_builder(builder: Callable[[dict], dict], chapter: dict, timeout_sec: float) -> dict:
    q: queue.Queue = queue.Queue(maxsize=1)

    def worker():
        try:
            q.put(("ok", builder(chapter)))
        except Exception as exc:  # noqa: BLE001
            q.put(("error", exc))

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    try:
        kind, value = q.get(timeout=max(0.01, float(timeout_sec)))
    except queue.Empty as exc:
        raise TimeoutError(f"章节 {chapter.get('id')} 超过 {timeout_sec}s 硬超时") from exc
    if kind == "error":
        raise value
    return value or {}


def run(index_path: str | Path, builder: Callable[[dict], dict], *, stop_after: int | None = None,
        timeout_sec: float = 300.0) -> dict:
    """Run pending/failed chapters; checkpoint after each one."""
    path = Path(index_path)
    index = load_index(path)
    done = 0
    for c in list(index.get("chapters") or []):
        if c.get("status") not in ("pending", "failed"):
            continue
        if stop_after is not None and done >= stop_after:
            break
        started = time.time()
        mark(index, path, c["id"], "running")
        try:
            result = _call_builder(builder, c, timeout_sec)
            aid = str(result.get("artifact_id") or result.get("id") or "")
            if not aid:
                raise RuntimeError("builder 未返回 artifact_id")
            status = "validated" if result.get("gate_passed") else "done"
            mark(index, path, c["id"], status, artifact_id=aid, seconds=time.time() - started)
        except Exception as exc:
            mark(index, path, c["id"], "failed", error=f"{type(exc).__name__}: {exc}",
                 seconds=time.time() - started)
        done += 1
    return load_index(path)

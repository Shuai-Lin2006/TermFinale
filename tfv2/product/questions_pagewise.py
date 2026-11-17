"""Pagewise question extraction: a 7-page scan must not be one huge prompt."""
from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from . import service, tasks

_QNO = re.compile(r"^\s*(?:\d{1,3}\s*[.、]|[（(]\s*\d{1,3}\s*[）)])")
_OPT = re.compile(r"^\s*[A-D]\s*[.、]")

def _has_question(text: str) -> bool:
    lines = [x.strip() for x in (text or "").splitlines() if x.strip()]
    numbered = sum(1 for x in lines if _QNO.match(x))
    options = sum(1 for x in lines if _OPT.match(x))
    answers = (text or "").count("【答案】")
    return numbered >= 1 or (options >= 2 and answers >= 1)


def extract_pages(page_text: dict[int, str], pages: list[int], client, *, workers: int = 3) -> dict:
    from .local_extract import extract_questions as local_questions

    def work(p: int):
        try:
            doc = tasks._extract("extract_questions", {"id": f"p{p}", "title": f"第{p}页"},
                                 [p], page_text, client, "original", "zh")
            return p, (doc.get("content") or {}).get("items") or [], []
        except Exception as exc:  # noqa: BLE001
            return p, [], [f"第{p}页：{type(exc).__name__}: {exc}"]

    question_pages = [p for p in pages if _has_question(page_text.get(p, ""))]
    no_question = [p for p in pages if p not in question_pages]
    items = []
    errors = []
    covered = set()
    with ThreadPoolExecutor(max_workers=max(1, min(workers, len(question_pages) or 1))) as pool:
        for fut in as_completed([pool.submit(work, p) for p in question_pages]):
            p, got, err = fut.result()
            errors.extend(err)
            if got:
                covered.add(p)
                items.extend(got)
            else:
                # no model output: keep explicitly answered local questions, no invention
                local = [x for x in local_questions(page_text, [p])
                         if x.get("answer_text") and x["answer_text"] != "原卷未给答案"]
                if local:
                    covered.add(p)
                    items.extend(local)
    # dedupe by source number + stem
    out = []
    seen = set()
    for x in items:
        key = (str(x.get("source_no") or ""), str(x.get("stem") or "")[:120])
        if key in seen:
            continue
        seen.add(key)
        out.append(x)
    return {"items": out, "pages": pages, "question_pages": question_pages,
            "no_question_pages": no_question, "covered_pages": sorted(covered),
            "coverage": round(len(covered) / max(1, len(question_pages)), 3),
            "errors": errors[:20]}


def extract_artifact(aid: str, client, *, workers: int = 3) -> dict:
    path = service.artifact_path(aid)
    if path is None:
        raise FileNotFoundError("artifact 不存在")
    data = json.loads((path / "source_pages.json").read_text(encoding="utf-8"))
    pages = data.get("pages") if isinstance(data, dict) else data
    text = {i + 1: (p.get("text") or "") for i, p in enumerate(pages)}
    return extract_pages(text, list(text), client, workers=workers)

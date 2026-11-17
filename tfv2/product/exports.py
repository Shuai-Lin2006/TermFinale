"""Question export: CSV for spreadsheets, CSV for Anki import."""
from __future__ import annotations

import csv
import io
import re


def _qlist(doc: dict) -> list[dict]:
    kind = str(doc.get("kind") or "")
    content = doc.get("content") or {}
    if kind == "exam":
        return [q for sec in content.get("sections") or [] for q in sec.get("questions") or []]
    if kind == "paper":
        return list(content.get("questions") or [])
    return list(content.get("items") or [])


def _safe(value) -> str:
    text = str(value if value is not None else "")
    if text[:1] in ("=", "+", "-", "@"):
        return "'" + text
    return text


def _options(q: dict) -> str:
    opts = q.get("options") or []
    return " | ".join(f"{chr(65 + i)}. {o}" for i, o in enumerate(opts))


def _answer(q: dict) -> str:
    if q.get("answer_text"):
        return str(q.get("answer_text"))
    if isinstance(q.get("answer"), int):
        return chr(65 + q["answer"])
    return ""


def questions_csv(doc: dict) -> str:
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["no", "year", "exam", "source_no", "qtype", "stem", "options",
                     "answer", "analysis", "points", "source_page", "quote"])
    for q in _qlist(doc):
        writer.writerow([
            _safe(q.get("no", "")), _safe(q.get("year", "")), _safe(q.get("exam", "")),
            _safe(q.get("source_no", "")), _safe(q.get("qtype", "")), _safe(q.get("stem", "")),
            _safe(_options(q)), _safe(_answer(q)), _safe(q.get("analysis", "")),
            _safe(q.get("points", 0)), _safe(q.get("source_page", "")),
            _safe(q.get("quote", "")),
        ])
    return "\ufeff" + out.getvalue()


def anki_csv(doc: dict) -> str:
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["Front", "Back", "Tags"])
    for q in _qlist(doc):
        opts = _options(q)
        front = str(q.get("stem") or "")
        if opts:
            front += "<br>" + opts.replace(" | ", "<br>")
        back = _answer(q)
        analysis = str(q.get("analysis") or "")
        if analysis:
            back += "<br><br>" + analysis
        meta = " ".join(x for x in [str(q.get("year") or ""), str(q.get("exam") or ""),
                                    str(q.get("source_no") or "")] if x)
        tags = "TermFinale " + (str(q.get("qtype") or "question"))
        if meta:
            back += "<br><small>" + meta + "</small>"
        writer.writerow([_safe(front), _safe(back), _safe(tags)])
    return "\ufeff" + out.getvalue()


def export_name(doc: dict, suffix: str) -> str:
    title = str(doc.get("title") or doc.get("kind") or "TermFinale")
    safe = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff_-]+", "_", title)[:40].strip("_") or "TermFinale"
    return f"{safe}_{suffix}.csv"

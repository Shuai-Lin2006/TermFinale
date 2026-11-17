"""Pipe-table structure: parse, validate, normalize.

Docling/TableFormer gives Markdown tables. The rest of the pipeline already
renders pipe tables in HTML and Word; this module is the deterministic gate
that decides whether a table is structurally usable or must stay as text.
"""
from __future__ import annotations

import re


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _separator(line: str) -> bool:
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    return len(cells) >= 2 and all(re.fullmatch(r":?-{1,}:?", c) for c in cells)


def parse_pipe_table(md: str) -> dict | None:
    lines = [x.strip() for x in str(md or "").splitlines() if x.strip()]
    if len(lines) < 2 or "|" not in lines[0]:
        return None
    headers = _cells(lines[0])
    start = 1
    if start < len(lines) and _separator(lines[start]):
        start += 1
    rows = []
    for line in lines[start:]:
        if "|" not in line:
            continue
        row = _cells(line)
        if not row or all(not c for c in row):
            continue
        if len(row) != len(headers):
            return None
        rows.append(row)
    if len(headers) < 2 or len(rows) < 1:
        return None
    if any(not h for h in headers):
        return None
    return {"headers": headers, "rows": rows}


def table_quality(md: str) -> dict:
    parsed = parse_pipe_table(md)
    if not parsed:
        return {"ok": False, "reason": "表格不是合法二维结构"}
    if len(parsed["headers"]) > 12:
        return {"ok": False, "reason": "列数过多，疑似把正文当表格"}
    return {"ok": True, "reason": "", "cols": len(parsed["headers"]), "rows": len(parsed["rows"])}


def normalize_table(md: str) -> str:
    parsed = parse_pipe_table(md)
    if not parsed:
        return str(md or "").strip()
    header = "| " + " | ".join(parsed["headers"]) + " |"
    sep = "| " + " | ".join("---" for _ in parsed["headers"]) + " |"
    body = ["| " + " | ".join(row) + " |" for row in parsed["rows"]]
    return "\n".join([header, sep, *body])

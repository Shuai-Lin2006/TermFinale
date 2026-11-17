"""Scoped generation: slice page range first, then run the lecture pipeline."""
from __future__ import annotations

import tempfile
from pathlib import Path

from . import generate, page_policy, page_scope


class ScopedGenerationError(ValueError):
    pass


def generate_scoped(source: str | Path, page_spec: str, *, mode: str = "precise",
                    **kwargs) -> dict:
    source = Path(source)
    import pymupdf
    doc = pymupdf.open(str(source))
    try:
        total = len(doc)
    finally:
        doc.close()
    try:
        pages = page_scope.parse(page_spec, total)
    except page_scope.ScopeError as exc:
        raise ScopedGenerationError(str(exc)) from exc
    options = page_policy.options(len(pages))
    try:
        chosen = page_policy.choose(len(pages), mode)
    except ValueError as exc:
        raise ScopedGenerationError(str(exc)) from exc
    with tempfile.TemporaryDirectory(prefix="tf_scope_") as td:
        scoped = Path(td) / f"scoped_{source.stem}.pdf"
        info = page_scope.slice_pdf(source, scoped, page_spec)
        result = generate.generate_lecture(scoped, **kwargs)
    result = dict(result)
    result["scope"] = {"pages": pages, "page_count": len(pages),
                       "original_pages": total, "mode": chosen["mode"],
                       "estimate": options}
    return result


def plan_scoped(source: str | Path, page_spec: str = "all") -> dict:
    import pymupdf
    doc = pymupdf.open(str(source))
    try:
        total = len(doc)
    finally:
        doc.close()
    pages = page_scope.parse(page_spec, total)
    return {"pages": pages, "page_count": len(pages), "original_pages": total,
            "policy": page_policy.options(len(pages))}

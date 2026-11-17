"""Benchmark Docling structure against a plain PyMuPDF baseline."""
from __future__ import annotations
import json, sys
from pathlib import Path
import pymupdf


def main() -> None:
    pdf = Path(sys.argv[1]); docling_path = Path(sys.argv[2])
    d = json.loads(docling_path.read_text(encoding="utf-8"))
    doc_pages = d.get("pages") or []
    doc_chars = sum(len(b.get("text", "") or "") for p in doc_pages for b in (p.get("blocks") or []))
    doc_blocks = sum(len(p.get("blocks") or []) for p in doc_pages)
    doc_pics = sum(len(p.get("pictures") or []) for p in doc_pages)
    pdf_doc = pymupdf.open(str(pdf))
    chars = blocks = pics = 0
    for page in pdf_doc:
        chars += len(page.get_text("text"))
        blocks += len(page.get_text("blocks"))
        pics += len(page.get_images(full=True))
    pages = len(pdf_doc)
    out = {
        "pdf_pages": pages,
        "docling": {"pages": len(doc_pages), "blocks": doc_blocks, "chars": doc_chars, "pictures": doc_pics},
        "pymupdf": {"pages": pages, "blocks": blocks, "chars": chars, "pictures": pics},
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    Path("data/golden/parse_bench.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()

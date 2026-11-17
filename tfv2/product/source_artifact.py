"""Import a past-exam PDF as an artifact for the questions module."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from . import generate, source_pages
from .data_paths import ARTIFACT_ROOT


def create_exam_source(pdf_path: str | Path, *, title: str = "", ocr: bool = False) -> dict:
    pdf = Path(pdf_path)
    if not pdf.is_file():
        raise FileNotFoundError(pdf)
    aid = generate._new_id()
    out = ARTIFACT_ROOT / aid
    out.mkdir(parents=True, exist_ok=False)
    (out / "source").mkdir()
    copied = out / "source" / pdf.name
    shutil.copy2(pdf, copied)
    images = out / "source_assets"; images.mkdir()
    ledger = generate._ledger(copied, images)
    if ocr:
        generate._ocr_low_text(ledger, copied)
    source_pages.save_source_pages(out, ledger)
    sections = [{
        "id": "s1", "title": title or pdf.stem,
        "blocks": [{"id": "b1", "kind": "paragraph", "text": "",
                    "source_refs": [{"material": pdf.name, "page_start": 1, "page_end": ledger.page_count}]}],
    }]
    (out / "sections.json").write_text(json.dumps(sections, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "lecture.html").write_text("<html></html>", encoding="utf-8")
    manifest = {"artifact": aid, "chapter": title or pdf.stem, "page_count": ledger.page_count,
                "kind": "exam_source", "gate": {"passed": True, "issues": []}}
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"id": aid, "pages": ledger.page_count, "path": str(out)}

"""Parser adapter interface: Docling/MinerU/Marker plug into the same contract."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from tfv2.domain.page import PageLedger
from tfv2.ingest.docling_pages import pages_from_structure


class DocumentParser(Protocol):
    name: str

    def parse(self, source: dict | Path) -> PageLedger: ...


class DoclingStructureParser:
    name = "docling"

    def parse(self, source: dict | Path) -> PageLedger:
        if isinstance(source, Path):
            data = json.loads(source.read_text(encoding="utf-8"))
        else:
            data = source
        return pages_from_structure(data, material=str(data.get("material") or "docling"))

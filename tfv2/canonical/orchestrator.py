"""Canonical orchestrator: parse -> facts/plans, with a simple disk cache."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .model import CanonicalDocument
from .parsers import DocumentParser
from .pipeline import run_canonical


PIPELINE_VERSION = "v4-curate1"


class CanonicalOrchestrator:
    def __init__(self, parser: DocumentParser, cache_dir: str | Path | None = None):
        self.parser = parser
        self.cache_dir = Path(cache_dir) if cache_dir else None

    def _key(self, source: dict | Path) -> str:
        raw = (PIPELINE_VERSION + "|" + (json.dumps(source, sort_keys=True, ensure_ascii=False) if isinstance(source, dict) else str(source)))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def run(self, source: dict | Path, *, document_id: str = "canonical") -> CanonicalDocument:
        key = self._key(source)
        if self.cache_dir:
            cache_file = self.cache_dir / f"{key}.json"
            if cache_file.is_file():
                return CanonicalDocument.model_validate(json.loads(cache_file.read_text(encoding="utf-8")))
        ledger = self.parser.parse(source)
        doc = run_canonical(ledger, document_id=document_id)
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = self.cache_dir / f"{key}.json"
            cache_file.write_text(json.dumps(doc.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")
        return doc

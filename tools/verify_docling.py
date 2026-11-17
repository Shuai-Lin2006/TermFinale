"""Verify a Docling structure without model calls."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("structure")
    ap.add_argument("--pages", type=int, default=10)
    ap.add_argument("--min-chars", type=int, default=5000)
    ap.add_argument("--min-pictures", type=int, default=10)
    args = ap.parse_args()
    data = json.loads(Path(args.structure).read_text(encoding="utf-8"))
    pages = data.get("pages") or []
    checks = {
        "page_count": len(pages) == args.pages,
        "all_pages_have_blocks": all(p.get("blocks") for p in pages),
        "text_chars": sum(len(b.get("text", "") or "") for p in pages for b in (p.get("blocks") or [])) >= args.min_chars,
        "pictures": sum(len(p.get("pictures") or []) for p in pages) >= args.min_pictures,
        "provider": data.get("provider") == "docling",
    }
    out = {"passed": all(checks.values()), "checks": checks,
           "pages": len(pages), "pictures": sum(len(p.get("pictures") or []) for p in pages),
           "chars": sum(len(b.get("text", "") or "") for p in pages for b in (p.get("blocks") or []))}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    sys.exit(0 if out["passed"] else 1)


if __name__ == "__main__":
    main()

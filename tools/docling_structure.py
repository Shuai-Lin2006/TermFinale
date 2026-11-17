#!/usr/bin/env python3
"""CLI: PDF -> structure JSON using an environment that has Docling."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tfv2.ingest.docling_adapter import convert_pdf

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("out")
    args = ap.parse_args()
    data = convert_pdf(args.pdf, args.out)
    print(json.dumps({"ok": True, "pages": data["page_count"],
                      "blocks": sum(len(p["blocks"]) for p in data["pages"]),
                      "pictures": sum(len(p["pictures"]) for p in data["pages"])}))

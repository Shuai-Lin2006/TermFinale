"""One-chapter worker process.

The parent kills this process on timeout. Keeping generation in its own process
is required because Python threads cannot be force-stopped.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ap.add_argument("result")
    args = ap.parse_args()
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    from tfv2.product import generate
    from tfv2.llm import usage
    usage.reset()
    try:
        res = generate.generate_lecture(
            manifest["source_pdf"], title=manifest.get("title") or "章节讲义",
            course=manifest.get("course") or "课程", gen_lang=manifest.get("gen_lang") or "zh",
            illustrations=False,
        )
        quality = res.get("quality") or (res.get("artifact") or {}).get("quality") or {}
        Path(args.result).write_text(json.dumps({
            "artifact_id": res.get("id"),
            "gate_passed": bool(quality.get("gate_passed")),
            "quality": {"gate_passed": bool(quality.get("gate_passed")),
                        "content_passed": bool(quality.get("content_passed")),
                        "pdf_passed": bool(quality.get("pdf_passed"))},
            "usage": usage.snapshot(),
        }, ensure_ascii=False), encoding="utf-8")
        return 0
    except Exception as exc:
        Path(args.result).write_text(json.dumps({"error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False), encoding="utf-8")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

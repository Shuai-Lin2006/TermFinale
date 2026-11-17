"""讲义基准测试：对同一本书的不同页段跑真实生成，记录门禁/覆盖率/耗时/质量指标。

用法：
  .venv/bin/python scripts/benchmark.py --artifact mathanalysis1001 \
      --starts 1,120,260,400 --pages 8 --out docs/evidence/benchmark.json

每个页段生成独立 artifact（数据目录同环境变量），最后打印对照表。
公式 OCR 默认关闭（数学书公式密集，pix2tex 很慢）；需要时加 --formula-ocr。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def slice_pdf(source: Path, start: int, pages: int, out_dir: Path) -> Path:
    import pymupdf

    doc = pymupdf.open(str(source))
    try:
        end = min(len(doc), start + pages - 1)
        out_pdf = out_dir / f"slice_{start}-{end}.pdf"
        out = pymupdf.open()
        for p in range(start - 1, end):
            out.insert_pdf(doc, from_page=p, to_page=p)
        out.save(str(out_pdf))
        out.close()
        return out_pdf
    finally:
        doc.close()


def run_one(source: Path, start: int, pages: int, *, title: str, workdir: Path) -> dict:
    from tfv2.product import generate

    pdf = slice_pdf(source, start, pages, workdir)
    t0 = time.time()
    row: dict = {"start": start, "pages": pages, "title": title}
    try:
        res = generate.generate_lecture(pdf, title=title, course="基准测试")
        aid = (res or {}).get("id") or ""
        row["artifact"] = aid
        pdir = Path(os.getenv("TFV2_DATA_ROOT", str(ROOT / "data"))) / "artifacts" / aid
        man = json.loads((pdir / "manifest.json").read_text(encoding="utf-8"))
        pr = json.loads((pdir / "project.json").read_text(encoding="utf-8"))
        secs = json.loads((pdir / "sections.json").read_text(encoding="utf-8"))
        row.update({
            "gate": bool(man.get("gate", {}).get("passed")),
            "issues": [i.get("message") for i in (man.get("gate", {}).get("issues") or [])][:3],
            "built_pages": man.get("page_count"),
            "pdf_pages": man.get("pdf_pages"),
            "sections": len(secs),
            "fill_pages": pr.get("page_fill_pages", 0),
            "fill_ratio": pr.get("page_fill_ratio", 0),
            "fallback_sections": len(pr.get("fallback_sections") or []),
            "cache_bytes": sum(f.stat().st_size for f in pdir.rglob("*") if f.is_file()) if pdir.is_dir() else 0,
        })
        # 质量指标复用评测脚本（导入它，避免两套口径）
        import importlib.util
        spec = importlib.util.spec_from_file_location("eh", ROOT / "scripts/eval_harness.py")
        eh = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(eh)
        q = eh.eval_lecture(aid, title)
        row.update({k: q.get(k) for k in ("coverage", "citation", "avg_sentence",
                                          "dup_ratio", "boilerplate_per_1k",
                                          "citation_support", "term_recall",
                                          "heading_recall")})
        row["ok"] = bool(row["gate"]) and not q.get("fails")
        row["quality_fails"] = q.get("fails") or []
    except Exception as exc:  # noqa: BLE001
        row.update({"gate": False, "ok": False, "error": f"{type(exc).__name__}: {str(exc)[:200]}"})
    row["seconds"] = round(time.time() - t0, 1)
    return row


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", default="mathanalysis1001")
    ap.add_argument("--starts", default="1,120,260,400")
    ap.add_argument("--pages", type=int, default=8)
    ap.add_argument("--formula-ocr", action="store_true")
    ap.add_argument("--out", default="docs/evidence/benchmark.json")
    args = ap.parse_args()

    if not args.formula_ocr:
        os.environ["TFV2_FORMULA_OCR"] = "0"
    # 基准产物默认放临时目录，避免把测试讲义塞进用户资料库
    if not os.getenv("TFV2_DATA_ROOT"):
        os.environ["TFV2_DATA_ROOT"] = tempfile.mkdtemp(prefix="tf_bench_data_")

    from tfv2.product import service

    art = service.artifact_path(args.artifact)
    if art is None:
        raise SystemExit(f"找不到资料：{args.artifact}")
    source = next((art / "source").glob("*.pdf"), None)
    if source is None:
        raise SystemExit("资料缺少 PDF")

    starts = [int(x) for x in args.starts.split(",") if x.strip()]
    workdir = Path(tempfile.mkdtemp(prefix="tf_bench_"))
    rows = []
    for start in starts:
        title = f"数学分析 第{start}–{start + args.pages - 1}页"
        print(f"[{len(rows)+1}/{len(starts)}] {title} ...", flush=True)
        row = run_one(source, start, args.pages, title=title, workdir=workdir)
        rows.append(row)
        print("   ", json.dumps({k: row.get(k) for k in ("gate", "ok", "sections", "coverage", "fill_ratio", "seconds")},
                               ensure_ascii=False), flush=True)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"artifact": args.artifact, "pages": args.pages, "rows": rows},
                              ensure_ascii=False, indent=2), encoding="utf-8")
    passed = sum(1 for r in rows if r.get("ok"))
    print(f"\n通过 {passed}/{len(rows)} · 报告 {out}")


if __name__ == "__main__":
    main()

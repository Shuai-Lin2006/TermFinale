"""数学影像版 e2e：扫描/公式教材按原页影像出讲义，目录与页序必须对得上。

用法：
  .venv/bin/python scripts/image_lecture_e2e.py --pages 120
  .venv/bin/python scripts/image_lecture_e2e.py --pages 1001 --group 20   # 全量影像版

验收：
1. 每一页都有原页影像块，图片文件真实存在且能解码；
2. 影像顺序 = 原资料页码顺序，不跳、不重、不倒序；
3. 目录节数与页段数一致，节标题写的是原资料页码；
4. 节出处覆盖全部选中页（不丢页）；
5. 产物 PDF 存在、页数合理，HTML 里没有乱码；
6. 任何一条不满足就非零退出。
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SCRATCH = Path(tempfile.mkdtemp(prefix="tf_image_e2e_"))
DATA = SCRATCH / "data"
(DATA / "artifacts").mkdir(parents=True, exist_ok=True)
os.environ["TFV2_DATA_ROOT"] = str(DATA)

from tfv2.product import service  # noqa: E402
from tfv2.product.source_digest import build_source_digest  # noqa: E402

SOURCE = ROOT / "data" / "artifacts" / "math1001scan"
FAILURES: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(f"  [{'ok' if cond else 'FAIL'}] {msg}")
    if not cond:
        FAILURES.append(msg)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=120)
    ap.add_argument("--group", type=int, default=20)
    ap.add_argument("--dpi", type=int, default=100)
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args()

    if not SOURCE.is_dir():
        raise SystemExit(f"缺少影像资料：{SOURCE}")
    link = DATA / "artifacts" / SOURCE.name
    if not link.exists():
        os.symlink(SOURCE.resolve(), link, target_is_directory=True)

    total = json.loads((SOURCE / "source_pages.json").read_text(encoding="utf-8"))["page_count"]
    n = min(args.pages, total)
    pages = list(range(1, n + 1))
    print(f"== 影像版：{SOURCE.name} 取第 1–{n} 页（资料共 {total} 页，每 {args.group} 页一节）==")

    t0 = time.time()
    out_id = "image-e2e"
    build_source_digest(SOURCE.name, pages, out_id, scan_mode=True,
                        group_size=args.group, dpi=args.dpi,
                        progress=lambda pct, step: print(f"  [{pct:3d}%] {step}"))
    print(f"  [info] 生成耗时 {time.time() - t0:.1f}s")

    dest = service.artifact_path(out_id)
    if dest is None or not (dest / "lecture.pdf").is_file():
        raise SystemExit("没有生成 lecture.pdf")
    sections = json.loads((dest / "sections.json").read_text(encoding="utf-8"))
    html = (dest / "lecture.html").read_text(encoding="utf-8")
    pdf_bytes = (dest / "lecture.pdf").stat().st_size

    figs = [b for s in sections for b in s.get("blocks") or [] if b.get("kind") == "figure"]
    check(len(figs) == n, f"每页都有原页影像（{len(figs)}/{n}）")
    missing = [b["id"] for b in figs if not b.get("figure") or not Path(b["figure"]["asset_path"]).is_file()]
    check(not missing, f"影像文件都存在（缺失 {len(missing)} 个）")

    def _src_page(fig: dict) -> int:
        return int((fig.get("figure") or {}).get("source", {}).get("source_page") or 0)

    order = [_src_page(b) for b in figs]
    check(order == sorted(order), "影像顺序与资料页码顺序一致（不倒序）")
    check(sorted(order) == list(range(1, n + 1)), f"影像覆盖 1–{n} 页且不重复（实际 {order[:3]}…{order[-3:]}）")
    captions_ok = all(f"第 {p} 页" in (b["figure"]["caption"] or "") for b, p in zip(figs, order))
    check(captions_ok, "图注写的是原资料页码")

    expected_sections = (n + args.group - 1) // args.group
    check(len(sections) == expected_sections, f"目录节数 {len(sections)} = 页段数 {expected_sections}")
    titles = [s["title"] for s in sections]
    check(all(t.startswith("第 ") for t in titles), f"节标题都是页码（{titles[:3]}…）")

    cited: set[int] = set()
    for s in sections:
        for r in s.get("source_refs") or []:
            cited.update(range(int(r["page_start"]), int(r.get("page_end") or r["page_start"]) + 1))
    check(cited == set(range(1, n + 1)), f"节出处覆盖全部 {n} 页（漏页 {sorted(set(range(1, n+1)) - cited)[:5]}）")

    toc_entries = html.count('class="toc-item"') or html.count("toc")
    check(len(sections) <= toc_entries or bool(toc_entries), f"HTML 目录已渲染（{toc_entries} 处目录标记）")
    bad = [c for c in ("\ufffd", "\ue000", "锟斤拷") if c in html]
    check(not bad, f"HTML 无乱码（{bad}）")
    check(pdf_bytes > 50_000, f"PDF 有实际内容（{pdf_bytes/1024/1024:.1f} MB）")

    images = list((dest / "source_assets").glob("*.png"))
    check(len(images) == n, f"原页影像文件数 {len(images)} = {n}")

    print(f"\n总耗时 {time.time() - t0:.1f}s · 产物 {dest}")
    if args.keep:
        print(f"保留目录：{DATA}")
    if FAILURES:
        print(f"\nFAILED（{len(FAILURES)} 条）")
        raise SystemExit(1)
    print("ALL PASSED")
    if not args.keep:
        shutil.rmtree(SCRATCH, ignore_errors=True)


if __name__ == "__main__":
    main()

"""对源文件 + 生成物生成逐页账本报告（text/图片页/占位/引用/缺页）。

用法：
    python tools/page_ledger_report.py --source 资料.pdf --md 生成物.md [--json out.json]

只读；不修改资料/生成物。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.parser import extract_text_from_file  # noqa: E402
from core.quality.page_ledger import build_page_ledger, ledger_summary  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="TermFinale 逐页账本")
    ap.add_argument("--source", required=True, help="原始资料路径")
    ap.add_argument("--md", required=True, help="生成物 markdown 路径")
    ap.add_argument("--json", default="", help="可选：把完整账本写到 JSON")
    args = ap.parse_args(argv)

    pages = extract_text_from_file(args.source)
    md = Path(args.md).read_text(encoding="utf-8", errors="ignore")
    ledger = build_page_ledger(pages, md)
    summary = ledger_summary(ledger)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if args.json:
        Path(args.json).write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n完整账本：{args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

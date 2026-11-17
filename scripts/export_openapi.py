"""导出 API 文档：docs/openapi.json + docs/API.md（接口清单，供外部集成/审查）。

用法：.venv/bin/python scripts/export_openapi.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    import sys

    sys.path.insert(0, str(ROOT))
    from tfv2.api.product_app import app

    spec = app.openapi()
    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    (docs / "openapi.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")

    rows = ["# TermFinale HTTP API", "",
            f"共 {len(spec.get('paths') or {})} 个路径。自动生成：`python scripts/export_openapi.py`。", "",
            "| 方法 | 路径 | 说明 |", "|---|---|---|"]
    for path, item in sorted((spec.get("paths") or {}).items()):
        for method, op in sorted(item.items()):
            if method.lower() not in ("get", "post", "put", "delete", "patch"):
                continue
            summary = str(op.get("summary") or op.get("operationId") or "").replace("|", "\\|")
            rows.append(f"| {method.upper()} | `{path}` | {summary} |")
    (docs / "API.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"paths={len(spec.get('paths') or {})} -> docs/openapi.json, docs/API.md")


if __name__ == "__main__":
    main()

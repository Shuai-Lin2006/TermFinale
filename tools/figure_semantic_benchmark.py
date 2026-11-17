"""语义契约基准：域 + labels + 尺寸 + 失败关闭；不冒充 VLM 视觉核对。"""
from __future__ import annotations
import json
from pathlib import Path
from PIL import Image
from tfv2.render import figure_compiler as fc

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "evidence" / "figure_semantic_benchmark.json"

CASES = [
    ("circuit-labels", "电路", {"kind": "circuit", "components": [
        {"type": "battery", "label": "U", "value": "12V"},
        {"type": "resistor", "label": "R", "value": "2Ω"}]},
     "circuit", ["U", "12V", "R", "2Ω"]),
    ("parallel-labels", "电路", {"kind": "circuit", "topology": "parallel", "branches": [
        {"type": "resistor", "label": "R1", "value": "2Ω"},
        {"type": "capacitor", "label": "C", "value": "1μF"}]},
     "circuit", ["R1", "2Ω", "C", "1μF"]),
    ("force-labels", "物理", {"kind": "force", "forces": [
        {"label": "F", "angle": 30}, {"label": "N", "angle": 90}]}, "physics", ["F", "N"]),
    ("flow-labels", "计算机", {"kind": "flow", "nodes": [
        {"id": "a", "label": "输入"}, {"id": "b", "label": "输出"}],
        "edges": [{"from": "a", "to": "b"}]}, "computing", ["输入", "输出"]),
    ("map-labels", "地理", {"kind": "map", "points": [
        {"x": 0, "y": 0, "label": "A"}, {"x": 1, "y": 1, "label": "B"}]}, "map", ["A", "B"]),
    ("timeline-labels", "历史", {"kind": "timeline", "events": [
        {"date": "1900", "label": "事件"}]}, "timeline", ["1900", "事件"]),
    ("3d-labels", "物理", {"kind": "3d", "objects": [
        {"type": "box", "label": "m"}, {"type": "arrow", "label": "F", "dx": 1}]}, "3d", ["m", "F"]),
    ("chem-molecule", "化学", {"kind": "chem", "smiles": "CCO"}, "chemistry", []),
    ("unsupported", "其他", {"kind": "qwerty"}, None, []),
]


def main() -> None:
    rows = []
    for name, subject, spec, domain, labels in CASES:
        out = ROOT / "data" / "figure_semantic" / f"{name}.png"
        res = fc.compile_figure(spec, subject=subject, out_path=out)
        got_labels = (res or {}).get("labels") or []
        ok = (res is None and domain is None) or (res is not None and res.get("domain") == domain)
        if res and out.is_file():
            try:
                with Image.open(out) as im:
                    ok = ok and im.width > 100 and im.height > 100
            except Exception:
                ok = False
        missing = [x for x in labels if x not in got_labels]
        ok = ok and not missing
        rows.append({"case": name, "domain": (res or {}).get("domain"), "expected_domain": domain,
                     "labels": got_labels, "missing": missing, "ok": ok})
    json.dump(rows, OUT.open("w", encoding="utf-8"), ensure_ascii=False, indent=2)
    for r in rows:
        print(f"{'PASS' if r['ok'] else 'FAIL'} {r['case']:20} domain={r['domain']} missing={r['missing']}")
    passed = sum(1 for r in rows if r["ok"])
    print(f"passed={passed}/{len(rows)} -> {OUT}")
    if passed != len(rows):
        raise SystemExit(1)


if __name__ == "__main__":
    main()

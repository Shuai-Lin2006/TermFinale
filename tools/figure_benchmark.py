"""跨学科图编译器基准：生成、校验、统计通过率。"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image
from tfv2.render import figure_compiler as fc

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "evidence" / "figure_benchmark.json"
IMG = ROOT / "docs" / "evidence" / "v3_series_diagram.png"

CASES = [
    ("circuit-series", "电路", {"kind": "circuit", "components": [
        {"type": "battery", "label": "U", "value": "12V"}, {"type": "resistor", "label": "R", "value": "2Ω"},
        {"type": "capacitor", "label": "C", "value": "1μF"}, {"type": "inductor", "label": "L", "value": "1H"}]}, "circuit"),
    ("circuit-parallel", "电路", {"kind": "circuit", "topology": "parallel", "branches": [
        {"type": "resistor", "label": "R1", "value": "2Ω"}, {"type": "capacitor", "label": "C", "value": "1μF"}]}, "circuit"),
    ("circuit-graph-netlist", "电路", {"kind": "circuit", "nodes": [
        {"id": "u", "type": "battery", "x": 80, "y": 210, "label": "U", "value": "12V"},
        {"id": "r", "type": "resistor", "x": 320, "y": 80, "label": "R", "value": "2Ω"},
        {"id": "c", "type": "capacitor", "x": 560, "y": 210, "label": "C", "value": "1μF"}],
        "edges": [["u", "r"], ["r", "c"], ["c", "u"]]}, "circuit"),
    ("physics-3d", "物理", {"kind": "3d", "objects": [
        {"type": "box", "x": 0, "y": 0, "z": 0, "w": 1, "h": 1, "d": 1, "label": "m"},
        {"type": "arrow", "x": 0, "y": 0, "z": 1, "dx": 1, "dy": 0, "dz": 0, "label": "F"}],
        "camera": {"elev": 25, "azim": 35}}, "3d"),
    ("spice", "电路", {"kind": "spice", "netlist": "V1 1 0 12\nR1 1 2 2\nC1 2 0 1e-6"}, "circuit"),
    ("mujoco", "物理", {"kind": "mujoco", "position": [0, 0, 1.2], "duration": 0.3}, "mujoco"),
    ("physics3d", "物理", {"kind": "physics3d", "position": [0, 0, 1], "velocity": [1, 0, 4],
                          "duration": 1.2}, "physics3d"),
    ("physics-force", "物理", {"kind": "force", "forces": [{"label": "F", "angle": 30}, {"label": "N", "angle": 90}]}, "physics"),
    ("math-points", "高等数学", {"kind": "math", "points": [[0, 0], [1, 1], [2, 4]]}, "math"),
    ("math-symbolic", "高等数学", {"kind": "math", "expression": "x**2"}, "math"),
    ("geometry", "高等数学", {"kind": "geometry", "elements": [
        {"type": "circle", "x": 360, "y": 210, "r": 80}, {"type": "line", "x1": 100, "y1": 350, "x2": 620, "y2": 350}]}, "math"),
    ("chem-molecule", "化学", {"kind": "chem", "smiles": "CCO"}, "chemistry"),
    ("chem-reaction", "化学", {"kind": "reaction", "reaction": "CCO>>CC=O"}, "chemistry"),
    ("chem-sequence", "化学", {"kind": "reaction-sequence", "steps": ["CCO>>CC=O", "CC=O>>CC(=O)O"]}, "chemistry"),
    ("cs-flow", "计算机", {"kind": "flow", "nodes": [{"id": "a", "label": "输入"}, {"id": "b", "label": "处理"}],
                          "edges": [{"from": "a", "to": "b"}]}, "computing"),
    ("econ-chart", "经济", {"kind": "bar", "labels": ["Q1", "Q2"], "values": [10, 20]}, "chart"),
    ("stats-line", "统计", {"kind": "line", "labels": ["A", "B", "C"], "values": [1, 3, 2]}, "chart"),
    ("table-med", "医学", {"kind": "table", "headers": ["指标", "值"], "rows": [["HR", "72"]]}, "table"),
    ("timeline-history", "历史", {"kind": "timeline", "events": [{"date": "1900", "label": "事件"}]}, "timeline"),
    ("map-geo", "地理", {"kind": "map", "points": [{"x": 0, "y": 0, "label": "A"}, {"x": 1, "y": 1, "label": "B"}]}, "map"),
    ("concept-liberal", "文科", {"kind": "concept", "nodes": [{"id": "a", "label": "概念"}], "edges": []}, "concept"),
    ("source-auto-page", "医学", {"kind": "source", "artifact_id": "v2_circuit_full", "page": 6}, "source"),
    ("source-med", "医学", {"kind": "source", "path": str(IMG)}, "source"),
    ("medical-circuit-fail", "医学", {"kind": "circuit", "components": [{"type": "battery"}]}, None),
    ("unsupported", "其他", {"kind": "qwerty"}, None),
]


def main() -> None:
    rows = []
    for name, subject, spec, expected in CASES:
        out = ROOT / "data" / "figure_bench" / f"{name}.png"
        try:
            res = fc.compile_figure(spec, subject=subject, out_path=out)
        except Exception as exc:
            res = None; err = str(exc)
        else:
            err = ""
        ok = (res is None and expected is None) or (res is not None and expected is not None and res.get("domain") == expected)
        if res and out.is_file():
            try:
                with Image.open(out) as im: size = im.size
            except Exception:
                size = None; ok = False
        else:
            size = None
        rows.append({"case": name, "subject": subject, "expected": expected,
                     "got": (res or {}).get("domain"), "engine": (res or {}).get("engine"),
                     "size": size, "ok": ok, "error": err})
    json.dump(rows, OUT.open("w", encoding="utf-8"), ensure_ascii=False, indent=2)
    passed = sum(1 for r in rows if r["ok"])
    for r in rows:
        print(f"{'PASS' if r['ok'] else 'FAIL'} {r['case']:22} expected={r['expected']} got={r['got']} {r['size']} {r['error']}")
    print(f"passed={passed}/{len(rows)} -> {OUT}")
    if passed != len(rows):
        raise SystemExit(1)


if __name__ == "__main__":
    main()

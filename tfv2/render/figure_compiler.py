"""全学科图编译器：领域 spec -> 确定性渲染 -> 校验；不支持的域返回 None。"""
from __future__ import annotations

from pathlib import Path

from tfv2.render import atlas, diagram, figure_router, figure_spec, three_d

DOMAINS = {
    "circuit": {"subjects": {"电路"}, "engine": "structured-circuit"},
    "physics": {"subjects": {"物理"}, "engine": "structured-force"},
    "math": {"subjects": {"高等数学"}, "engine": "matplotlib-points"},
    "chemistry": {"subjects": {"化学"}, "engine": "rdkit-smiles"},
    "computing": {"subjects": {"计算机"}, "engine": "flow-pillow"},
    "chart": {"subjects": {"经济", "统计", "医学", "生物", "文科"}, "engine": "matplotlib-chart"},
    "concept": {"subjects": {"文科", "其他"}, "engine": "flow-pillow"},
    "table": {"subjects": {"全部"}, "engine": "table-pillow"},
    "timeline": {"subjects": {"历史", "文科"}, "engine": "timeline-pillow"},
    "map": {"subjects": {"地理", "历史"}, "engine": "map-scatter"},
    "source": {"subjects": {"医学", "生物", "地理", "历史"}, "engine": "source-only"},
    "3d": {"subjects": {"物理", "高等数学", "工程"}, "engine": "matplotlib-3d"},
    "physics3d": {"subjects": {"物理"}, "engine": "physics3d-euler"},
    "mujoco": {"subjects": {"物理", "工程"}, "engine": "mujoco"},
    "atlas": {"subjects": {"医学", "生物"}, "engine": "atlas-source-only"},
    "geojson": {"subjects": {"地理", "历史"}, "engine": "geojson-matplotlib"},
}
NO_GENERATE = {"医学", "生物", "地理", "历史"}




def _parallel_circuit(spec: dict, out: Path) -> dict | None:
    branches = spec.get("branches") or []
    if not isinstance(branches, list) or not branches:
        return None
    elements = [{"type": "battery", "x": 80, "y": 210, "length": 70, "orientation": "v",
                 "label": str(spec.get("source_label") or "U"), "value": str(spec.get("source_value") or "")},
                {"type": "wire", "points": [[80, 175], [80, 80], [640, 80]]},
                {"type": "wire", "points": [[80, 245], [80, 340], [640, 340]]}]
    xs = [240 + int(360 * (i + 0.5) / len(branches)) for i in range(len(branches))]
    for x, br in zip(xs, branches):
        typ = str(br.get("type") or "resistor")
        if typ not in ("resistor", "capacitor", "inductor", "lamp"):
            continue
        elements.append({"type": typ, "x": x, "y": 210, "length": 70, "orientation": "v",
                         "label": str(br.get("label") or ""), "value": str(br.get("value") or "")})
        elements.append({"type": "wire", "points": [[x, 80], [x, 175]]})
        elements.append({"type": "wire", "points": [[x, 245], [x, 340]]})
    elements.append({"type": "wire", "points": [[640, 80], [640, 340]]})
    return diagram.render_spec({"kind": "circuit", "topology": "parallel", "elements": elements}, out)


def _force_template(spec: dict, out: Path) -> dict | None:
    forces = spec.get("forces")
    if not isinstance(forces, list) or not forces:
        return None
    try:
        from PIL import Image, ImageDraw, ImageFont
        import math
    except Exception:
        return None
    W, H, S = 720, 420, 2
    img = Image.new("RGB", (W * S, H * S), (255, 255, 255)); d = ImageDraw.Draw(img)
    try: font = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 28)
    except Exception: font = ImageFont.load_default()
    # 斜面
    d.line((80 * S, 340 * S, 640 * S, 160 * S), fill=(60, 68, 76), width=3)
    d.line((80 * S, 340 * S, 640 * S, 340 * S), fill=(160, 168, 176), width=2)
    cx, cy = 360 * S, 250 * S
    d.rectangle((cx - 60, cy - 35, cx + 60, cy + 35), outline=(40, 70, 90), width=3, fill=(245, 250, 252))
    d.text((cx, cy), "m", fill=(24, 28, 32), font=font, anchor="mm")
    for f in forces:
        try:
            ang = math.radians(float(f.get("angle", 0)))
        except Exception:
            ang = 0
        length = 110
        ex, ey = cx + length * math.cos(ang), cy - length * math.sin(ang)
        d.line((cx, cy, ex, ey), fill=(15, 118, 110), width=3)
        for sign in (-0.5, 0.5):
            d.line((ex, ey, ex - 14 * math.cos(ang + sign), ey + 14 * math.sin(ang + sign)), fill=(15, 118, 110), width=3)
        d.text((ex + 8, ey - 8), str(f.get("label") or ""), fill=(15, 118, 110), font=font)
    out.parent.mkdir(parents=True, exist_ok=True); img.save(out)
    return {"path": str(out), "layout": "force", "elements": len(forces), "engine": "force-template"}


def _symbolic_math(spec: dict, out: Path) -> dict | None:
    expr = str(spec.get("expression") or "").strip()
    if not expr:
        return None
    try:
        import sympy as sp
        import matplotlib
        matplotlib.use("Agg")
        matplotlib.rcParams["font.sans-serif"] = ["PingFang SC", "Arial Unicode MS", "DejaVu Sans"]
        matplotlib.rcParams["axes.unicode_minus"] = False
        import matplotlib.pyplot as plt
        import numpy as np
        x = sp.symbols("x")
        f = sp.sympify(expr)
        xs = np.linspace(float(spec.get("x_min", -5)), float(spec.get("x_max", 5)), 400)
        fn = sp.lambdify(x, f, "numpy")
        ys = fn(xs)
        fig, ax = plt.subplots(figsize=(7.2, 4.2), dpi=160)
        ax.plot(xs, ys, color="#245c73", linewidth=2)
        ax.axhline(0, color="#8a949e"); ax.axvline(0, color="#8a949e")
        ax.grid(True, linestyle=":", alpha=0.5); ax.set_title(expr)
        fig.tight_layout(); out.parent.mkdir(parents=True, exist_ok=True); fig.savefig(out); plt.close(fig)
        return {"path": str(out), "layout": "math", "elements": 1, "engine": "sympy-matplotlib"}
    except Exception:
        return None


def _reaction(spec: dict, out: Path) -> dict | None:
    reaction = str(spec.get("reaction") or spec.get("reaction_smiles") or "").strip()
    if not reaction or ">>" not in reaction:
        return None
    try:
        from rdkit import Chem
        from rdkit.Chem import Draw, AllChem
        rxn = AllChem.ReactionFromSmarts(reaction)
        img = Draw.ReactionToImage(rxn, subImgSize=(320, 240))
        out.parent.mkdir(parents=True, exist_ok=True); img.save(out)
        return {"path": str(out), "layout": "reaction", "elements": 1, "engine": "rdkit-reaction"}
    except Exception:
        return None



def _geometry(spec: dict, out: Path) -> dict | None:
    elements = spec.get("elements")
    if not isinstance(elements, list) or not elements:
        return None
    try:
        return diagram.render_spec({"kind": "geometry", "elements": elements}, out)
    except Exception:
        return None


def _table(spec: dict, out: Path) -> dict | None:
    rows = spec.get("rows")
    headers = spec.get("headers") or []
    if not isinstance(rows, list) or not rows:
        return None
    try:
        from PIL import Image, ImageDraw, ImageFont
        import textwrap
        W, H = 1200, 120 + 90 * (len(rows) + 1)
        img = Image.new("RGB", (W, H), (255, 255, 255)); d = ImageDraw.Draw(img)
        try: font = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 24)
        except Exception: font = ImageFont.load_default()
        cols = max(len(headers), max(len(r) for r in rows))
        cw = (W - 80) // cols
        y = 40
        def line(row, bold=False):
            nonlocal y
            for i, cell in enumerate(row):
                d.rectangle((40 + i * cw, y, 40 + (i + 1) * cw, y + 72), outline=(210, 214, 220), width=1)
                txt = textwrap.shorten(str(cell), width=max(4, cw // 16), placeholder="…")
                d.text((52 + i * cw, y + 22), txt, fill=(24, 28, 32), font=font)
            y += 72
        if headers: line(headers, True)
        for r in rows: line(list(r) + [""] * (cols - len(r)))
        out.parent.mkdir(parents=True, exist_ok=True); img.save(out)
        return {"path": str(out), "layout": "table", "elements": len(rows), "engine": "table-pillow"}
    except Exception:
        return None


def _timeline(spec: dict, out: Path) -> dict | None:
    events = spec.get("events")
    if not isinstance(events, list) or not events:
        return None
    try:
        from PIL import Image, ImageDraw, ImageFont
        W, H = 1200, 360
        img = Image.new("RGB", (W, H), (255, 255, 255)); d = ImageDraw.Draw(img)
        try: font = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 22)
        except Exception: font = ImageFont.load_default()
        y = 180; d.line((80, y, W - 80, y), fill=(40, 70, 90), width=3)
        n = len(events)
        for i, ev in enumerate(events):
            x = 120 + (W - 240) * i / max(1, n - 1)
            d.ellipse((x - 8, y - 8, x + 8, y + 8), fill=(15, 118, 110))
            d.line((x, y, x, y - 50 if i % 2 == 0 else y + 50), fill=(120, 128, 136), width=2)
            d.text((x, y - 80 if i % 2 == 0 else y + 60), str(ev.get("date") or ""), fill=(80, 90, 100), font=font, anchor="mm")
            d.text((x, y - 110 if i % 2 == 0 else y + 90), str(ev.get("label") or ""), fill=(24, 28, 32), font=font, anchor="mm")
        out.parent.mkdir(parents=True, exist_ok=True); img.save(out)
        return {"path": str(out), "layout": "timeline", "elements": n, "engine": "timeline-pillow"}
    except Exception:
        return None


def _schematic_map(spec: dict, out: Path) -> dict | None:
    points = spec.get("points")
    if not isinstance(points, list) or not points:
        return None
    try:
        import matplotlib
        matplotlib.use("Agg")
        matplotlib.rcParams["font.sans-serif"] = ["PingFang SC", "Arial Unicode MS", "DejaVu Sans"]
        matplotlib.rcParams["axes.unicode_minus"] = False
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(7.2, 4.8), dpi=160)
        xs = [float(p.get("x", 0)) for p in points]
        ys = [float(p.get("y", 0)) for p in points]
        ax.scatter(xs, ys, color="#245c73", s=40)
        for p in points:
            if p.get("label"):
                ax.annotate(str(p["label"]), (float(p.get("x", 0)), float(p.get("y", 0))), fontsize=8)
        ax.set_title(str(spec.get("title") or "示意地图（非精确地理边界）"))
        ax.grid(True, linestyle=":", alpha=0.4); fig.tight_layout()
        out.parent.mkdir(parents=True, exist_ok=True); fig.savefig(out); plt.close(fig)
        return {"path": str(out), "layout": "schematic-map", "elements": len(points), "engine": "map-scatter"}
    except Exception:
        return None



def _netlist_series(spec: dict, out: Path) -> dict | None:
    comps = spec.get("components")
    if not isinstance(comps, list) or not comps:
        return None
    elements = []
    for c in comps:
        typ = str(c.get("type") or "")
        if typ not in ("battery", "resistor", "capacitor", "inductor", "switch", "lamp"):
            continue
        elements.append({"type": typ, "label": str(c.get("label") or ""), "value": str(c.get("value") or "")})
    if not any(e["type"] == "battery" for e in elements):
        return None
    try:
        return diagram.render_spec({"kind": "circuit", "topology": "series", "elements": elements}, out)
    except Exception:
        return None


def _reaction_sequence(spec: dict, out: Path) -> dict | None:
    steps = spec.get("steps")
    if not isinstance(steps, list) or not steps:
        return None
    try:
        from rdkit.Chem import Draw, AllChem
        from PIL import Image, ImageDraw, ImageFont
        imgs = []
        for st in steps:
            rxn = AllChem.ReactionFromSmarts(str(st))
            imgs.append(Draw.ReactionToImage(rxn, subImgSize=(420, 220)))
        W = max(i.width for i in imgs); H = sum(i.height + 40 for i in imgs)
        canvas = Image.new("RGB", (W, H), (255, 255, 255)); d = ImageDraw.Draw(canvas)
        try: font = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 24)
        except Exception: font = ImageFont.load_default()
        y = 10
        for i, im in enumerate(imgs):
            d.text((10, y), f"Step {i+1}", fill=(24, 28, 32), font=font)
            canvas.paste(im, (0, y + 28))
            if i < len(imgs) - 1:
                ay = y + 28 + im.height + 4
                d.line((W // 2, ay, W // 2, ay + 20), fill=(15, 118, 110), width=3)
                d.polygon([(W // 2, ay + 28), (W // 2 - 6, ay + 18), (W // 2 + 6, ay + 18)], fill=(15, 118, 110))
            y += im.height + 40
        out.parent.mkdir(parents=True, exist_ok=True); canvas.save(out)
        return {"path": str(out), "layout": "reaction-sequence", "elements": len(steps), "engine": "rdkit-reaction-sequence"}
    except Exception:
        return None


def _source_image(spec: dict, out: Path) -> dict | None:
    path = str(spec.get("path") or spec.get("source_path") or "")
    if not path and spec.get("artifact_id"):
        try:
            from tfv2.product import service
            a = service.get_artifact(str(spec["artifact_id"])) or {}
            page = int(spec.get("page") or 0)
            for fig in a.get("figure_list") or []:
                pages = [int(x) for x in (fig.get("source_pages") or [])]
                if (not page or page in pages) and fig.get("asset_exists"):
                    base = service.artifact_path(str(spec["artifact_id"]))
                    if base:
                        path = str(base / str(fig.get("asset_path") or ""))
                        spec = {**spec, "page": page or (pages[0] if pages else None)}
                        break
        except Exception:
            path = ""
    if not path:
        return None
    try:
        from shutil import copyfile
        from PIL import Image
        src = Path(path)
        if not src.is_file(): return None
        with Image.open(src) as im:
            width, height = im.size
            im.verify()
        out.parent.mkdir(parents=True, exist_ok=True); copyfile(src, out)
        if spec.get("crop", True):
            try:
                from PIL import ImageChops
                with Image.open(out) as im2:
                    rgb = im2.convert("RGB")
                    bg = Image.new("RGB", rgb.size, rgb.getpixel((0, 0)))
                    bbox = ImageChops.difference(rgb, bg).getbbox()
                    if bbox:
                        pad = 18
                        x0, y0, x1, y1 = bbox
                        x0, y0 = max(0, x0 - pad), max(0, y0 - pad)
                        x1, y1 = min(rgb.width, x1 + pad), min(rgb.height, y1 + pad)
                        if (x1 - x0) > rgb.width * 0.4 and (y1 - y0) > rgb.height * 0.4:
                            rgb.crop((x0, y0, x1, y1)).save(out)
                            width, height = x1 - x0, y1 - y0
            except Exception:
                pass
        return {"path": str(out), "layout": "source", "elements": 1, "engine": "source-only",
                "width": width, "height": height, "source_note": "资料原图；不生成、不重绘，仅裁掉空白边"}
    except Exception:
        return None



def _netlist_graph(spec: dict, out: Path) -> dict | None:
    nodes = spec.get("nodes")
    edges = spec.get("edges") or []
    if not isinstance(nodes, list) or not nodes:
        return None
    by_id = {}
    elements = []
    for n in nodes:
        if not isinstance(n, dict):
            continue
        nid = str(n.get("id") or len(by_id))
        by_id[nid] = n
        typ = str(n.get("type") or "node")
        x, y = float(n.get("x", 120 + 80 * len(by_id))), float(n.get("y", 210))
        if typ in ("battery", "resistor", "capacitor", "inductor", "switch", "lamp"):
            elements.append({"type": typ, "x": x, "y": y, "length": float(n.get("length", 80)),
                             "orientation": str(n.get("orientation") or "h"),
                             "label": str(n.get("label") or ""), "value": str(n.get("value") or "")})
        elif typ in ("node", "junction"):
            elements.append({"type": "node", "x": x, "y": y})
        elif typ in ("label", "text"):
            elements.append({"type": "label", "x": x, "y": y, "label": str(n.get("label") or "")})
    for e in edges:
        if isinstance(e, (list, tuple)) and len(e) >= 2:
            a, b = str(e[0]), str(e[1])
        elif isinstance(e, dict):
            a, b = str(e.get("from") or e.get("a") or ""), str(e.get("to") or e.get("b") or "")
        else:
            continue
        if a not in by_id or b not in by_id:
            continue
        x1, y1 = float(by_id[a].get("x", 0)), float(by_id[a].get("y", 0))
        x2, y2 = float(by_id[b].get("x", 0)), float(by_id[b].get("y", 0))
        if abs(x1 - x2) < 1 or abs(y1 - y2) < 1:
            pts = [[x1, y1], [x2, y2]]
        else:
            mx = (x1 + x2) / 2
            pts = [[x1, y1], [mx, y1], [mx, y2], [x2, y2]]
        elements.append({"type": "wire", "points": pts})
    if not elements:
        return None
    try:
        return diagram.render_spec({"kind": "circuit", "topology": "netlist", "elements": elements}, out)
    except Exception:
        return None



def _spice_circuit(spec: dict, out: Path) -> dict | None:
    net = str(spec.get("netlist") or spec.get("spice") or "").strip()
    if not net:
        return None
    try:
        import tempfile
        from lcapy import Circuit
        with tempfile.NamedTemporaryFile("w", suffix=".net", delete=False) as fh:
            fh.write(net + "\n"); path = fh.name
        Circuit(path)  # lcapy 校验网表/元件
        nodes, edges = [], []
        mapping = {"R": "resistor", "C": "capacitor", "L": "inductor", "V": "battery", "I": "battery", "S": "switch"}
        for line in net.replace(";", "\n").splitlines():
            parts = line.split()
            if len(parts) < 3 or parts[0].startswith(("*", ".", "#")):
                continue
            name = parts[0]; typ = mapping.get(name[0].upper())
            if not typ:
                continue
            n1, n2 = parts[1], parts[2]
            val = parts[3] if len(parts) > 3 else ""
            nodes.append({"id": name, "type": typ, "label": name, "value": val})
            edges += [[name, n1], [name, n2]]
        # 合并同名节点
        existing = {str(n["id"]) for n in nodes}
        for line in net.replace(";", "\n").splitlines():
            parts = line.split()
            if len(parts) >= 3 and not parts[0].startswith(("*", ".", "#")):
                for nid in (parts[1], parts[2]):
                    if nid not in existing:
                        nodes.append({"id": nid, "type": "node"}); existing.add(nid)
        if not nodes:
            return None
        return _netlist_graph({"nodes": nodes, "edges": edges}, out) | {"engine": "lcapy-spice"} if _netlist_graph({"nodes": nodes, "edges": edges}, out) else None
    except Exception:
        return None



def _geojson(spec: dict, out: Path) -> dict | None:
    path = str(spec.get("path") or "")
    if not path or not Path(path).is_file():
        return None
    try:
        import json
        import matplotlib
        matplotlib.use("Agg")
        matplotlib.rcParams["font.sans-serif"] = ["STHeiti Light", "Arial Unicode MS", "DejaVu Sans"]
        import matplotlib.pyplot as plt
        from matplotlib.patches import Polygon
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        fig, ax = plt.subplots(figsize=(7.2, 5), dpi=160)
        def draw(geom):
            if not geom: return
            if geom.get("type") == "Polygon":
                for ring in geom["coordinates"]:
                    ax.add_patch(Polygon(ring, closed=True, fill=True, alpha=.35, edgecolor="#245c73"))
            elif geom.get("type") == "MultiPolygon":
                for poly in geom["coordinates"]:
                    for ring in poly:
                        ax.add_patch(Polygon(ring, closed=True, fill=True, alpha=.35, edgecolor="#245c73"))
        if data.get("type") == "FeatureCollection":
            for f in data.get("features") or []: draw(f.get("geometry"))
        elif data.get("type") == "Feature":
            draw(data.get("geometry"))
        else:
            draw(data)
        ax.set_aspect("equal"); ax.grid(alpha=.2); ax.set_title(str(spec.get("title") or "GeoJSON"))
        fig.tight_layout(); out.parent.mkdir(parents=True, exist_ok=True); fig.savefig(out); plt.close(fig)
        return {"path": str(out), "layout": "geojson", "elements": 1, "engine": "geojson-matplotlib"}
    except Exception:
        return None

def _domain(spec: dict, subject: str) -> str:
    kind = str(spec.get("kind") or "").lower()
    if kind == "source":
        return "source"
    if kind in ("3d", "scene", "rigid3d"):
        return "3d"
    if kind in ("physics3d", "kinematics"):
        return "physics3d"
    if kind in ("spice", "netlist-spice"):
        return "circuit"
    if kind == "mujoco":
        return "mujoco"
    if kind == "atlas":
        return "atlas"
    if kind == "geojson":
        return "geojson"
    if subject == "化学" or kind in ("chem", "chemistry", "molecule", "reaction", "reaction-sequence"):
        return "chemistry"
    if subject == "计算机" or kind in ("flow", "flowchart", "graph", "tree", "er"):
        return "computing"
    if subject == "高等数学" or kind in ("math", "function", "geometry"):
        return "math"
    if subject in ("电路", "物理") or kind in ("circuit", "force", "physics"):
        return "circuit" if subject == "电路" or kind == "circuit" else "physics"
    if kind in ("chart", "bar", "line", "pie"):
        return "chart"
    if kind in ("table", "grid"):
        return "table"
    if kind in ("timeline", "chronology"):
        return "timeline"
    if kind in ("map", "schematic-map"):
        return "map"
    if kind in ("geometry", "construction"):
        return "math"
    if kind in ("concept", "mindmap"):
        return "concept"
    if kind in ("elements", "generic"):
        return "generic"
    return ""


def _chart(spec: dict, out: Path) -> dict | None:
    labels = spec.get("labels")
    values = spec.get("values")
    if not isinstance(labels, list) or not isinstance(values, list) or len(labels) != len(values) or not labels:
        return None
    try:
        import matplotlib
        matplotlib.use("Agg")
        matplotlib.rcParams["font.sans-serif"] = ["PingFang SC", "Arial Unicode MS", "DejaVu Sans"]
        matplotlib.rcParams["axes.unicode_minus"] = False
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(7.2, 4.2), dpi=160)
        kind = str(spec.get("kind") or "bar")
        if kind == "pie":
            ax.pie([float(v) for v in values], labels=[str(x) for x in labels], autopct="%1.0f%%")
        elif kind == "line":
            ax.plot([str(x) for x in labels], [float(v) for v in values], marker="o", color="#245c73")
        else:
            ax.bar([str(x) for x in labels], [float(v) for v in values], color="#2f6f6a")
        ax.set_title(str(spec.get("title") or ""))
        ax.grid(True, axis="y", linestyle=":", alpha=0.5)
        fig.tight_layout(); out.parent.mkdir(parents=True, exist_ok=True); fig.savefig(out); plt.close(fig)
        return {"path": str(out), "layout": "chart", "elements": len(labels), "engine": "matplotlib-chart"}
    except Exception:
        return None


def compile_figure(spec: dict, *, subject: str, out_path: str | Path) -> dict | None:
    if not isinstance(spec, dict) or not spec:
        return None
    spec = figure_spec.normalize(spec)
    if figure_spec.validate(spec):
        return None
    if subject in NO_GENERATE and str(spec.get("kind") or "").lower() not in ("chart", "bar", "line", "pie", "table", "grid", "timeline", "chronology", "map", "schematic-map", "source", "atlas", "geojson"):
        return None
    domain = _domain(spec, subject)
    if not domain:
        return None
    out = Path(out_path)
    if domain == "source":
        res = _source_image(spec, out)
    elif domain == "3d":
        res = three_d.render_3d(spec, out)
    elif domain == "physics3d":
        res = three_d.render_physics(spec, out)
    elif domain == "mujoco":
        res = three_d.render_mujoco(spec, out)
    elif domain == "atlas":
        root = Path(str(spec.get("root") or "data/atlas"))
        item = atlas.pick(root, tags=spec.get("tags") or [], page=spec.get("page"))
        if not item:
            res = None
        else:
            res = _source_image({"path": str(root / str(item.get("file") or "")), "crop": True}, out)
            if res:
                res["engine"] = "atlas-source-only"; res["source_note"] = str(item.get("source") or "")
    elif domain == "geojson":
        res = _geojson(spec, out)
    elif domain == "circuit" and spec.get("nodes"):
        res = _netlist_graph(spec, out)
    elif domain == "chart":
        res = _chart(spec, out)
    elif domain == "chemistry":
        res = _reaction_sequence(spec, out) or _reaction(spec, out) or figure_router.render(spec, subject=subject, out_path=out)
    elif domain == "circuit" and spec.get("netlist"):
        res = _spice_circuit(spec, out)
    elif domain == "circuit" and spec.get("components"):
        res = _netlist_series(spec, out)
    elif domain == "circuit" and str(spec.get("topology") or "") == "parallel":
        res = _parallel_circuit(spec, out)
    elif domain == "physics" and spec.get("forces"):
        res = _force_template(spec, out)
    elif domain == "math" and spec.get("expression"):
        res = _symbolic_math(spec, out)
    elif domain == "math" and spec.get("elements"):
        res = _geometry(spec, out)
    elif domain == "table":
        res = _table(spec, out)
    elif domain == "timeline":
        res = _timeline(spec, out)
    elif domain == "map":
        res = _schematic_map(spec, out)
    elif domain == "generic":
        res = _geometry(spec, out)
    elif domain == "concept":
        res = figure_router.render({"kind": "flow", "nodes": spec.get("nodes") or [], "edges": spec.get("edges") or []},
                                   subject="计算机", out_path=out)
    else:
        res = figure_router.render(spec, subject=subject, out_path=out)
    min_size = 1 if domain == "source" else 1000
    if not res or not out.is_file() or out.stat().st_size < min_size:
        return None
    try:
        from PIL import Image
        with Image.open(out) as im:
            res["width"], res["height"] = im.size
    except Exception:
        return None
    labels = figure_spec.labels(spec)
    res["labels"] = list(dict.fromkeys(labels))
    res["domain"] = domain
    res["subject"] = subject
    res["engine"] = res.get("engine") or DOMAINS[domain]["engine"]
    res["label_source"] = "spec"
    return res


def support_matrix() -> list[dict]:
    return [{"domain": k, "subjects": sorted(v["subjects"]), "engine": v["engine"],
             "generate": k not in ("medical", "bio")} for k, v in DOMAINS.items()]

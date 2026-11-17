"""学科图路由：有精确渲染器就画，画不出就返回 None，不拿文生图冒充。"""
from __future__ import annotations

from pathlib import Path

from tfv2.render import diagram

PRECISE_SUBJECTS = {"电路", "物理", "高等数学", "化学", "计算机"}
NO_GEN_SUBJECTS = {"医学", "生物", "文科"}


def render(spec: dict, *, subject: str, out_path: str | Path) -> dict | None:
    kind = str((spec or {}).get("kind") or "").lower()
    out = Path(out_path)
    if subject == "化学" or kind in ("chem", "chemistry", "molecule"):
        return render_chemistry(spec, out)
    if subject == "计算机" or kind in ("flow", "flowchart", "graph", "architecture", "er"):
        return render_flow(spec, out)
    if subject == "高等数学" or kind in ("math", "function", "geometry"):
        return render_math(spec, out)
    if subject in ("电路", "物理") or kind in ("circuit", "force", "physics"):
        return diagram.render_spec(spec, out)
    return None


def render_chemistry(spec: dict, out: Path) -> dict | None:
    smiles = str(spec.get("smiles") or "").strip()
    if not smiles:
        return None
    try:
        from rdkit import Chem
        from rdkit.Chem import Draw

        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        img = Draw.MolToImage(mol, size=(900, 560))
        out.parent.mkdir(parents=True, exist_ok=True)
        img.save(out)
        return {"path": str(out), "layout": "chem", "elements": mol.GetNumAtoms()}
    except Exception:
        return None


def render_flow(spec: dict, out: Path) -> dict | None:
    nodes = spec.get("nodes")
    edges = spec.get("edges") or []
    if not isinstance(nodes, list) or not nodes:
        return None
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return None
    W, H = 1000, 700
    img = Image.new("RGB", (W, H), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    fonts = ["/System/Library/Fonts/STHeiti Light.ttc",
             "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
             "/System/Library/Fonts/Supplemental/Songti.ttc"]
    font = ImageFont.load_default()
    for p in fonts:
        try:
            font = ImageFont.truetype(p, 20)
            break
        except Exception:
            pass
    # 纵向自动布局；有 x/y 就用
    n = len(nodes)
    pos = {}
    for i, node in enumerate(nodes):
        nid = str(node.get("id") or i)
        x = float(node.get("x", 500))
        y = float(node.get("y", 90 + i * (520 / max(1, n - 1)) if n > 1 else 350))
        pos[nid] = (x, y)
        label = str(node.get("label") or nid)
        tw = draw.textlength(label, font=font)
        box = (x - max(100, tw / 2 + 20), y - 28, x + max(100, tw / 2 + 20), y + 28)
        draw.rounded_rectangle(box, radius=12, outline=(40, 70, 90), width=2, fill=(245, 250, 252))
        draw.text((x, y), label, fill=(24, 28, 32), font=font, anchor="mm")
    for e in edges:
        a, b = str(e.get("from") or ""), str(e.get("to") or "")
        if a not in pos or b not in pos:
            continue
        x1, y1 = pos[a]; x2, y2 = pos[b]
        # 从方框边缘出发
        if abs(y2 - y1) >= abs(x2 - x1):
            sy = 28 if y2 > y1 else -28
            draw.line((x1, y1 + sy, x2, y2 - sy), fill=(40, 70, 90), width=2)
            ex, ey = x2, y2 - sy
        else:
            sx = 100 if x2 > x1 else -100
            draw.line((x1 + sx, y1, x2 - sx, y2), fill=(40, 70, 90), width=2)
            ex, ey = x2 - sx, y2
        draw.polygon([(ex, ey), (ex - 10, ey - 5), (ex - 10, ey + 5)], fill=(40, 70, 90))
        if e.get("label"):
            draw.text(((x1 + x2) / 2, (y1 + y2) / 2 - 12), str(e["label"]), fill=(80, 90, 100), font=font)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return {"path": str(out), "layout": "flow", "elements": len(nodes)}


def render_math(spec: dict, out: Path) -> dict | None:
    points = spec.get("points")
    if not isinstance(points, list) or len(points) < 2:
        return None
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(7.2, 4.2), dpi=160)
        xs = [float(p[0]) for p in points]
        ys = [float(p[1]) for p in points]
        ax.plot(xs, ys, color="#245c73", linewidth=2)
        ax.axhline(0, color="#8a949e", linewidth=1)
        ax.axvline(0, color="#8a949e", linewidth=1)
        ax.grid(True, linestyle=":", alpha=0.5)
        ax.set_xlabel(str(spec.get("x_label") or "x"))
        ax.set_ylabel(str(spec.get("y_label") or "y"))
        if spec.get("title"):
            ax.set_title(str(spec["title"]))
        fig.tight_layout()
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out)
        plt.close(fig)
        return {"path": str(out), "layout": "math", "elements": len(points)}
    except Exception:
        return None

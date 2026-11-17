"""结构化示意图渲染：模型给元件/连线/标签/数值，Pillow 画图。

不是文生图；不保证物理拓扑正确，只保证结构合法、标签可见，UI 会标“AI 结构示意图”。
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 720, 420
SCALE = 2
INK = (24, 28, 32)
MUTED = (100, 108, 116)
LINE = (60, 68, 76)
FILL = (255, 255, 255)
ACCENT = (15, 118, 110)

ALLOWED = {"wire", "resistor", "capacitor", "inductor", "battery", "switch", "lamp", "meter",
           "arrow", "line", "circle", "rect", "label", "ground", "node"}
FONT_CANDIDATES = [
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Songti.ttc",
    "/System/Library/Fonts/PingFang.ttc",
]


class DiagramError(RuntimeError):
    pass


def _font(size: int):
    for p in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _xy(el: dict, key: str = "x", default: float = 0) -> float:
    try:
        return float(el.get(key, default))
    except Exception:
        return default


def _walk(el: dict) -> list[tuple[float, float]]:
    pts = el.get("points") or []
    out = []
    for p in pts:
        if isinstance(p, (list, tuple)) and len(p) >= 2:
            out.append((float(p[0]), float(p[1])))
    return out


def _label(draw, x, y, text, size=16, fill=INK, anchor="mm"):
    if not text:
        return
    draw.text((x, y), str(text), font=_font(size), fill=fill, anchor=anchor)


def _text_size(draw, text, size):
    if not text:
        return (0, 0)
    box = draw.textbbox((0, 0), str(text), font=_font(size))
    return (box[2] - box[0], box[3] - box[1])


def _component_label(draw, x, y, label, value, vertical=False):
    text = f"{label} = {value}".strip(" =") if label or value else ""
    if not text:
        return
    w, h = _text_size(draw, text, 15)
    bx = x - w / 2 - 3
    by = y - (28 if vertical else 24) - h / 2
    draw.rectangle((bx, by - 2, bx + w + 6, by + h + 2), fill=(255, 255, 255))
    _label(draw, x, by + h / 2, text, 15)


def _nearest_on_segment(px, py, seg):
    x1, y1, x2, y2 = seg
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return x1, y1, math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    qx, qy = x1 + t * dx, y1 + t * dy
    return qx, qy, math.hypot(px - qx, py - qy)


def _lead(draw, px, py, segments):
    if not segments:
        return
    best = min((_nearest_on_segment(px, py, seg) for seg in segments), key=lambda z: z[2])
    if best[2] <= 90 * SCALE:
        draw.line((px, py, best[0], best[1]), fill=LINE, width=2)


def _resistor(draw, x, y, length, vertical, label, value):
    if vertical:
        x1, y1, x2, y2 = x, y - length / 2, x, y + length / 2
    else:
        x1, y1, x2, y2 = x - length / 2, y, x + length / 2, y
    draw.line((x1, y1, x2, y2), fill=LINE, width=2)
    # 简化折线
    n = 6
    if vertical:
        pts = []
        for i in range(n + 1):
            yy = y1 + (y2 - y1) * i / n
            xx = x + (10 if i % 2 else -10)
            pts.append((xx, yy))
    else:
        pts = []
        for i in range(n + 1):
            xx = x1 + (x2 - x1) * i / n
            yy = y + (10 if i % 2 else -10)
            pts.append((xx, yy))
    draw.line(pts, fill=LINE, width=2)
    _component_label(draw, x + (18 if vertical else 0), y, label, value, vertical)


def _capacitor(draw, x, y, length, vertical, label, value):
    gap = 6
    if vertical:
        draw.line((x - 16, y - gap, x + 16, y - gap), fill=LINE, width=3)
        draw.line((x - 16, y + gap, x + 16, y + gap), fill=LINE, width=3)
        draw.line((x, y - length / 2, x, y - gap), fill=LINE, width=2)
        draw.line((x, y + gap, x, y + length / 2), fill=LINE, width=2)
    else:
        draw.line((x - gap, y - 16, x - gap, y + 16), fill=LINE, width=3)
        draw.line((x + gap, y - 16, x + gap, y + 16), fill=LINE, width=3)
        draw.line((x - length / 2, y, x - gap, y), fill=LINE, width=2)
        draw.line((x + gap, y, x + length / 2, y), fill=LINE, width=2)
    _component_label(draw, x, y, label, value, vertical)


def _inductor(draw, x, y, length, vertical, label, value):
    if vertical:
        draw.line((x, y - length / 2, x, y + length / 2), fill=LINE, width=2)
        for i in range(4):
            yy = y - length / 2 + length * (i + 1) / 5
            draw.arc((x - 10, yy - 8, x + 10, yy + 8), 180, 0, fill=LINE, width=2)
    else:
        draw.line((x - length / 2, y, x + length / 2, y), fill=LINE, width=2)
        for i in range(4):
            xx = x - length / 2 + length * (i + 1) / 5
            draw.arc((xx - 8, y - 10, xx + 8, y + 10), 90, 270, fill=LINE, width=2)
    _component_label(draw, x, y, label, value, vertical)


def _battery(draw, x, y, length, vertical, label, value):
    if vertical:
        draw.line((x - 14, y - 6, x + 14, y - 6), fill=LINE, width=2)
        draw.line((x - 8, y + 6, x + 8, y + 6), fill=LINE, width=4)
        draw.line((x, y - length / 2, x, y - 6), fill=LINE, width=2)
        draw.line((x, y + 6, x, y + length / 2), fill=LINE, width=2)
    else:
        draw.line((x - 6, y - 14, x - 6, y + 14), fill=LINE, width=2)
        draw.line((x + 6, y - 8, x + 6, y + 8), fill=LINE, width=4)
        draw.line((x - length / 2, y, x - 6, y), fill=LINE, width=2)
        draw.line((x + 6, y, x + length / 2, y), fill=LINE, width=2)
    _component_label(draw, x, y, label, value, vertical)


def _switch(draw, x, y, length, vertical, label, value):
    if vertical:
        draw.line((x, y - length / 2, x, y), fill=LINE, width=2)
        draw.line((x, y, x + 20, y - 18), fill=LINE, width=2)
        draw.line((x, y, x, y + length / 2), fill=LINE, width=2)
        draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=LINE)
    else:
        draw.line((x - length / 2, y, x, y), fill=LINE, width=2)
        draw.line((x, y, x + 18, y - 20), fill=LINE, width=2)
        draw.line((x, y, x + length / 2, y), fill=LINE, width=2)
        draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=LINE)
    _component_label(draw, x + (18 if vertical else 0), y, label, value, vertical)


def _arrow(draw, x1, y1, x2, y2, label, color=ACCENT):
    draw.line((x1, y1, x2, y2), fill=color, width=2)
    ang = math.atan2(y2 - y1, x2 - x1)
    for sign in (-0.5, 0.5):
        draw.line((x2, y2, x2 - 10 * math.cos(ang + sign), y2 - 10 * math.sin(ang + sign)), fill=color, width=2)
    if label:
        _label(draw, (x1 + x2) / 2, (y1 + y2) / 2 - 12, label, 12, color)




def _simple_series(elements: list[dict]) -> list[dict] | None:
    """识别“一个电源 + 1–3 个两端元件”的串联回路，忽略模型乱坐标，重画成闭合回路。"""
    comps = [e for e in elements if isinstance(e, dict) and str(e.get("type") or "") in
             ("battery", "resistor", "capacitor", "inductor", "switch")]
    batteries = [e for e in comps if str(e.get("type")) == "battery"]
    rest = [e for e in comps if str(e.get("type")) != "battery"]
    if len(batteries) == 1 and 1 <= len(rest) <= 6:
        return [batteries[0]] + rest
    return None


def _render_series(comps: list[dict], target: Path) -> dict:
    img = Image.new("RGB", (W * SCALE, H * SCALE), FILL)
    draw = ImageDraw.Draw(img)
    battery, rest = comps[0], comps[1:]
    bx, by = 110, 230
    top_y, bottom_y = 90, 360
    left_x, right_x = 110, 620
    # 电源在左，剩余元件均分在上边
    _battery(draw, bx * SCALE, by * SCALE, 70 * SCALE, True,
             str(battery.get("label") or "U"), str(battery.get("value") or ""))
    draw.line((left_x * SCALE, (by - 35) * SCALE, left_x * SCALE, top_y * SCALE), fill=LINE, width=2)
    n = len(rest)
    span = right_x - 220
    xs = [220 + span * (i + 0.5) / n for i in range(n)]
    # 电源上端到第一个元件的线
    draw.line((left_x * SCALE, top_y * SCALE, (xs[0] - 45) * SCALE, top_y * SCALE), fill=LINE, width=2)
    for i, el in enumerate(rest):
        x = xs[i]
        typ = str(el.get("type"))
        label, value = str(el.get("label") or ""), str(el.get("value") or "")
        if typ == "resistor":
            _resistor(draw, x * SCALE, top_y * SCALE, 90 * SCALE, False, label, value)
        elif typ == "capacitor":
            _capacitor(draw, x * SCALE, top_y * SCALE, 90 * SCALE, False, label, value)
        elif typ == "inductor":
            _inductor(draw, x * SCALE, top_y * SCALE, 90 * SCALE, False, label, value)
        elif typ == "switch":
            _switch(draw, x * SCALE, top_y * SCALE, 90 * SCALE, False, label, value)
        if i < n - 1:
            draw.line(((x + 45) * SCALE, top_y * SCALE, (xs[i + 1] - 45) * SCALE, top_y * SCALE), fill=LINE, width=2)
    draw.line(((xs[-1] + 45) * SCALE, top_y * SCALE, right_x * SCALE, top_y * SCALE), fill=LINE, width=2)
    draw.line((right_x * SCALE, top_y * SCALE, right_x * SCALE, bottom_y * SCALE), fill=LINE, width=2)
    draw.line((right_x * SCALE, bottom_y * SCALE, left_x * SCALE, bottom_y * SCALE), fill=LINE, width=2)
    draw.line((left_x * SCALE, bottom_y * SCALE, left_x * SCALE, (by + 35) * SCALE), fill=LINE, width=2)
    _label(draw, 360 * SCALE, 30 * SCALE, "AI 结构示意图（串联回路）", 17, MUTED)
    target.parent.mkdir(parents=True, exist_ok=True)
    img.save(target, format="PNG")
    return {"path": str(target), "width": W * SCALE, "height": H * SCALE, "elements": len(comps), "layout": "series"}

def render_spec(spec: dict, out_path: str | Path) -> dict:
    if not isinstance(spec, dict):
        raise DiagramError("figure_spec 不是对象")
    elements = spec.get("elements")
    if not isinstance(elements, list) or not elements:
        raise DiagramError("figure_spec.elements 为空")
    simple = None if str(spec.get("topology") or "") == "parallel" else _simple_series([e for e in elements if isinstance(e, dict)])
    if simple:
        return _render_series(simple, Path(out_path))
    img = Image.new("RGB", (W * SCALE, H * SCALE), FILL)
    draw = ImageDraw.Draw(img)
    # 轻网格，方便定位
    for x in range(0, W, 40):
        draw.line((x * SCALE, 0, x * SCALE, H * SCALE), fill=(240, 242, 244), width=1)
    for y in range(0, H, 40):
        draw.line((0, y * SCALE, W * SCALE, y * SCALE), fill=(240, 242, 244), width=1)
    segments = []
    for el in elements:
        if isinstance(el, dict) and str(el.get("type") or "") == "wire":
            pts = [(a * SCALE, b * SCALE) for a, b in _walk(el)]
            for a, b in zip(pts, pts[1:]):
                segments.append((a[0], a[1], b[0], b[1]))
    used = 0
    for el in elements:
        if not isinstance(el, dict):
            continue
        typ = str(el.get("type") or "").strip()
        if typ not in ALLOWED:
            continue
        x, y = _xy(el, "x") * SCALE, _xy(el, "y") * SCALE
        length = _xy(el, "length", 80) * SCALE
        vertical = str(el.get("orientation") or "h").lower().startswith("v")
        label = str(el.get("label") or "")
        value = str(el.get("value") or "")
        if typ in ("resistor", "capacitor", "inductor", "battery", "switch"):
            if vertical:
                _lead(draw, x, y - length / 2, segments); _lead(draw, x, y + length / 2, segments)
            else:
                _lead(draw, x - length / 2, y, segments); _lead(draw, x + length / 2, y, segments)
        if typ == "wire":
            pts = [(a * SCALE, b * SCALE) for a, b in _walk(el)]
            if len(pts) >= 2:
                draw.line(pts, fill=LINE, width=2)
                used += 1
        elif typ == "resistor":
            _resistor(draw, x, y, length, vertical, label, value); used += 1
        elif typ == "capacitor":
            _capacitor(draw, x, y, length, vertical, label, value); used += 1
        elif typ == "inductor":
            _inductor(draw, x, y, length, vertical, label, value); used += 1
        elif typ == "battery":
            _battery(draw, x, y, length, vertical, label, value); used += 1
        elif typ == "switch":
            _switch(draw, x, y, length, vertical, label, value); used += 1
        elif typ == "lamp":
            r = 14
            draw.ellipse((x - r, y - r, x + r, y + r), outline=LINE, width=2)
            draw.line((x - 8, y - 8, x + 8, y + 8), fill=LINE, width=2)
            draw.line((x - 8, y + 8, x + 8, y - 8), fill=LINE, width=2)
            _component_label(draw, x, y, label, value, vertical); used += 1
        elif typ == "arrow":
            _arrow(draw, _xy(el, "x1") * SCALE, _xy(el, "y1") * SCALE,
                   _xy(el, "x2") * SCALE, _xy(el, "y2") * SCALE,
                   label or value); used += 1
        elif typ == "line":
            draw.line((_xy(el, "x1") * SCALE, _xy(el, "y1") * SCALE,
                       _xy(el, "x2") * SCALE, _xy(el, "y2") * SCALE), fill=LINE, width=2)
            used += 1
        elif typ == "circle":
            r = _xy(el, "r", 20) * SCALE
            draw.ellipse((x - r, y - r, x + r, y + r), outline=LINE, width=2)
            _label(draw, x, y, label or value, 12); used += 1
        elif typ == "rect":
            w, h = _xy(el, "w", 100) * SCALE, _xy(el, "h", 50) * SCALE
            draw.rectangle((x, y, x + w, y + h), outline=LINE, width=2)
            _label(draw, x + w / 2, y + h / 2, label or value, 12); used += 1
        elif typ == "label":
            _label(draw, x, y, label or value, 13)
            used += 1
        elif typ == "ground":
            draw.line((x - 14, y, x + 14, y), fill=LINE, width=2)
            draw.line((x - 8, y + 6, x + 8, y + 6), fill=LINE, width=2)
            draw.line((x - 3, y + 12, x + 3, y + 12), fill=LINE, width=2)
            used += 1
        elif typ == "node":
            draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=LINE)
            used += 1
    if used == 0:
        raise DiagramError("figure_spec 没有可绘制的元素")
    target = Path(out_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    img.save(target, format="PNG")
    return {"path": str(target), "width": W * SCALE, "height": H * SCALE, "elements": used}

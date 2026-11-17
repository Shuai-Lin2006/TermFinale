"""生成白底苯系芳烃命名示例（邻/间/对与三取代）。"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

_FONT = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"


def _font(size: int):
    try:
        return ImageFont.truetype(_FONT, size)
    except OSError:
        return ImageFont.load_default()


def _benzene(d: ImageDraw.ImageDraw, cx: int, cy: int, positions: list[int], label: str,
             f_label, f_small) -> None:
    r = 62
    pts = []
    for i in range(6):
        a = -math.pi / 2 + 2 * math.pi * i / 6
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    d.line(pts + [pts[0]], fill="#1f2328", width=5, joint="curve")
    d.ellipse((cx - 34, cy - 34, cx + 34, cy + 34), outline="#1f2328", width=4)
    for i in positions:
        x, y = pts[i]
        dx, dy = x - cx, y - cy
        norm = math.hypot(dx, dy) or 1
        ex, ey = x + dx / norm * 42, y + dy / norm * 42
        d.line(((x, y), (ex, ey)), fill="#1f2328", width=3)
    d.text((cx - 76, cy + 120), label, font=f_label, fill="#1f2328")


def draw_benzene_naming(path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1600, 1000), "white")
    d = ImageDraw.Draw(img)
    f_title = _font(40)
    f_label = _font(25)
    f_small = _font(18)
    d.text((70, 40), "苯系芳烃命名示例", font=f_title, fill="#1f2328")
    d.text((70, 100), "邻/间/对表示二取代苯的相对位置；三取代苯用数字编号", font=f_small, fill="#5b6470")

    top = [
        (300, 320, [0, 1], "邻二甲苯（1,2-）"),
        (800, 320, [0, 2], "间二甲苯（1,3-）"),
        (1300, 320, [0, 3], "对二甲苯（1,4-）"),
    ]
    bottom = [
        (300, 680, [0, 1, 2], "1,2,3-三甲苯"),
        (800, 680, [0, 1, 3], "1,2,4-三甲苯"),
        (1300, 680, [0, 2, 4], "1,3,5-三甲苯"),
    ]
    for cx, cy, pos, label in top + bottom:
        _benzene(d, cx, cy, pos, label, f_label, f_small)
    d.text((70, 930), "说明：本图为教学示意；苯环内圈表示芳香性，每条短线代表一个 CH₃。", font=f_small, fill="#8a929c")
    img.save(path)
    return path


if __name__ == "__main__":
    print(draw_benzene_naming("/tmp/benzene_naming.png"))

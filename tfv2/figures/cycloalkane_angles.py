"""生成白底环烷烃内角示意图（三角/四角/五角/六角）。"""
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


def _polygon(cx: int, cy: int, n: int, r: int = 95):
    pts = []
    for i in range(n):
        angle = -math.pi / 2 + 2 * math.pi * i / n
        pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    return pts


def draw_cycloalkane_angles(path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1600, 620), "white")
    d = ImageDraw.Draw(img)
    f_title = _font(40)
    f_label = _font(26)
    f_small = _font(20)
    d.text((70, 40), "环烷烃的环大小与内角", font=f_title, fill="#1f2328")
    d.text((70, 100), "Baeyer 平面假设下的内角；环越小，偏离 109.5° 越多", font=f_small, fill="#5b6470")

    items = [
        (250, "环丙烷", 3, "60°"),
        (620, "环丁烷", 4, "90°"),
        (990, "环戊烷", 5, "108°"),
        (1360, "环己烷", 6, "120°"),
    ]
    for cx, name, n, angle in items:
        pts = _polygon(cx, 340, n)
        d.line(pts + [pts[0]], fill="#1f2328", width=6, joint="curve")
        for x, y in pts:
            d.ellipse((x - 12, y - 12, x + 12, y + 12), fill="#1f2328")
        d.text((cx - 45, 490), name, font=f_label, fill="#1f2328")
        d.text((cx - 28, 530), f"平面内角 {angle}", font=f_small, fill="#245c73")

    d.text((70, 580), "说明：本图为教学示意，键长/键角未按真实比例绘制。", font=f_small, fill="#8a929c")
    img.save(path)
    return path


if __name__ == "__main__":
    print(draw_cycloalkane_angles("/tmp/cycloalkane_angles.png"))

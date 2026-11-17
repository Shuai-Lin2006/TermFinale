"""生成休克尔规则 4n+2 示例表（白底、教材式）。"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

_FONT = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"


def _font(size: int):
    try:
        return ImageFont.truetype(_FONT, size)
    except OSError:
        return ImageFont.load_default()


def draw_huckel_examples(path: str | Path) -> Path:
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1600, 900), "white")
    d = ImageDraw.Draw(img)
    f_title = _font(40); f_head = _font(28); f = _font(23); f_small = _font(18)
    d.text((70, 40), "休克尔规则：4n+2 的例子", font=f_title, fill="#1f2328")
    d.text((70, 100), "单环、平面、闭合共轭，且 π 电子数 = 4n+2", font=f_small, fill="#5b6470")

    yes = [
        ("苯", "6π = 4×1+2"), ("萘", "10π = 4×2+2"), ("蒽", "14π = 4×3+2"),
        ("环戊二烯负离子", "6π"), ("环丙烯正离子", "2π"),
        ("环丁二烯双正离子", "2π"), ("环辛四烯双正离子", "6π"), ("[18]-轮烯", "18π"),
    ]
    no = [("环丁二烯", "4π"), ("环辛四烯", "8π")]

    d.rectangle((70, 155, 1530, 190), fill="#e8f3ee")
    d.text((90, 158), "有芳香性（4n+2）", font=f_head, fill="#1f5c3a")
    y = 215
    for name, count in yes:
        d.text((100, y), "✓", font=f_head, fill="#1f7a4d")
        d.text((150, y), name, font=f, fill="#1f2328")
        d.text((700, y), count, font=f, fill="#245c73")
        y += 62

    y = 215
    d.rectangle((1080, 155, 1530, 190), fill="#f8e9e9")
    d.text((1100, 158), "无芳香性", font=f_head, fill="#7a1f1f")
    for name, count in no:
        d.text((1110, y), "✗", font=f_head, fill="#a33")
        d.text((1160, y), name, font=f, fill="#1f2328")
        d.text((1370, y), count, font=f, fill="#7a1f1f")
        y += 62

    d.text((70, 840), "说明：本表据资料第27–29页整理；n=0,1,2,3…；离子体系要把电荷计入 π 电子数。", font=f_small, fill="#8a929c")
    img.save(path)
    return path


if __name__ == "__main__":
    print(draw_huckel_examples("/tmp/huckel_examples.png"))

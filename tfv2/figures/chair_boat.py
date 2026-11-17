"""生成白底、干净的环己烷椅式/船式示意图（不依赖 PPT 截图）。"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

_FONT_CANDIDATES = (
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
)


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in _FONT_CANDIDATES:
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _vertex(draw: ImageDraw.ImageDraw, xy: tuple[int, int], r: int = 13) -> None:
    x, y = xy
    draw.ellipse((x - r, y - r, x + r, y + r), fill="#1f2328")


def _bond(draw: ImageDraw.ImageDraw, a: tuple[int, int], b: tuple[int, int], width: int = 6) -> None:
    draw.line((a, b), fill="#1f2328", width=width, joint="curve")


def draw_chair_boat(path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1600, 900), "white")
    d = ImageDraw.Draw(img)
    f_title = _font(42)
    f_label = _font(30)
    f_small = _font(22)

    d.text((70, 40), "环己烷的椅式与船式构象", font=f_title, fill="#1f2328")
    d.text((70, 100), "a 键：直立键（垂直）    e 键：平伏键（近似平行于环平面）", font=f_small, fill="#5b6470")

    # 椅式
    chair = [(200, 420), (320, 300), (520, 220), (720, 320), (600, 440), (400, 520)]
    for i in range(len(chair)):
        _bond(d, chair[i], chair[(i + 1) % len(chair)])
    for p in chair:
        _vertex(d, p)

    # 椅式 a 键（蓝）
    a_bonds = [
        ((200, 420), (200, 500)),
        ((320, 300), (320, 220)),
        ((520, 220), (520, 300)),
        ((720, 320), (720, 240)),
        ((600, 440), (600, 520)),
        ((400, 520), (400, 440)),
    ]
    for a, b in a_bonds:
        d.line((a, b), fill="#245c73", width=4)
    # 椅式 e 键（红）
    e_bonds = [
        ((200, 420), (120, 420)),
        ((320, 300), (250, 270)),
        ((520, 220), (590, 190)),
        ((720, 320), (800, 320)),
        ((600, 440), (670, 470)),
        ((400, 520), (330, 550)),
    ]
    for a, b in e_bonds:
        d.line((a, b), fill="#b45309", width=4)
    d.text((165, 480), "a", font=f_small, fill="#245c73")
    d.text((90, 395), "e", font=f_small, fill="#b45309")
    d.text((430, 650), "椅式", font=f_label, fill="#1f2328")
    d.text((360, 690), "椅式：六个碳交错上下，最稳定", font=f_small, fill="#5b6470")

    # 船式
    boat = [(1000, 450), (1150, 340), (1350, 340), (1500, 450), (1350, 560), (1150, 560)]
    for i in range(len(boat)):
        _bond(d, boat[i], boat[(i + 1) % len(boat)])
    for p in boat:
        _vertex(d, p)
    d.text((1160, 650), "船式", font=f_label, fill="#1f2328")
    d.text((1050, 690), "船式：船头/船尾上翘，稳定性低于椅式", font=f_small, fill="#5b6470")

    d.text((70, 800), "说明：本图为教学示意，键长/键角未按真实比例绘制；结构式请以资料原图为准。", font=f_small, fill="#8a929c")
    img.save(path)
    return path


if __name__ == "__main__":
    print(draw_chair_boat("/tmp/chair_boat.png"))

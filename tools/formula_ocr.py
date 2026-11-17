
"""Run pix2tex (LaTeX-OCR) in the docling venv and print LaTeX JSON.

Usage: python tools/formula_ocr.py image1.png image2.png ...
Output: {"items":[{"path":"...","latex":"\\int..."}]}
"""
from __future__ import annotations

import json
import os
import sys

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")


def main() -> None:
    import warnings
    warnings.filterwarnings("ignore")
    from PIL import Image
    from pix2tex.cli import LatexOCR

    model = LatexOCR()
    items = []
    for path in sys.argv[1:]:
        latex = ""
        try:
            from PIL import ImageOps
            with Image.open(path) as im:
                rgba = im.convert("RGBA")
                bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
                bg.alpha_composite(rgba)
                rgb = bg.convert("RGB")
                # pix2tex expects a white margin; a tight transparent crop
                # becomes black-on-black after naive RGB conversion.
                rgb = ImageOps.expand(rgb, border=16, fill="white")
            # resize=False skips the torch-jit resize model (broken on 3.14) and
            # is ~10x faster; pix2tex pads/resizes internally anyway.
            latex = (model(rgb, resize=True) or "").strip()
        except Exception:
            latex = ""
        items.append({"path": path, "latex": latex})
    print(json.dumps({"items": items}, ensure_ascii=False))


if __name__ == "__main__":
    main()

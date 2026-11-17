"""Render a LaTeX formula to PNG for PDF/Word fallback.

KaTeX/Typst handle most formulas. When they cannot, an image is the only
faithful output: never print half LaTeX or raw backslash commands.
"""
from __future__ import annotations

import base64
import tempfile
from pathlib import Path


def _clean(latex: str) -> str:
    text = str(latex or "").strip()
    for left, right in (("$$", "$$"), ("$", "$"), ("\\[", "\\]"), ("\\(", "\\)")):
        if text.startswith(left) and text.endswith(right):
            text = text[len(left): len(text) - len(right)].strip()
    return text


def formula_png(latex: str) -> bytes | None:
    text = _clean(latex)
    if not text or any(x in text for x in ("\\chemfig", "\\ce{", "\\begin{array}")):
        return None
    try:
        import matplotlib
        matplotlib.use("Agg")
        from matplotlib import mathtext
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as fh:
            path = Path(fh.name)
        try:
            mathtext.math_to_image(text, str(path), dpi=220, format="png")
            return path.read_bytes()
        finally:
            path.unlink(missing_ok=True)
    except Exception:
        return None


def formula_data_uri(latex: str) -> str:
    png = formula_png(latex)
    if not png:
        return ""
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")

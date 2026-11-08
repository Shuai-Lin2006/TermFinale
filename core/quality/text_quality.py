"""页文本质量检测：识别 PDF 文本层乱码/公式串，触发 OCR 回退。"""
from __future__ import annotations

import re

_CN = re.compile(r"[\u4e00-\u9fff]")
_LATIN_WORD = re.compile(r"[A-Za-z]+")
# “x x x y y y”这类公式乱码 / 连续单字母
_SPACED_SINGLE = re.compile(r"(?:\b[A-Za-z]\b[\s,，.]*){5,}")


def is_low_quality_page(text: str) -> bool:
    t = (text or "").strip()
    if len(t) < 20:
        return True
    cn = len(_CN.findall(t))
    words = _LATIN_WORD.findall(t)
    single = sum(1 for w in words if len(w) == 1)
    if _SPACED_SINGLE.search(t):
        return True
    # 中文几乎消失，且大量单字母：典型公式文本层乱码
    if cn < 8 and words and single / max(1, len(words)) > 0.35:
        return True
    # 可见字符里中文占比极低，且行内几乎没有完整英文单词
    visible = len(re.sub(r"\s+", "", t))
    if visible >= 40 and cn / visible < 0.08 and (not words or len(" ".join(words)) / visible < 0.15):
        return True
    # 公式 PDF 的文本层：大量私用区字形 + 单字符短行
    private = len(re.findall(r"[\uf000-\uf0ff]", t))
    lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
    if visible >= 30 and private / visible > 0.03:
        return True
    if len(lines) >= 8:
        short = sum(1 for ln in lines if len(ln) <= 2) / len(lines)
        if short > 0.45 and cn < 40:
            return True
    return False

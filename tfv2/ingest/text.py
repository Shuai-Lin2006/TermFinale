"""资料文本清洗：去掉控制/私用区乱码，保留常见数学符号。

PPT 的公式编辑器常把 Ω/Φ 等存成 U+F0xx 私用区字符；
直接当乱码删掉会把 2Ω 变成 2，所以先做小范围映射再清理。
"""
from __future__ import annotations

import re

# 常见 MathType/Symbol 私用区映射（按 Times New Roman/Symbol 编码）
_PRIVATE_MAP = {
    "\uf046": "Φ",
    "\uf057": "Ω",
    "\uf02d": "−",
    "\uf03d": "=",
    "\uf0b4": "×",
    "\uf0b1": "±",
}
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ue000-\uf8ff]")


def sanitize_text(text: str) -> str:
    text = text or ""
    for src, dst in _PRIVATE_MAP.items():
        text = text.replace(src, dst)
    text = _CONTROL.sub("", text)
    text = text.replace("\ufffd", "")
    return text

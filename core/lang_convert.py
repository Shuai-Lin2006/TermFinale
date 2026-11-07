"""生成内容语言转换：简体 → 繁体（词组级）。"""
from __future__ import annotations

_cc = None

def to_hant(text: str) -> str:
    global _cc
    if not text:
        return text
    try:
        if _cc is None:
            from opencc import OpenCC
            _cc = OpenCC("s2twp")
        return _cc.convert(text)
    except Exception:
        return text


_EN_LABELS = {
    "易错点": "Common pitfalls", "易错": "Common pitfalls",
    "例题": "Example", "例": "Example", "小结": "Summary",
    "定义": "Definition", "补充": "Supplement", "注意": "Note",
    "考点": "Key points", "解析": "Solution", "答案": "Answer",
    "本章速查": "Quick review", "出处": "Source",
}


def to_english(md: str) -> str:
    """轻量英文标签替换：只处理常见栏目标题，避免中文残留。"""
    for zh, en in _EN_LABELS.items():
        md = md.replace(zh, en)
    return md

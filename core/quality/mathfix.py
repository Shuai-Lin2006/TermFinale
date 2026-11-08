"""行内公式闭合修复：只处理单行奇数个 `$`，不改代码块/公式块。"""
from __future__ import annotations


def close_inline_math(markdown: str) -> tuple[str, int]:
    out = []
    fixed = 0
    in_code = False
    for line in (markdown or "").splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
            out.append(line); continue
        if in_code or "$$" in line:
            out.append(line); continue
        if line.count("$") % 2 == 1:
            line = line.rstrip() + "$"
            fixed += 1
        out.append(line)
    text = "\n".join(out)
    if text.count("$$") % 2 == 1:
        text = text.rstrip() + "\n$$"
        fixed += 1
    return text, fixed

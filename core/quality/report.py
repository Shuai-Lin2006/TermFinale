"""生成后自检：把「乱码、公式、重复、图片、空章」这类问题在展示前暴露出来。"""
from __future__ import annotations

import re

BAD_TEMPLATES = ("为什么学这个", "核心原理与公式", "深度拆解", "零基础大白话", "考场避坑与拿分套路")


def audit_markdown(md: str, expect_images: bool = False, source_tags: int = 0,
                   require_headings: bool = True) -> dict:
    text = md or ""
    issues: list[str] = []
    checks: list[tuple[str, bool]] = []

    def add(name: str, ok: bool, msg: str = "") -> None:
        checks.append((name, ok))
        if not ok and msg:
            issues.append(msg)

    add("内容非空", len(text.strip()) >= 300, f"正文过短（{len(text)} 字）")
    add("无乱码", "�" not in text, "出现替换字符 �")

    # 公式定界符：去掉 $$ 后剩余 $ 必须成对
    stripped = text.replace("$$", "")
    add("公式成对", stripped.count("$") % 2 == 0, "存在未闭合的 $ 公式")

    bad_tag = any("[[[IMAGE:" in line and "]]]" not in line for line in text.splitlines())
    add("无占位符残留", "@@" not in text and not bad_tag,
        "存在未替换的占位符或残缺图片标签")

    leftovers = [t for t in BAD_TEMPLATES if t in text]
    add("无旧模板标题", not leftovers, "出现旧模板标题：" + "、".join(leftovers))

    # 重复检测：统计重复段落占比
    blocks = [b for b in re.split(r"\n{2,}", text) if len(b.strip()) > 40]
    dup_ratio = 0.0
    if blocks:
        seen: set[str] = set()
        dup = 0
        for b in blocks:
            key = re.sub(r"\s+", "", b)
            if key in seen:
                dup += 1
            else:
                seen.add(key)
        dup_ratio = dup / len(blocks)
    add("重复段落<15%", dup_ratio < 0.15, f"重复段落占 {dup_ratio:.0%}，建议重新生成")

    chapters = len(re.findall(r"(?m)^##\s", text))
    if require_headings:
        add("章节完整", chapters >= 1, "没有识别到章节标题")

    actual_tags = text.count("[[[IMAGE:")
    if expect_images:
        add("配图标签完整", actual_tags > 0, "资料里有图，但生成内容没有引用配图")
    if source_tags:
        add("配图未丢失", actual_tags >= max(1, int(source_tags * 0.8)),
            f"资料里有 {source_tags} 张图，正文只引用了 {actual_tags} 张")

    # 图片堆叠：连续 3 个标签之间几乎没有文字
    positions = [m.start() for m in re.finditer(r"\[\[\[IMAGE:", text)]
    stacked = 0
    for i in range(len(positions) - 2):
        if positions[i + 2] - positions[i] < 400:
            stacked += 1
    add("图片未堆叠", stacked == 0, "有 3 张以上配图堆在一起，可能张冠李戴")

    passed = all(ok for _, ok in checks)
    return {"passed": passed, "checks": [{"name": n, "ok": ok} for n, ok in checks],
            "issues": issues, "chars": len(text), "chapters": chapters,
            "dup_ratio": round(dup_ratio, 3)}

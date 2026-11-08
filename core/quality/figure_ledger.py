"""逐图账本：源资料里的图片标签是否进入讲义、文件/页码/图注是否有效。"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

TAG_RE = re.compile(r"\[\[\[IMAGE:\s*([^|\]]+?)\s*\|\s*图注:\s*(.*?)（第\s*(\d+)\s*页）\s*\]\]\]", re.S)


@dataclass
class FigureItem:
    file: str
    page: int
    caption: str
    in_source: bool
    in_guide: bool
    file_exists: bool
    caption_ok: bool


@dataclass
class FigureLedger:
    source: int = 0
    used: int = 0
    missing: list[str] = field(default_factory=list)
    orphan: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    items: list[FigureItem] = field(default_factory=list)


def audit_figures(source_pages: list[str], markdown: str, assets_dir: str | Path) -> FigureLedger:
    root = Path(assets_dir)
    src = []
    for i, block in enumerate(source_pages, 1):
        for m in TAG_RE.finditer(block or ""):
            src.append((m.group(1).strip(), int(m.group(3)), m.group(2).strip(), i))
    guide = []
    for m in TAG_RE.finditer(markdown or ""):
        guide.append((m.group(1).strip(), int(m.group(3)), m.group(2).strip()))
    src_names = {x[0] for x in src}
    guide_names = {x[0] for x in guide}
    led = FigureLedger(source=len(src), used=len(guide_names & src_names))
    for name, page, cap, page_idx in src:
        in_guide = name in guide_names
        exists = (root / name).is_file()
        cap_ok = len(re.sub(r"\s+", "", cap)) >= 4
        led.items.append(FigureItem(name, page, cap, True, in_guide, exists, cap_ok))
        if not in_guide:
            led.missing.append(f"{name}（P.{page}）")
        if not exists:
            led.issues.append(f"文件不存在：{name}")
        if not cap_ok:
            led.issues.append(f"图注过短：{name}")
    for name, page, cap in guide:
        if name not in src_names:
            led.orphan.append(f"{name}（P.{page}）")
    return led

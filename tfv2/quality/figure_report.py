"""图片清单/图源报告：每张图必须有图注、来源页、资产和来源类型。"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from tfv2.domain.lecture import LectureSpec

try:
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None


class FigureReportItem(BaseModel):
    section_title: str
    block_id: str
    image_id: str
    caption: str
    source_pages: list[int]
    asset_path: str | None
    asset_exists: bool
    width: int | None = None
    height: int | None = None
    origin: Literal["source", "redrawn", "schematic"] = "schematic"
    source_note: str | None = None
    source_bbox: list[float] | None = None
    status: Literal["ok", "ok_schematic", "fail"] = "ok"
    issue: str | None = None


def _pages(fig) -> list[int]:
    end = fig.source.page_end or fig.source.page_start
    return list(range(fig.source.page_start, end + 1))


def build_figure_report(spec: LectureSpec, base_dir: str | Path) -> list[FigureReportItem]:
    base = Path(base_dir)
    items: list[FigureReportItem] = []
    for sec in spec.sections:
        for block in sec.blocks:
            fig = block.figure
            if fig is None:
                continue
            asset = fig.asset_path
            path = (base / asset) if asset and not Path(asset).is_absolute() else (Path(asset) if asset else None)
            exists = bool(path and path.is_file())
            width = height = None
            if exists and Image is not None:
                try:
                    with Image.open(path) as im:  # type: ignore[arg-type]
                        width, height = im.size
                except Exception:
                    pass
            issue = None
            status: Literal["ok", "ok_schematic", "fail"] = "ok"
            if not fig.caption.strip():
                issue = "缺图注"; status = "fail"
            elif not exists:
                issue = "资产不存在"; status = "fail"
            elif fig.origin == "schematic":
                status = "ok_schematic"
            items.append(FigureReportItem(
                section_title=sec.title, block_id=block.id, image_id=fig.image_id,
                caption=fig.caption, source_pages=_pages(fig), asset_path=asset,
                asset_exists=exists, width=width, height=height,
                origin=fig.origin, source_note=fig.source_note,
                source_bbox=fig.bbox, status=status, issue=issue,
            ))
    return items


def report_markdown(items: list[FigureReportItem]) -> str:
    lines = ["# 图源报告", "", f"- 图片数：{len(items)}", ""]
    for it in items:
        lines += [
            f"## {it.image_id} · {it.section_title}",
            "",
            f"- 图注：{it.caption}",
            f"- 来源页：{it.source_pages}",
            f"- 来源区域：{it.source_bbox}",
            f"- 资产：{it.asset_path or '（无）'}",
            f"- 类型：{it.origin}",
            f"- 尺寸：{it.width}×{it.height}" if it.width else "- 尺寸：未知",
            f"- 状态：{it.status}" + (f"（{it.issue}）" if it.issue else ""),
        ]
        if it.source_note:
            lines.append(f"- 说明：{it.source_note}")
        lines.append("")
    return "\n".join(lines)

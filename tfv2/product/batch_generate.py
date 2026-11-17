"""分批生成：每 16 页一个单元，生成后合并为一份讲义。"""
from __future__ import annotations

from pathlib import Path

from core import paths
from tfv2.product import service
from tfv2.product.batch_merge import merge_chunks
from tfv2.product.preview_generate import generate_preview


def _chunk_dir(cid: str) -> Path:
    d = service.artifact_path(cid)
    if d is not None:
        return d
    return paths.data_dir() / "previews" / cid


def generate_batch(artifact_id: str, pages: list[int], output_id: str, progress=None) -> Path:
    chosen = sorted({int(p) for p in pages if int(p) > 0})
    if not chosen:
        raise ValueError("没有有效页码")
    chunks = [chosen[i:i + 16] for i in range(0, len(chosen), 16)]
    ids: list[str] = []
    for i, chunk in enumerate(chunks, start=1):
        cid = f"{output_id}-c{i}"
        if progress:
            progress(int((i - 1) / len(chunks) * 70), f"第 {i}/{len(chunks)} 批：生成")
        generate_preview(artifact_id, cid, page_numbers=chunk)
        ids.append(cid)
    if progress:
        progress(75, "合并分批讲义")
    pdf = merge_chunks(output_id, ids)
    if progress:
        progress(95, "构建完成")
    return pdf

"""图形区域检测与渲染（PDF 优先）。

背景：旧实现只把 PDF 里「文本流中的位图块」当图片，而课件里的受力图、
电路图、几何图几乎都是**矢量绘制**，于是永远提取不到。

做法：不「提取对象」，而是把页面上的**图形区域整块渲染成 PNG**——
PDF 自带渲染器，矢量图与位图一视同仁。

输出：`Figure` 列表，每个带页码、bbox、文件名、图注；
调用方按 bbox.y0 把它插回该页文本流的正确位置。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import fitz
from loguru import logger

FIG_PAD = 30  # 裁剪留白，避免图内文字标签被切
from PIL import Image, ImageStat

# 过滤阈值（页面比例）
MIN_AREA_RATIO = 0.004     # 小于 0.4% 页面积视为图标
MAX_AREA_RATIO = 0.90      # 大于 90% 视为整页背景
MIN_SIDE = 24              # 任一边小于 24pt 视为装饰
MAX_TEXT_COVER = 0.55      # 区域内文字覆盖超过 55% 视为正文块
MAX_CLUSTER_AREA = 0.70    # 超过 70% 页面积多半是整页版式；45%~70% 的"图+公式"混排块仍保留（文本层缺失时它是唯一载体）
MIN_ASPECT, MAX_ASPECT = 0.15, 6.5   # 过扁/过竖的多半是背景条或分隔线
CLUSTER_GAP = 12           # 聚类外扩
CAPTION_MAX_GAP = 46       # 图注与图形最大垂直距离


@dataclass
class Figure:
    page: int                      # 1-based
    filename: str
    bbox: tuple[float, float, float, float]
    caption: str = ""
    source: str = "vector"         # vector | raster
    hash: int = 0

    def tag(self) -> str:
        cap = self.caption or f"第 {self.page} 页配图"
        return f"[[[IMAGE: {self.filename} | 图注: {cap}]]]"


@dataclass
class _Cand:
    rect: fitz.Rect
    source: str


def _page_area(page: fitz.Page) -> float:
    return page.rect.width * page.rect.height


def _is_decorative(rect: fitz.Rect, page: fitz.Page) -> bool:
    w, h = rect.width, rect.height
    if w < MIN_SIDE or h < MIN_SIDE:
        return True
    area_ratio = (w * h) / max(1.0, _page_area(page))
    if area_ratio > MAX_AREA_RATIO or area_ratio < MIN_AREA_RATIO / 4:
        return True

    pw, ph = page.rect.width, page.rect.height
    # 页眉横幅：贴顶且较宽
    if rect.y1 < ph * 0.18 and w > pw * 0.22:
        return True
    # 页脚
    if rect.y0 > ph * 0.90:
        return True
    # 角落 logo：小面积 + 贴角
    in_left, in_right = rect.x1 < pw * 0.18, rect.x0 > pw * 0.82
    in_top, in_bottom = rect.y1 < ph * 0.18, rect.y1 > ph * 0.82
    if area_ratio < 0.05 and ((in_left and in_bottom) or (in_right and in_top) or (in_left and in_top)):
        return True
    return False


def _collect_candidates(page: fitz.Page) -> list[_Cand]:
    cands: list[_Cand] = []
    pw, ph = page.rect.width, page.rect.height
    for d in page.get_drawings():
        rect = fitz.Rect(d["rect"])
        if _is_decorative(rect, page):
            continue
        area_ratio = rect.width * rect.height / max(1.0, pw * ph)
        # 整页宽/高的细线（页眉横线、边框、分隔线）会把多个图连成一张，直接忽略
        if rect.height < 4 and rect.width > pw * 0.5:
            continue
        if rect.width < 4 and rect.height > ph * 0.5:
            continue
        # 全页背景板（常见于 PPT 导出的 PDF）：白色或接近铺满，绝不能参与聚簇
        if area_ratio > 0.9:
            continue
        fill = d.get("fill")
        if fill and min(fill) > 0.95 and area_ratio > 0.25:
            continue
        cands.append(_Cand(rect, "vector"))
    for info in page.get_image_info():
        rect = fitz.Rect(info["bbox"])
        if _is_decorative(rect, page):
            continue
        cands.append(_Cand(rect, "raster"))
    return cands


def _cluster(cands: list[_Cand]) -> list[fitz.Rect]:
    """外扩后相交则合并，直到稳定。"""
    rects = [fitz.Rect(c.rect) for c in cands]
    changed = True
    while changed:
        changed = False
        out: list[fitz.Rect] = []
        for r in rects:
            merged = False
            for i, other in enumerate(out):
                a = fitz.Rect(r) + (-CLUSTER_GAP, -CLUSTER_GAP, CLUSTER_GAP, CLUSTER_GAP)
                if a.intersects(other):
                    out[i] = other | r
                    merged = True
                    changed = True
                    break
            if not merged:
                out.append(fitz.Rect(r))
        rects = out
    return rects


def _text_coverage(rect: fitz.Rect, text_blocks: list) -> float:
    """区域内文字块面积 / 区域面积。"""
    area = max(1.0, rect.width * rect.height)
    covered = 0.0
    for b in text_blocks:
        br = fitz.Rect(b[:4])
        inter = br & rect
        if not inter.is_empty:
            covered += inter.width * inter.height
    return min(1.0, covered / area)


def _dense_text_blocks(rect: fitz.Rect, text_blocks: list) -> int:
    """区域内「成句」的文本块数量（图里的短标签不算）。"""
    count = 0
    for b in text_blocks:
        text = (b[4] or "").strip()
        if len(text) < 20:
            continue
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        if rect.x0 <= cx <= rect.x1 and rect.y0 <= cy <= rect.y1:
            count += 1
    return count


def _find_caption(rect: fitz.Rect, text_blocks: list) -> str:
    """就近找「图x-x / Fig.」图注文本。"""
    best, best_gap = "", CAPTION_MAX_GAP + 1
    for b in text_blocks:
        text = (b[4] or "").strip().replace("\n", " ")
        if not text or len(text) > 80:
            continue
        looks_caption = bool(re.match(r"^(图|表|Fig\.?|Figure)\s*[\d一二三四五六七八九十]", text)) or \
            text.startswith("图注")
        if not looks_caption:
            continue
        gap = b[1] - rect.y1 if b[1] >= rect.y1 else rect.y0 - b[3]
        if 0 <= gap < best_gap:
            best_gap, best = gap, text
    return best




def _trim_border(img: Image.Image, pad: int = 8) -> Image.Image:
    """裁掉近白边（PPT 截图常见），让插图更紧凑。"""
    try:
        gray = img.convert("L")
        mask = gray.point(lambda p: 0 if p < 244 else 255)
        box = mask.getbbox()
        if not box:
            return img
        x0, y0, x1, y1 = box
        if (x1 - x0) < img.width * 0.35 or (y1 - y0) < img.height * 0.35:
            return img
        x0, y0 = max(0, x0 - pad), max(0, y0 - pad)
        x1, y1 = min(img.width, x1 + pad), min(img.height, y1 + pad)
        return img.crop((x0, y0, x1, y1))
    except Exception:  # noqa: BLE001
        return img

def _is_uniform(img: Image.Image) -> bool:
    """近乎纯色的条带/背景块，没有信息量。"""
    stat = ImageStat.Stat(img.convert("L"))
    return max(stat.stddev) < 4.0


def _dhash(img: Image.Image, size: int = 8) -> int:
    small = img.convert("L").resize((size + 1, size), Image.LANCZOS)
    pixels = list(small.getdata())
    bits = 0
    for row in range(size):
        for col in range(size):
            left = pixels[row * (size + 1) + col]
            right = pixels[row * (size + 1) + col + 1]
            bits = (bits << 1) | (1 if left > right else 0)
    return bits


def _hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def extract_figures(
    doc: fitz.Document,
    out_dir: str | Path,
    *,
    dpi: int = 220,
    max_figures: int = 120,
    pages: list[int] | None = None,
) -> dict[int, list[Figure]]:
    """返回 {页码(1-based): [Figure, ...]}。渲染结果写入 out_dir。"""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    result: dict[int, list[Figure]] = {}
    seen: list[int] = []
    total = 0

    page_numbers = pages if pages is not None else range(len(doc))
    for pno in page_numbers:
        page = doc[pno]
        text_blocks = [b for b in page.get_text("blocks") if b[6] == 0]
        if not text_blocks and not page.get_drawings():
            continue

        figs: list[Figure] = []
        for rect in _cluster(_collect_candidates(page)):
            if rect.width < MIN_SIDE or rect.height < MIN_SIDE:
                continue
            area_ratio = (rect.width * rect.height) / max(1.0, _page_area(page))
            if area_ratio < MIN_AREA_RATIO or area_ratio > MAX_AREA_RATIO:
                continue
            if area_ratio > MAX_CLUSTER_AREA:
                # 半页以上的区域多半是"版式块"（图+公式+正文混排），宁可不要也不塞垃圾
                continue
            if _text_coverage(rect, text_blocks) > MAX_TEXT_COVER:
                continue
            if _dense_text_blocks(rect, text_blocks) >= 2:
                continue

            aspect = rect.width / max(1.0, rect.height)
            if aspect < MIN_ASPECT or aspect > MAX_ASPECT:
                continue

            caption = _find_caption(rect, text_blocks)
            # 小且方、无字无图注 → 章节图标/装饰
            if area_ratio < 0.06 and 0.75 <= aspect <= 1.33 \
                    and _dense_text_blocks(rect, text_blocks) == 0 and not caption:
                continue

            clip = fitz.Rect(rect.x0 - FIG_PAD, rect.y0 - FIG_PAD,
                             rect.x1 + FIG_PAD, rect.y1 + FIG_PAD)
            # 把贴着图形的短文字（坐标轴标注、图内标题）一起截进来，避免文字被切断
            for block in text_blocks:
                label = (block[4] or "").strip()
                if not label or len(label) > 40 or label == caption:
                    continue
                label_rect = fitz.Rect(block[:4])
                # 不要吞进 PPT/页眉标题：顶部 12% 或过大的文字块一律跳过
                if label_rect.y1 < page.rect.height * 0.12:
                    continue
                if label_rect.height > 46 or label_rect.width > page.rect.width * 0.75:
                    continue
                if label_rect.intersects(clip):
                    merged = clip | label_rect
                    if merged.width * merged.height < page.rect.width * page.rect.height * 0.85:
                        clip = merged
            clip &= page.rect
            try:
                pix = page.get_pixmap(clip=clip, dpi=dpi)
                img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                img = _trim_border(img)
            except Exception as exc:  # noqa: BLE001
                logger.debug("渲染失败 p{}: {}", pno + 1, exc)
                continue
            if img.width < MIN_SIDE or img.height < MIN_SIDE:
                continue
            if _is_uniform(img):
                continue

            digest = _dhash(img)
            if any(_hamming(digest, old) <= 3 for old in seen):
                continue

            total += 1
            if total > max_figures:
                logger.warning("图形数量超过上限 {}，停止提取", max_figures)
                break

            filename = f"fig_p{pno + 1:02d}_{len(figs) + 1}.png"
            img.save(out / filename)
            seen.append(digest)
            figs.append(Figure(
                page=pno + 1,
                filename=filename,
                bbox=(round(clip.x0, 1), round(clip.y0, 1), round(clip.x1, 1), round(clip.y1, 1)),
                caption=caption,
                source="raster" if any(i["bbox"] == rect for i in page.get_image_info()) else "vector",
                hash=digest,
            ))

        if figs:
            result[pno + 1] = figs

    logger.info("图形提取完成：{} 页 / {} 张", len(result), total)
    return result


def extract_figures_from_pdf(pdf_path: str | Path, out_dir: str | Path, **kwargs) -> dict[int, list[Figure]]:
    doc = fitz.open(str(pdf_path))
    try:
        return extract_figures(doc, out_dir, **kwargs)
    finally:
        doc.close()

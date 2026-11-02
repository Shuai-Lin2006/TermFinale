import hashlib
import json
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import docx
import fitz
from PIL import Image
import io
from pptx import Presentation
from loguru import logger
from core.ai_vision import analyze_image_with_ai
from core import paths
from core.parsing import figures as figure_lib

IMG_DIR = str(paths.assets_dir())
paths.ensure_dirs()

FIG_DPI = 180
_DISABLE_VISION = os.getenv("TERMFINALE_DISABLE_VISION", "").strip().lower() in ("1", "true", "yes")


_VISION_CONCURRENCY = int(os.getenv("TERMFINALE_VISION_CONCURRENCY", "4") or 4)
_CAPTION_CACHE_FILE = paths.debug_dir() / "caption_cache.json"
_caption_cache: dict[str, str] | None = None


def _load_caption_cache() -> dict:
    global _caption_cache
    if _caption_cache is None:
        try:
            _caption_cache = json.loads(_CAPTION_CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            _caption_cache = {}
    return _caption_cache


def _save_caption_cache() -> None:
    try:
        paths.ensure_dirs()
        _CAPTION_CACHE_FILE.write_text(
            json.dumps(_caption_cache or {}, ensure_ascii=False), encoding="utf-8")
    except OSError as exc:
        logger.warning("图注缓存写入失败: {}", exc)


def _file_digest(path: str) -> str:
    try:
        with open(path, "rb") as fh:
            return hashlib.md5(fh.read()).hexdigest()
    except OSError:
        return ""


def resolve_captions(figs: list, on_progress=None) -> dict:
    """批量图注：页面原文优先 → 本地缓存 → 视觉模型（并发）。

    返回 {filename: caption or None}；None 表示视觉模型判定为装饰，应丢弃。
    缓存按图片内容哈希，重复生成同一份资料时不再调视觉模型。
    """
    cache = _load_caption_cache()
    result: dict = {}
    pending: list = []

    for fig in figs:
        if fig.caption:
            result[fig.filename] = fig.caption
            continue
        if _DISABLE_VISION:
            result[fig.filename] = f"第 {fig.page} 页配图"
            continue
        digest = _file_digest(os.path.join(IMG_DIR, fig.filename))
        if digest and digest in cache:
            result[fig.filename] = cache[digest] or None
        else:
            pending.append((fig, digest))

    total = len(pending)
    if on_progress and total:
        on_progress(0, total)

    def work(item):
        fig, digest = item
        caption = analyze_image_with_ai(os.path.join(IMG_DIR, fig.filename))
        return fig, digest, (caption.strip() if caption and caption.strip() else None)

    if total:
        workers = max(1, min(8, _VISION_CONCURRENCY))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(work, item) for item in pending]
            for index, future in enumerate(as_completed(futures), start=1):
                try:
                    fig, digest, caption = future.result()
                except Exception as exc:  # noqa: BLE001
                    logger.error("图注识别失败: {}", exc)
                    continue
                result[fig.filename] = caption
                if digest:
                    cache[digest] = caption or ""
                if on_progress:
                    on_progress(index, total)
        _save_caption_cache()
    return result


def clean_text_lines(slide_text: str) -> list:
    cleaned_lines = []
    for line in slide_text.split('\n'):
        line = line.strip()
        if not line: continue
        if "[[[IMAGE:" in line:
            cleaned_lines.append(line)
            continue
        if len(line) <= 3 and re.match(r'^[\d\W]+$', line): continue
        junk_keywords = ["Tel", "电话", "手机", "邮箱", "@", "Site", "微信", "QQ", "平时成绩", "期中考试", "期末考试",
                         "期末成绩", "成绩占比"]
        if len(line) < 30 and any(keyword in line for keyword in junk_keywords): continue
        line = re.sub(r'\s+', ' ', line)
        cleaned_lines.append(line)
    return cleaned_lines


def process_image(img_bytes, img_filename):
    try:
        img = Image.open(io.BytesIO(img_bytes))
        w, h = img.size
        # 🚨 放宽限制：只要大于 50x50 就保留，绝不错杀小图
        if w < 50 or h < 50: return ""
        # 放宽长宽比限制
        if w / h > 10 or h / w > 10: return ""
    except Exception:
        return ""

    img_path = os.path.join(IMG_DIR, img_filename)
    with open(img_path, 'wb') as f:
        f.write(img_bytes)

    # 🚨 核心修复：无论视觉模型识别出什么，都强制加上标签
    if _DISABLE_VISION:
        caption = ""
    else:
        try:
            caption = analyze_image_with_ai(img_path)
        except Exception as e:
            logger.error(f"图注识别异常: {e}")
            caption = ""

    if not caption or len(caption.strip()) < 2:
        caption = "原题配图"

    return f"[[[IMAGE: {img_filename} | 图注: {caption}]]]"


def extract_text_from_file(file_path: str, on_progress=None) -> list:
    file_name = os.path.basename(file_path)
    ext = file_path.lower().split('.')[-1]
    all_pages = []

    try:
        if ext == 'pptx':
            prs = Presentation(file_path)
            for index, slide in enumerate(prs.slides):
                slide_text = ""
                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text.strip():
                        slide_text += shape.text + "\n"
                    elif shape.shape_type == 13:
                        try:
                            image = shape.image
                            if len(image.blob) < 5 * 1024: continue  # 🚨 降至 5KB
                            img_filename = f"slide{index + 1}_{len(os.listdir(IMG_DIR)) + 1}.{image.ext.lower()}"
                            img_tag = process_image(image.blob, img_filename)
                            if img_tag: slide_text += f"\n{img_tag}\n"
                        except:
                            pass
                if slide_text.strip():
                    cleaned = "\n".join(clean_text_lines(slide_text))
                    if cleaned.strip(): all_pages.append(f"【《{file_name}》第 {index + 1} 页】\n{cleaned}")

        elif ext == 'pdf':
            doc = fitz.open(file_path)
            try:
                # 先把整份文档的图形区域渲染出来（矢量图也能出），再按 y 坐标插回文本流
                figs_by_page = figure_lib.extract_figures(doc, IMG_DIR, dpi=FIG_DPI)
                all_figs = [f for group in figs_by_page.values() for f in group]
                captions = resolve_captions(all_figs, on_progress)
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    text_blocks = [b for b in page.get_text("blocks") if b[6] == 0]

                    items = [(b[1], b[0], b[4]) for b in text_blocks]
                    for fig in figs_by_page.get(page_num + 1, []):
                        caption = captions.get(fig.filename)
                        if caption is None:  # 装饰图，丢弃
                            continue
                        items.append((fig.bbox[1], fig.bbox[0],
                                      f"[[[IMAGE: {fig.filename} | 图注: {caption}]]]"))

                    items.sort(key=lambda item: (item[0], item[1]))
                    page_text = "\n".join(item[2] for item in items)

                    if page_text.strip():
                        cleaned = "\n".join(clean_text_lines(page_text))
                        if cleaned.strip():
                            all_pages.append(f"【《{file_name}》第 {page_num + 1} 页】\n{cleaned}")
            finally:
                doc.close()

        elif ext in ['doc', 'docx']:
            doc = docx.Document(file_path)
            text_content = []
            for para in doc.paragraphs:
                if para.text.strip(): text_content.append(para.text)
            for img_index, rel in enumerate(doc.part.rels.values()):
                if "image" in rel.reltype:
                    try:
                        image_bytes = rel.target_part.blob
                        if len(image_bytes) < 5 * 1024: continue
                        img_filename = f"doc_{img_index}.{rel.target_part.partname.split('.')[-1]}"
                        img_tag = process_image(image_bytes, img_filename)
                        if img_tag: text_content.append(img_tag)
                    except:
                        pass
            cleaned = "\n".join(clean_text_lines("\n".join(text_content)))
            if cleaned.strip(): all_pages.append(f"【《{file_name}》全文】\n{cleaned}")

        return all_pages
    except Exception as e:
        logger.error(f"解析失败: {e}")
        return []
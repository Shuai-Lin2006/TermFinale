import os
import re
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


def _figure_caption(fig) -> str | None:
    """图注：优先用页面上的原文标题；否则调视觉模型。

    视觉模型判定"无内容"（返回空）时返回 None，表示这张图是装饰，应当丢弃。
    离线模式（TERMFINALE_DISABLE_VISION=1）直接给兜底文案，不联网。
    """
    if fig.caption:
        return fig.caption
    if _DISABLE_VISION:
        return f"第 {fig.page} 页配图"
    caption = analyze_image_with_ai(os.path.join(IMG_DIR, fig.filename))
    if not caption or not caption.strip():
        return None
    return caption


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


def extract_text_from_file(file_path: str) -> list:
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
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    text_blocks = [b for b in page.get_text("blocks") if b[6] == 0]

                    items = [(b[1], b[0], b[4]) for b in text_blocks]
                    for fig in figs_by_page.get(page_num + 1, []):
                        caption = _figure_caption(fig)
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
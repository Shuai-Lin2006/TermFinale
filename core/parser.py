import hashlib
import json
import os
import re
from pathlib import Path
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
OCR_DPI = 120
_OCR_CACHE_FILE = paths.debug_dir() / "ocr_cache.json"
_ocr_cache: dict | None = None
_OCR_PROMPT = (
    "把这张图片里的所有文字按阅读顺序完整转录为纯文本。\n"
    "要求：1) 不要总结、不要解释、不要遗漏；2) 保留题号、选项、编号与分行；"
    "3) 公式用 $...$ 包裹；4) 只输出转录结果。"
)


def _load_ocr_cache() -> dict:
    global _ocr_cache
    if _ocr_cache is None:
        try:
            _ocr_cache = json.loads(_OCR_CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            _ocr_cache = {}
    return _ocr_cache


def _save_ocr_cache() -> None:
    try:
        paths.ensure_dirs()
        _OCR_CACHE_FILE.write_text(json.dumps(_ocr_cache or {}, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def _clean_ocr_text(text: str) -> str:
    """qwen-vl-ocr 常返回 ```html 包裹的 HTML，这里转成纯文本。"""
    import html as html_lib

    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text).strip()
    if "<" in text and ">" in text:
        text = re.sub(r"</p>|<br\s*/?>|</div>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", "", text)
        text = html_lib.unescape(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _ocr_page(page, model: str | None = None) -> str:
    """把一页渲染成图，交给视觉模型转录成文字。"""
    from openai import OpenAI
    from core.config import get_key

    pix = page.get_pixmap(dpi=OCR_DPI)
    png = pix.tobytes("png")
    digest = hashlib.md5(png).hexdigest()
    cache = _load_ocr_cache()
    if digest in cache:
        return cache[digest]

    client = OpenAI(api_key=get_key("DASHSCOPE_API_KEY", "sk-not-configured"),
                    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")
    import base64
    b64 = base64.b64encode(png).decode()
    ocr_model = model or os.getenv("TERMFINALE_OCR_MODEL", "qwen-vl-ocr")
    resp = client.chat.completions.create(
        model=ocr_model,
        max_tokens=4096,
        messages=[{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            {"type": "text", "text": _OCR_PROMPT},
        ]}],
    )
    text = _clean_ocr_text(resp.choices[0].message.content or "")
    cache[digest] = text
    _save_ocr_cache()
    return text


def _ocr_pages(doc, on_progress=None) -> dict:
    """扫描件整本 OCR：返回 {页码(1-based): 文本}。"""
    pages = list(range(len(doc)))
    total = len(pages)
    out: dict = {}
    if on_progress:
        on_progress(0, total, "ocr")

    def work(pno):
        try:
            return pno, _ocr_page(doc[pno])
        except Exception as exc:  # noqa: BLE001
            logger.error("OCR 第 {} 页失败: {}", pno + 1, exc)
            return pno, ""

    workers = max(1, min(4, int(os.getenv("TERMFINALE_VISION_CONCURRENCY", "4") or 4)))
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(work, pno): pno for pno in pages}
        for future in as_completed(futures):
            pno, text = future.result()
            out[pno + 1] = text
            done += 1
            if on_progress:
                on_progress(done, total, "ocr")
    return out
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
        on_progress(0, total, "caption")

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
                    on_progress(index, total, "caption")
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




IMAGE_EXTS = {'jpg', 'jpeg', 'png', 'webp', 'bmp'}


def _ocr_image_file(file_path: str) -> str:
    """拍照/截图导入：把图片里的文字转成 Markdown 文本。"""
    import base64
    from openai import OpenAI
    from core.config import get_key

    data = Path(file_path).read_bytes()
    b64 = base64.b64encode(data).decode()
    mime = "image/png" if file_path.lower().endswith(".png") else "image/jpeg"
    client = OpenAI(api_key=get_key("DASHSCOPE_API_KEY", "sk-not-configured"),
                    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")
    resp = client.chat.completions.create(
        model=os.getenv("TERMFINALE_OCR_MODEL", "qwen-vl-ocr"),
        max_tokens=4096,
        messages=[{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
            {"type": "text", "text": ("把图片里的所有文字按阅读顺序转录为 Markdown。保留标题、编号、表格与公式。"
                                      "普通文字用纯文本，不要包进 $\\text{}$ 或 aligned；只有真正的数学公式才用 $...$。"
                                      "不要总结、不要解释、不要遗漏。")},
        ]}],
    )
    return _clean_ocr_text(resp.choices[0].message.content or "")

def extract_text_from_file(file_path: str, on_progress=None) -> list:
    file_name = os.path.basename(file_path)
    ext = file_path.lower().split('.')[-1]
    all_pages = []

    try:
        if ext in IMAGE_EXTS:
            text = _ocr_image_file(file_path)
            if text.strip():
                all_pages.append(f"【《{file_name}》 图片转写】\n{text}")
        elif ext in ('mp3', 'wav', 'm4a', 'aac', 'flac', 'ogg', 'amr'):
            from core.asr import transcribe_audio
            text = transcribe_audio(file_path, on_progress=on_progress)
            if text.strip():
                all_pages.append(f"【《{file_name}》 音频转写】\n{text}")
        elif ext in ('txt', 'md'):
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
            if text.strip():
                all_pages.append(f"【《{file_name}》】\n{text}")
        elif ext == 'pptx':
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
                scanned = sum(len(doc[i].get_text().strip()) for i in range(len(doc))) < 50
                ocr_map: dict = {}
                if scanned:
                    logger.info("检测到扫描版 PDF（无文字层），启用视觉 OCR")
                    ocr_map = _ocr_pages(doc, on_progress)
                    figs_by_page, captions = {}, {}
                else:
                    figs_by_page = figure_lib.extract_figures(doc, IMG_DIR, dpi=FIG_DPI)
                    all_figs = [f for group in figs_by_page.values() for f in group]
                    captions = resolve_captions(all_figs, on_progress)

                for page_num in range(len(doc)):
                    if ocr_map:
                        body = ocr_map.get(page_num + 1, "").strip()
                        if body:
                            all_pages.append(f"【《{file_name}》第 {page_num + 1} 页】\n{body}")
                        continue

                    page = doc[page_num]
                    text_blocks = [b for b in page.get_text("blocks") if b[6] == 0]

                    items = [(b[1], b[0], b[4]) for b in text_blocks]
                    for fig in figs_by_page.get(page_num + 1, []):
                        caption = captions.get(fig.filename)
                        if caption is None:  # 装饰图，丢弃
                            continue
                        items.append((fig.bbox[1], fig.bbox[0],
                                      f"[[[IMAGE: {fig.filename} | 图注: {caption}（第 {page_num + 1} 页）]]]"))

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
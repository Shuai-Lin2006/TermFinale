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
from core.quality.text_quality import is_low_quality_page

IMG_DIR = str(paths.assets_dir())
paths.ensure_dirs()

# 解析行为变更时递增：解析缓存 key 会带上它，旧缓存自动失效。
PARSER_VERSION = "2026-11-08.5"

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




def _find_soffice() -> str | None:
    """Finder 启动 App 时 PATH 往往不含 Homebrew，必须显式找 LibreOffice。"""
    import shutil
    candidates = [
        shutil.which("soffice"), shutil.which("libreoffice"),
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
        "/opt/homebrew/bin/soffice", "/usr/local/bin/soffice",
    ]
    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return candidate
    return None


def _sort_pages_by_number(all_pages: list) -> list:
    def _key(block: str) -> int:
        m = re.search(r"第\s*(\d+)\s*页", block or "")
        return int(m.group(1)) if m else 10 ** 9
    return sorted(all_pages, key=_key)


def _fill_missing_ppt_pages(file_path: str, file_name: str, all_pages: list, total: int) -> list:
    """对 PPT 中没有文字的页：整本转 PDF，逐页渲染后 OCR 回填。

    回填后必须保证 1..total 每页都有条目（哪怕只是占位），否则覆盖率分母会失真。
    """
    present = set()
    for block in all_pages:
        m = re.search(r"第\s*(\d+)\s*页", block)
        if not m:
            continue
        plain = re.sub(r"\[\[\[IMAGE:.*?\]\]\]", "", block, flags=re.S)
        if len(plain.strip()) > 12:
            present.add(int(m.group(1)))
    missing = [n for n in range(1, total + 1) if n not in present]
    if not missing:
        return _sort_pages_by_number(all_pages)

    soffice = _find_soffice()
    if not soffice:
        logger.warning("未找到 LibreOffice，PPT 图片页无法 OCR：{}", file_name)
        for n in missing:
            all_pages.append(f"【《{file_name}》第 {n} 页】\n[本页 OCR 未执行：未安装 LibreOffice]")
        return _sort_pages_by_number(all_pages)

    try:
        import subprocess, tempfile, fitz
        outdir = tempfile.mkdtemp(prefix="pptocr_")
        proc = subprocess.run(
            [soffice, "--headless", "--convert-to", "pdf", "--outdir", outdir, file_path],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=240)
        pdfs = [os.path.join(outdir, x) for x in os.listdir(outdir) if x.lower().endswith(".pdf")]
        if proc.returncode != 0 or not pdfs:
            logger.warning("PPT 转 PDF 失败 rc={} pdfs={} file={}", proc.returncode, len(pdfs), file_name)
            for n in missing:
                all_pages.append(f"【《{file_name}》第 {n} 页】\n[本页 OCR 失败：PPT 转 PDF 未成功]")
            return _sort_pages_by_number(all_pages)
        doc = fitz.open(pdfs[0])
        filled = failed = 0
        try:
            for n in missing:
                if n > len(doc):
                    continue
                txt = ""
                for _attempt in (1, 2):
                    try:
                        txt = _clean_ocr_text(_ocr_page(doc[n - 1]) or "")
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("PPT 第 {} 页 OCR 异常（第 {} 次）: {}", n, _attempt, str(exc)[:80])
                        txt = ""
                    if txt.strip():
                        break
                if txt.strip():
                    all_pages.append(f"【《{file_name}》第 {n} 页】\n{txt.strip()}")
                    filled += 1
                else:
                    # OCR 失败时再用视觉描述兜底：至少把图里的结构/公式讲清楚
                    desc = ""
                    try:
                        import tempfile
                        pix = doc[n - 1].get_pixmap(dpi=140)
                        _tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                        _tmp.write(pix.tobytes("png")); _tmp.close()
                        desc = _clean_slide_ocr(analyze_image_with_ai(_tmp.name))
                        try: os.unlink(_tmp.name)
                        except OSError: pass
                    except Exception as _e:  # noqa: BLE001
                        logger.warning("整页视觉兜底失败 page={} err={}", n, str(_e)[:80])
                    if desc.strip():
                        all_pages.append(f"【《{file_name}》第 {n} 页】\n【图示页】\n{desc.strip()}")
                        filled += 1
                    else:
                        all_pages.append(f"【《{file_name}》第 {n} 页】\n[本页 OCR 未识别出文字]")
                        failed += 1
        finally:
            doc.close()
        logger.info("PPT 图片页回填：{} 页成功 / {} 页失败（共缺 {} 页）", filled, failed, len(missing))
    except Exception as e:
        logger.warning("PPT 图片页 OCR 回填失败: {}", str(e)[:100])
        for n in missing:
            all_pages.append(f"【《{file_name}》第 {n} 页】\n[本页 OCR 失败：{str(e)[:60]}]")
    return _sort_pages_by_number(all_pages)


def _clean_slide_ocr(text: str) -> str:
    """清洗整页 OCR：去校名/页眉/孤立符号，合并断行，保留公式。"""
    if not text:
        return ""
    out = []
    for line in text.splitlines():
        t = line.strip()
        if not t:
            continue
        if any(k in t for k in ("大学", "学院", "University", "College")):
            continue
        if t.isdigit() and len(t) <= 3:
            continue
        out.append(t)
    return "\n".join(out)


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
        # 空/失败结果绝不命中缓存：旧版本曾把 "" 永久写进去，图就再也回不来了
        if digest and cache.get(digest):
            result[fig.filename] = cache[digest]
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
                if digest and caption:
                    cache[digest] = caption
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


def process_image(img_bytes, img_filename, with_caption=True, caption_text=None):
    try:
        img = Image.open(io.BytesIO(img_bytes))
        w, h = img.size
        # 🚨 放宽限制：只要大于 50x50 就保留，绝不错杀小图
        if w < 50 or h < 50: return ""
        # 放宽长宽比限制
        if w / h > 10 or h / w > 10: return ""
    except Exception:
        return ""

    import hashlib as _hashlib
    img_filename = f"{_hashlib.md5(img_bytes).hexdigest()[:16]}.{img_filename.rsplit('.', 1)[-1]}"
    try:
        probe = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        w, h = probe.size
        if w / max(1, h) > 8 or h / max(1, w) > 8:
            return ""
        small = probe.resize((24, 24))
        colors = small.getcolors(24 * 24) or []
        if colors:
            dominant = max(colors)[0] / (24 * 24)
            if dominant > 0.96:
                return ""
    except Exception:
        pass

    img_path = os.path.join(IMG_DIR, img_filename)
    with open(img_path, 'wb') as f:
        f.write(img_bytes)

    # 🚨 核心修复：无论视觉模型识别出什么，都强制加上标签
    if caption_text:
        caption = caption_text
    elif _DISABLE_VISION or not with_caption:
        caption = ""
    else:
        try:
            caption = analyze_image_with_ai(img_path)
        except Exception as e:
            logger.error(f"图注识别异常: {e}")
            caption = ""

    if not caption or len(caption.strip()) < 2:
        caption = "PPT 图示" if not with_caption else "原题配图"

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
            total_slides = len(prs.slides)
            for index, slide in enumerate(prs.slides):
                if on_progress:
                    on_progress(index, total_slides, "slide")
                slide_text = ""
                candidates = []
                page_images = []
                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text.strip():
                        slide_text += shape.text + "\n"
                    elif shape.shape_type == 13:
                        try:
                            image = shape.image
                            if len(image.blob) < 5 * 1024:
                                continue
                            probe = Image.open(io.BytesIO(image.blob))
                            w, h = probe.size
                            if w < 160 or h < 120 or w * h < 40000:
                                continue
                            try:
                                ratio = (float(shape.width) * float(shape.height)) / (float(prs.slide_width) * float(prs.slide_height))
                            except Exception:
                                ratio = 0.0
                            if ratio > 0.65:
                                # 整页图不作为正文配图，但正文过短时要拿它做 OCR
                                page_images.append((w * h, image.blob, image.ext.lower()))
                                continue
                            candidates.append((w * h, image.blob, image.ext.lower()))
                        except Exception:
                            pass
                # 每页最多保留 2 张最大的图，避免把 logo/装饰图当正文配图
                candidates.sort(key=lambda x: x[0], reverse=True)
                slide_title = next((ln.strip() for ln in slide_text.splitlines() if ln.strip()), "")
                # 注意：变量名不能叫 ext——它会覆盖外层文件扩展名，导致后面的
                # `if ext == 'pptx'` 永远为假，整本 OCR 回填从不执行（85 页缺 8 页的根因）。
                for _area, blob, img_ext in candidates[:2]:
                    try:
                        img_filename = f"slide{index + 1}_{len(os.listdir(IMG_DIR)) + 1}.{img_ext}"
                        cap = f"{slide_title}（第 {index + 1} 页）" if slide_title else f"第 {index + 1} 页图示"
                        img_tag = process_image(blob, img_filename, with_caption=False, caption_text=cap)
                        if img_tag:
                            slide_text += f"\n{img_tag}\n"
                    except Exception:
                        pass
                # 图片/电路图页：正文过短时也要看整页图，不能只靠几个标题字。
                _plain = re.sub(r"\[\[\[IMAGE:.*?\]\]\]", "", slide_text, flags=re.S).strip()
                _ocr_candidates = candidates or page_images
                if _ocr_candidates and len(_plain) < 80:
                    try:
                        import tempfile
                        _best = max(_ocr_candidates, key=lambda x: x[0])
                        _blob = _best[1]; _img_ext = _best[2]
                        _tmp = tempfile.NamedTemporaryFile(delete=False, suffix="." + _img_ext)
                        _tmp.write(_blob); _tmp.close()
                        _ocr = _clean_slide_ocr(analyze_image_with_ai(_tmp.name))
                        try: os.unlink(_tmp.name)
                        except OSError: pass
                        if _ocr and _ocr.strip() and _ocr.strip() not in slide_text:
                            slide_text += "\n【图示内容】\n" + _ocr.strip()
                    except Exception as _e:
                        logger.warning("图片页 OCR 失败: {}", str(_e)[:80])
                if slide_text.strip():
                    cleaned = "\n".join(clean_text_lines(slide_text))
                    if cleaned.strip(): all_pages.append(f"【《{file_name}》第 {index + 1} 页】\n{cleaned}")

        if ext == 'pptx':
            try:
                all_pages = _fill_missing_ppt_pages(file_path, file_name, all_pages, len(prs.slides))
            except Exception:
                pass

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
                    _fig_prefix = hashlib.md5(file_path.encode("utf-8", "ignore")).hexdigest()[:8]
                    figs_by_page = figure_lib.extract_figures(
                        doc, IMG_DIR, dpi=FIG_DPI, prefix=_fig_prefix)
                    all_figs = [f for group in figs_by_page.values() for f in group]
                    captions = resolve_captions(all_figs, on_progress)

                for page_num in range(len(doc)):
                    if ocr_map:
                        body = ocr_map.get(page_num + 1, "").strip()
                        if body:
                            all_pages.append(f"【《{file_name}》第 {page_num + 1} 页】\n{body}")
                        else:
                            all_pages.append(f"【《{file_name}》第 {page_num + 1} 页】\n[本页 OCR 未识别出文字]")
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

                    # 混合扫描件：这一页没有文字层，但有图/矢量内容 → 单页 OCR。
                    plain = re.sub(r"\[\[\[IMAGE:.*?\]\]\]", "", page_text, flags=re.S).strip()
                    # 有文字层但文本层是公式乱码/单字母串：同样单页 OCR 回退。
                    if plain and is_low_quality_page(plain):
                        ocr_txt = ""
                        try:
                            ocr_txt = _clean_ocr_text(_ocr_page(page) or "")
                        except Exception as exc:  # noqa: BLE001
                            logger.warning("PDF 第 {} 页乱码 OCR 异常: {}", page_num + 1, str(exc)[:80])
                        if ocr_txt.strip() and len(ocr_txt) >= max(20, int(len(plain) * 0.45)):
                            logger.info("PDF 第 {} 页文本层乱码，已用 OCR 替换（{}→{} 字）",
                                        page_num + 1, len(plain), len(ocr_txt))
                            # 只保留图片标签；旧文本层是乱码，不能再进正文/证据库
                            _imgs = "\n".join(re.findall(r"\[\[\[IMAGE:.*?\]\]\]", page_text, re.S))
                            page_text = ocr_txt + ("\n" + _imgs if _imgs else "")
                    if not plain and (page.get_images() or page.get_drawings()):
                        ocr_txt = ""
                        for _attempt in (1, 2):
                            try:
                                ocr_txt = _clean_ocr_text(_ocr_page(page) or "")
                            except Exception as exc:  # noqa: BLE001
                                logger.warning("PDF 第 {} 页 OCR 异常（第 {} 次）: {}",
                                               page_num + 1, _attempt, str(exc)[:80])
                                ocr_txt = ""
                            if ocr_txt.strip():
                                break
                        if ocr_txt.strip():
                            page_text = ocr_txt + ("\n" + page_text if page_text.strip() else "")
                        else:
                            page_text += "\n[本页 OCR 未识别出文字]"

                    cleaned = "\n".join(clean_text_lines(page_text))
                    if cleaned.strip():
                        all_pages.append(f"【《{file_name}》第 {page_num + 1} 页】\n{cleaned}")
                    else:
                        all_pages.append(f"【《{file_name}》第 {page_num + 1} 页】\n[本页无可提取文字]")
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
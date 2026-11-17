import os
import base64
from openai import OpenAI
from loguru import logger
from core.config import get_key, load_env, vision_model

load_env()

# 视觉模型连续失败就本进程内熔断：每次失败要等 25s 超时，
# 一个 8 页讲义能白等两分钟。熔断后按“无图”处理（fail-open），不影响正文。
_VISION_FAILS = 0
_VISION_OFF = False
VISION_FAIL_LIMIT = 2


def reset_vision_breaker() -> None:
    global _VISION_FAILS, _VISION_OFF
    _VISION_FAILS = 0
    _VISION_OFF = False


def vision_available() -> bool:
    return not _VISION_OFF


def _note_vision_failure() -> None:
    global _VISION_FAILS, _VISION_OFF
    _VISION_FAILS += 1
    if _VISION_FAILS >= VISION_FAIL_LIMIT and not _VISION_OFF:
        _VISION_OFF = True
        logger.warning(f"视觉模型连续 {_VISION_FAILS} 次失败，本次运行不再尝试识图（正文不受影响）")

# 🚨 阿里云百炼 OpenAI 兼容接口
client = OpenAI(
    api_key=get_key("DASHSCOPE_API_KEY", "sk-not-configured"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

def analyze_image_with_ai(image_path: str) -> str:
    logger.info(f"正在调用视觉模型识别图片: {os.path.basename(image_path)}")
    try:
        # 压缩后送模型：原图/GIF 动辄数 MB，会把单次识别拖到几十秒
        import io
        from PIL import Image
        img = Image.open(image_path).convert("RGB")
        if max(img.size) > 1280:
            img.thumbnail((1280, 1280), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=82)
        img_base = base64.b64encode(buf.getvalue()).decode('utf-8')
        ext = "jpeg"

        # 可用 QWEN_VL_MODEL 覆盖；默认 qwen-vl-max（旧值 qwen3.8-max 会 404）
        response = client.chat.completions.create(
            model=vision_model(),
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/{ext};base64,{img_base}"}
                        },
                        {
                            "type": "text",
                            "text": """
你是一个全学科（理、工、文、医、商、法）的顶尖期末复习教研专家。
请仔细观察这张图片，自动判断它属于哪个学科的知识，并生成一段精准的图注。要求如下：
1. 【理工科】（如化学方程式、电路图、物理受力图、数学几何图）：请准确描述反应物与生成物、电路连接方式、受力方向或几何关系。
2. 【医学/生物】（如解剖图、细胞结构、病理切片）：请准确指出器官名称、组织类型、细胞结构或病变特征。
3. 【人文社科】（如历史地图、法律逻辑图、经济学图表）：请描述地图版图变迁、法律权利义务关系、或图表揭示的经济趋势。
4. 【普通截图/无关紧要的装饰】：如果是纯文字截图、校徽、小人动画等没有实质知识的图片，请只回复'无'。
请用一句话（不超过40字）给出极其专业的图注，直接输出内容，不要加任何前缀和解释。
                            """
                        }
                    ]
                }
            ],
            temperature=0.1,
            timeout=25,
        )

        caption = response.choices[0].message.content.strip()
        if "无" in caption or len(caption) < 3:
            return ""
        return caption
    except Exception as e:
        # 🚨 这里打印出真正的报错原因，比如 Key 错误、模型不存在、欠费等
        logger.error(f"视觉模型识别失败，完整报错: {e}")
        return ""

def analyze_teaching_figure(image_path: str) -> str:
    """图注/图源判定专用：只返回可进讲义的实质教学图描述。

    与问答用的通用识图分开，避免把装饰色块、背景、校徽当成知识图。
    """
    global _VISION_FAILS
    if _VISION_OFF:
        return ""
    logger.info(f"正在判定教学图: {os.path.basename(image_path)}")
    try:
        import io
        from PIL import Image
        img = Image.open(image_path).convert("RGB")
        if max(img.size) > 1280:
            img.thumbnail((1280, 1280), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=82)
        img_base = base64.b64encode(buf.getvalue()).decode("utf-8")
        response = client.chat.completions.create(
            model=vision_model(),
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_base}"}},
                    {"type": "text", "text": """
你是教材插图编辑。判断这张图能否作为讲义的实质教学内容图，并写一句准确图注（不超过40字）。
- 电路图、结构图、流程图、受力图、几何图、表格、显微图、实物元件/现象照片：可以，准确描述它表达的知识；
- 纯色/渐变背景、装饰图案、校徽、logo、纯文字截图、空白模板、抽象色块：一律只回复“无”；
- 看不清具体结构、无法确认内容：只回复“无”；
- 不要猜测学科，不要编造图里没有的元件、数值或关系。
直接输出图注或“无”，不要前缀。
"""}]}],
            temperature=0.1,
            timeout=25,
        )
        caption = (response.choices[0].message.content or "").strip().strip("。. ")
        _VISION_FAILS = 0
        if caption in ("无", "无图", "none", "None") or len(caption) < 3:
            return ""
        return caption
    except Exception as e:
        logger.error(f"教学图识别失败，完整报错: {e}")
        _note_vision_failure()
        return ""


def verify_teaching_figure(image_path: str, *, section_title: str, context: str = "", caption: str = "") -> bool:
    """Ask the vision model whether a candidate figure directly supports a section.

    Fail-open: API/parse failure returns True so a temporary vision outage does
    not silently remove all figures; caption/page filters still apply.
    """
    try:
        import io
        from PIL import Image
        img = Image.open(image_path).convert("RGB")
        if max(img.size) > 1280:
            img.thumbnail((1280, 1280), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=82)
        img_base = base64.b64encode(buf.getvalue()).decode("utf-8")
        response = client.chat.completions.create(
            model=vision_model(),
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_base}"}},
                    {"type": "text", "text": f"""
这张图是否直接支持下面这一节的讲解？只判断图文是否对应，不要评价图片美观。
小节标题：{section_title}
小节摘要：{context[:700] or '无'}
图注：{caption[:120] or '无'}
只回答 YES 或 NO。
"""},
                ],
            }],
            temperature=0.0,
            max_tokens=8,
            timeout=25,
        )
        answer = (response.choices[0].message.content or "").strip().upper()
        if answer.startswith("NO"):
            return False
        if answer.startswith("YES"):
            return True
        return True
    except Exception as e:
        logger.error(f"图文相关性复核失败，按保留处理: {e}")
        return True


def read_formula_latex(image_path: str) -> str:
    """Formula OCR fallback: ask the vision model for LaTeX only."""
    logger.info("正在识别公式: " + os.path.basename(image_path))
    try:
        import io
        from PIL import Image
        img = Image.open(image_path).convert("RGB")
        if max(img.size) > 1600:
            img.thumbnail((1600, 1600), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        img_base = base64.b64encode(buf.getvalue()).decode("utf-8")
        response = client.chat.completions.create(
            model=vision_model(),
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64," + img_base}},
                    {"type": "text", "text": "识别这张公式图片，只输出 LaTeX 源码，不要 $$、不要 Markdown、不要解释。看不清就输出空。"},
                ],
            }],
            temperature=0.0,
            max_tokens=300,
            timeout=30,
        )
        latex = (response.choices[0].message.content or "").strip()
        if latex.startswith("$$") and latex.endswith("$$"):
            latex = latex[2:-2].strip()
        if latex.startswith("$") and latex.endswith("$"):
            latex = latex[1:-1].strip()
        return latex
    except Exception as exc:
        logger.error("公式识别失败: " + str(exc))
        return ""


def read_table_markdown(image_path: str) -> str:
    """Image/table fallback: ask the vision model for Markdown tables only."""
    logger.info("正在识别表格: " + os.path.basename(image_path))
    try:
        import io
        from PIL import Image
        img = Image.open(image_path).convert("RGB")
        if max(img.size) > 1800:
            img.thumbnail((1800, 1800), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        img_base = base64.b64encode(buf.getvalue()).decode("utf-8")
        response = client.chat.completions.create(
            model=vision_model(),
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64," + img_base}},
                    {"type": "text", "text": "只提取图中的表格，输出 GitHub Markdown 管道表；不要解释、不要周围正文。没有表格就输出空。"},
                ],
            }],
            temperature=0.0,
            max_tokens=1800,
            timeout=40,
        )
        text = (response.choices[0].message.content or "").strip()
        if "|" not in text:
            return ""
        return text
    except Exception as exc:
        logger.error("表格识别失败: " + str(exc))
        return ""

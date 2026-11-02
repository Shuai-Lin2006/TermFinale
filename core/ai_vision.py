import os
import base64
from openai import OpenAI
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

# 🚨 阿里云百炼 OpenAI 兼容接口
client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

def analyze_image_with_ai(image_path: str) -> str:
    logger.info(f"正在调用视觉模型识别图片: {os.path.basename(image_path)}")
    try:
        with open(image_path, "rb") as f:
            img_base = base64.b64encode(f.read()).decode('utf-8')

        ext = image_path.split('.')[-1].lower()
        if ext == 'jpg': ext = 'jpeg'

        # 可用 QWEN_VL_MODEL 覆盖；默认 qwen-vl-max（旧值 qwen3.8-max 会 404）
        response = client.chat.completions.create(
            model=os.getenv("QWEN_VL_MODEL", "qwen-vl-max"),
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
            temperature=0.1
        )

        caption = response.choices[0].message.content.strip()
        if "无" in caption or len(caption) < 3:
            return ""
        return caption
    except Exception as e:
        # 🚨 这里打印出真正的报错原因，比如 Key 错误、模型不存在、欠费等
        logger.error(f"视觉模型识别失败，完整报错: {e}")
        return "原题配图"
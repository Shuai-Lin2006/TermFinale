import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from loguru import logger

# 1. 加载保险箱里的钥匙
load_dotenv()

# 2. 初始化 DeepSeek 客户端
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)


# 3. 核心功能：让 AI 提取知识点
def extract_knowledge_with_ai(raw_text: str) -> list:
    """
    调用大模型，把杂乱的 PPT 文本提取成结构化的知识点 JSON
    """
    logger.info("正在呼叫 AI 大脑进行结构化提取...")

    system_prompt = """
    你是一个顶尖的大学期末复习教研专家。
    用户会给你一段从 PPT 中提取的杂乱文本。请你：
    1. 忽略所有无意义的符号乱码和排版错误。
    2. 提取出真正的知识点，并修复排版导致的语病。
    3. 判断该知识点的难度（1-5的整数，1最简单，5最难）。
    4. 严格按照以下 JSON 格式返回，不要包含任何其他的废话或Markdown标记：
    {
        "knowledge_points": [
            {"title": "知识点名称", "difficulty": 3, "summary": "一句话总结该考点"}
        ]
    }
    5.极其重要：绝对不要提取“考试课”、“作业”、“分数比例”、“老师姓名”等非专业知识点的词汇。如果这段文本只是废话（
    没有实质的考点），请直接返回{"knowledge_points": []}。
    """

    try:
        # 发送请求给 AI
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": raw_text}
            ],
            response_format={"type": "json_object"},  # 强制 AI 吐 JSON
            temperature=0.3
        )

        result_text = response.choices[0].message.content
        result_json = json.loads(result_text)

        logger.success("AI 解析成功！")
        return result_json.get("knowledge_points", [])

    except Exception as e:
        logger.error(f"AI 调用失败: {e}")
        return []


# 4. 测试区
if __name__ == "__main__":
    test_text = """
    【第 50 页】
    例1-9. 河水自西向东流动,速度为10 kmh-1. 一轮船在水中航行, 船相对于河水的航向为北偏西30, 相对
    于河水的航速为20 kmh-1. 此时风向为由东向西,风速为10 kmh-1.
    """

    print("正在测试 AI 接口，请稍等...")
    kps = extract_knowledge_with_ai(test_text)

    if kps:
        print("\n========= AI 提取的知识点 =========")
        print(json.dumps(kps, indent=4, ensure_ascii=False))
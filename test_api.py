import os
from zhipuai import ZhipuAI
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("ZHIPU_API_KEY")
client = ZhipuAI(api_key=api_key)

try:
    response = client.chat.completions.create(
        model="glm-4v",
        messages=[{"role": "user", "content": "请回复：连接成功！"}]
    )
    print("✅ API Key 验证成功！智谱说：", response.choices[0].message.content)
except Exception as e:
    print("❌ 验证失败，错误信息：", e)
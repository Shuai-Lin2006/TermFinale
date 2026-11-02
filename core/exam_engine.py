import os
import time
from openai import OpenAI
from dotenv import load_dotenv
from loguru import logger

load_dotenv()
client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")


def call_ai_with_retry(sys_prompt, user_content, temp=0.1):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": user_content}],
                temperature=temp, max_tokens=4096, timeout=90
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.warning(f"API 请求失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1: return ""
            time.sleep(3)


def generate_logic_analysis(raw_text: str, mode: str) -> str:
    if mode == "mindmap":
        sys_prompt = """
        【系统角色】知识架构师。
        【任务】生成 Mermaid 思维导图。总节点不超过 15 个，单节点不超过 10 字。
        🚨 严禁任何废话！不要输出任何解释，直接输出代码！
        🚨 必须严格使用 `graph TD` 语法。如果节点包含中文或标点，请使用双引号包裹，例如 A["核心 (重点)"]。
        🚨 格式必须完全如下：
        ```mermaid
        graph TD
            A["第一章"] --> B["第一节"]
            A --> C["第二节"]
        ```
        """
    else:
        sys_prompt = """
        【系统角色】顶尖学术推演专家。
        【任务】请根据资料，梳理出极富深度的【因果逻辑链】。
        🚨【严禁废话】绝对不准出现互动废话！直接输出逻辑！
        【结构要求】：
        ### 📌 宏观架构
        ### 🔗 逻辑推演链
        ### 🧠 认知避坑
        【强制溯源】：必须在每个核心推演结束时标注：[出处：《文件名》第X页]。
        """
    return call_ai_with_retry(sys_prompt, raw_text, temp=0.2)


def generate_extraction(raw_text: str, extract_type: str, with_answer: bool = True) -> str:
    if extract_type == "nouns":
        sys_prompt = "【任务】提取核心名词。完整提取所有！严格用格式：\n- **名词**：大白话解释。 [出处：《文件名》第X页]"
    elif extract_type == "points":
        sys_prompt = "【任务】提取核心考点。完整提取所有！必须包含实战意义：\n### 考点：XXX\n- **考察方式**：...\n- **拿分套路**：...\n- [出处：《文件名》第X页]"
    else:
        ans_req = "必须在每道题下方附带【答案】和【解析】。" if with_answer else "仅输出题目。"
        sys_prompt = f"""
        【系统角色】资深资料提取专家。
        【任务】请从提供的资料中，原封不动地提取出所有的【原题】。
        🚨 1. 严禁瞎编！资料里没有的题绝对不准出！如果只有计算题，就不准出选择题！
        🚨 2. 图片兜底规则：如果原题依赖配图，请在题目末尾写上：`[📷 原题配图详见资料对应页]`。
        🚨 3. 选项换行，公式用 `$` 包裹。
        {ans_req}
        """
    return call_ai_with_retry(sys_prompt, raw_text, temp=0.2)


def generate_exam_paper(raw_text: str, train_type: str, num_sets: int, difficulty: int = 3, diy_config: str = "",
                        user_context: dict = None, lang: str = "中文") -> str:
    if diy_config:
        paper_structure = f"【试卷结构】：{diy_config}"
    else:
        paper_structure = "【试卷结构】：自动规划合理的题型及数量，满分100分。"

    # 🚨 针对不同模式，注入极强的“变异”指令
    if train_type == "original":
        type_req = "【原题改数练习】保持原题的物理/数学背景和公式框架，**必须修改核心参数**，绝不能照抄原题数据。"
    elif train_type == "variant":
        type_req = "【原题变式练习】🚨 严禁只改数字！你必须改变题目的已知条件组合、设问角度、或者物理模型（比如把平面受力改为斜面受力，把已知力求加速度改为已知加速度求某个力）。"
    elif train_type == "predict":
        type_req = "【预测仿真练习】结合该章节的高频考点，模仿考研或期末压轴题的风格。可以引入相关的实际应用场景（如工程机械、生活现象），题目要有层次感。"
    else:
        type_req = "【全新模拟练习】🚨 严禁换皮！必须引入全新的应用情境或组合模型，考察相同的知识点但完全不同的设问方式，要像真正的大学期末统考一样综合。"

    lang_req = "🚨【STRICT ENGLISH ONLY】: You must output entirely in English. No Chinese characters." if lang == "English" else "🚨【语言要求】：请必须使用纯正的中文输出。"

    sys_prompt = f"""
    【系统角色】大学期末考试命题组长。你有着极其丰富的出题经验，非常厌恶只会换数字的劣质题。
    【任务】生成 {num_sets} 套期末试卷。难度：{difficulty} 星。
    {type_req}
    {paper_structure}
    {lang_req}

    🚨【出题红线：绝对防幻觉与反模板】🚨
    1. **严格贴合资料**：你只能考察资料中出现的知识点！符合大学期末考真实难度，不出弱智题，不出超纲题。
    2. **拒绝千篇一律**：同一套试卷中，不允许出现两道套路完全一样的题。可以尝试从计算题、证明题、概念辨析题中灵活切换。
    3. **严禁乱标页码**：这些题目是你新编的，原资料里根本不存在！所以**绝对不准**写“参考原资料第X页”！
    4. **图形文字化建模（极重要）**：如果新出的题需要配图（如受力分析、滑轮），你**必须用极其详尽的文字把图形描述出来**（例如：“一根长为L的杆，左端通过铰链固定，右端受水平向右的拉力F，此时杆与竖直方向夹角为θ...”）。确保学生不看图，光看文字就能列出方程。
    5. 选项独立换行。公式必须用 `$` 包裹。
    6. 先输出纯题目，结束后写 `# 答案与解析`，再输出答案。在解析中，必须写明“本题考查了XXX的核心概念”和“常见易错点”。
    """
    # 🚨 温度提升到 0.7，激发 AI 的创造力，不再只会套死模板
    return call_ai_with_retry(sys_prompt, raw_text, temp=0.7)
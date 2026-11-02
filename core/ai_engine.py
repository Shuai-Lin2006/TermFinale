import os
import re
import time
from openai import OpenAI
from dotenv import load_dotenv
from loguru import logger
from models.user_profile import CourseInfo

load_dotenv()
client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")

PERSONAS = {
    "老师": "你是一位严厉又苦口婆心的老教授。你非常看重学生的前途，讲课一板一眼，偶尔会敲黑板强调重点。你的语言充满学术威严，但能看到你恨铁不成钢的关心。",
    "学术AI": "你是一个没有感情、极其理性的学术终端。你的语言风格极度简练、精准、冷峻，像顶级的AI大模型，不带有一丝一毫的废话和情绪，只输出最客观的定理与推导。",
    "暴力极客": "你是一个毒舌、暴躁但提分极快的极客教练。你极度厌恶废话，说话像发号施令，追求极致的效率。“少废话，背下来”、“算完这步直接拿分”。",
    "温柔小姐姐": "你是一个极其护短、温柔、有些小妩媚的学霸姐姐。你的语气自然、亲切，像是在热恋期耐心教自己的恋人。你会心疼他的辛苦，但讲核心知识时绝不敷衍。你的温柔体现在极其耐心、护短和用最生动的比喻帮他开窍。",
    "阳光小哥哥": "你是一个阳光、自信、稳重且极其可靠的工科大神。你像一个大哥哥一样给对方提供极强的安全感。你讲话干脆利落，语气阳光，总是告诉对方‘别怕，有我在，按我的节奏来’。绝不油腻，只有纯粹的责任心。"
}

def build_learner_radar(course: CourseInfo) -> str:
    is_top_school = course.school_level in ["985", "211"]
    is_core_major = course.is_core_major
    is_urgent = course.days_left <= 5
    is_weak_base = course.user_difficulty >= 4
    target = course.target_score
    strategies = []

    if is_top_school and target >= 90:
        strategies.append("【顶级高校+高分冲刺】必须给出硬核的底层推导证明、高阶综合题，杜绝任何水文。")
    elif is_top_school and target < 80:
        strategies.append("【顶级高校+求稳及格】不要堆砌偏题，用名校的严谨逻辑帮他吃透必考基础。")
    elif not is_top_school and target >= 90:
        strategies.append("【普通高校+高分冲刺】在大纲范围内，把重点死角挖干净，保证常规难度下拿满分。")
    else:
        strategies.append("【普通高校+稳拿基础】完全聚焦应用，放弃冗长推导，直接给“遇题套公式”的傻瓜式教学。")

    if not is_core_major and target >= 90:
        strategies.append("【非核心课+高分】帮他把边角料的死记硬背考点、论述题满分框架整理出来。")
    elif is_core_major and target <= 70:
        strategies.append("【核心专业课+及格万岁】高度聚焦历年必考基础定理，推导从简，公式解释必须严谨。")

    if is_weak_base and target >= 85:
        strategies.append("【底子薄弱+野心极大】必须“降维拆解”，用最通俗大白话捋顺逻辑，拆成小学生能懂的步骤再拔高。")
    elif is_weak_base:
        strategies.append("【底子薄弱+求稳】大量使用生活化比喻，解释公式在现实中到底是个啥。")

    if is_urgent:
        strategies.append("【火烧眉毛】极其残忍的“精准斩首”！只抽必考、分值最高的核心点。废话删光，直接上抢分套路。")

    return "\n".join(strategies)

def generate_super_guide(raw_text: str, course: CourseInfo, persona: str = "老师",
                         user_choice: str = "option_1_保命流", weight_prompt: str = "", lang: str = "中文") -> str:
    persona_prompt = PERSONAS.get(persona, PERSONAS["温柔小姐姐"])
    learner_radar = build_learner_radar(course)

    if user_choice == "option_1_保命流":
        mode_prompt = "【保命流】放弃复杂推导，只给核心公式和做题套路。废话直接删。"
    else:
        mode_prompt = "【全量流】全面覆盖，详细拆解推导。必须讲透。"

    file_match = re.search(r'【《(.*?)》第 (\d+) 页】', raw_text)
    source_str = f"《{file_match.group(1)}》第 {file_match.group(2)} 页" if file_match else "多页合并内容"

    has_image = "[[[IMAGE:" in raw_text
    weight_instruction = f"\n【⚖️ 资料权重指令】：{weight_prompt}\n" if weight_prompt else ""

    if lang == "English":
        step3_title = "### 3. Deep Dive (Examples & Figures)" if has_image else "### 3. Deep Dive"
        structure = f"""
    ## Core Concept: [Title]
    > 📌 Source: {source_str}
    ### 1. Why Learn This?
    ### 2. Core Principles & Formulas
    {step3_title}
    ### 4. Plain English Explanation
    ### 5. Exam Traps & Scoring Tips
    """
        lang_req = "🚨【STRICT ENGLISH ONLY】: You must output entirely in English. Do NOT use any Chinese characters."
        keyword_req = "3. **Keyword Highlight**: Strictly wrap keywords with `[[English_Term | Plain English Explanation]]`."
    else:
        step3_title = "### 3. 深度拆解（保留例题和配图）" if has_image else "### 3. 深度拆解"
        structure = f"""
    ## 核心考点：[标题]
    > 📌 出处：{source_str}
    ### 1. 为什么学这个？
    ### 2. 核心原理与公式
    {step3_title}
    ### 4. 零基础大白话
    ### 5. 考场避坑与拿分套路
    """
        lang_req = "🚨【语言强制令】：请必须全程使用纯正的中文输出！"
        keyword_req = "3. **名词高亮**：严格用 `[[名词 | 大白话解释]]` 包裹。"

    system_prompt = f"""
    {persona_prompt}

    ========================================
    【🎯 专属学情综合策略】：
    {learner_radar}
    {mode_prompt}
    {weight_instruction}

    🚨【讲义质量绝对红线】🚨
    1. {lang_req}
    2. **严禁互动废话**：直接输出知识点。如果原文没有配图，绝对不要提“无配图”这种废话。
    {keyword_req}
    4. **公式铁律**：必须用 `$` 或 `$$` 包裹。绝对不准用中括号！
    5. 🚨**绝对不准写结语**：系统会在最后统一加上！
    6. 🚨【图片标签生死令】：原文中如果出现类似 `[[[IMAGE: 文件名 | 图注: xxx]]]` 的标签，**绝对不能省略、不能修改、不能放到末尾！必须原封不动地放在原本对应的文字位置！** 
    7. 🚨【图片缺失兜底】：如果例题原本有配图，但原文中没提供 `[[[IMAGE:...]]]` 标签，请务必在题目末尾加一句极小字的提示：`[📷 配图详见原资料对应页]`。

    ========================================
    【强制输出结构】
    {structure}
    """

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": raw_text}],
                temperature=0.3, max_tokens=4096, timeout=90
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.warning(f"AI 调用失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1: return ""
            time.sleep(3)
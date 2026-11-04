import re
import time
from openai import OpenAI
from core.config import get_key, load_env, max_tokens, model_extra, text_model
from loguru import logger
from models.user_profile import CourseInfo

load_env()
client = OpenAI(api_key=get_key("DEEPSEEK_API_KEY", "sk-not-configured"), base_url="https://api.deepseek.com")

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
                         user_choice: str = "option_1_保命流", weight_prompt: str = "", lang: str = "中文",
                         chapter: dict | None = None, user_note: str = "") -> str:
    """生成一章讲义。

    chapter: {title, index, total, must_know, neighbors, target_words}
    """
    persona_prompt = PERSONAS.get(persona, PERSONAS["温柔小姐姐"])
    learner_radar = build_learner_radar(course)
    is_key = user_choice == "option_1_保命流"

    if is_key:
        mode_prompt = (
            "【保命流·结构压缩】只输出三样：①必背要点(3~5条) ②公式卡(公式/符号含义/适用条件) "
            "③三步解题套路。禁止推导过程、历史背景、无关比喻。"
            "注意：压缩的是**排版与展开度**，不是知识点——必考概念一个都不能漏。"
        )
    else:
        mode_prompt = "【全量流】完整覆盖：概念→原理→推导→例题→陷阱。可以长，但每句话都要有信息量。"

    file_match = re.search(r'【《(.*?)》第 (\d+) 页】', raw_text)
    source_str = f"《{file_match.group(1)}》第 {file_match.group(2)} 页" if file_match else "多页合并内容"

    weight_instruction = f"\n【⚖️ 资料权重指令】：{weight_prompt}\n" if weight_prompt else ""

    chapter_title = ""
    chapter_block = ""
    idx = 1
    if chapter:
        idx = int(chapter.get("index", 0)) + 1
        total = int(chapter.get("total", 1))
        chapter_title = str(chapter.get("title", "")).strip()
        must = "、".join(chapter.get("must_know") or []) or "（沿用资料主线）"
        neighbors = chapter.get("neighbors", "") or "无"
        target_words = chapter.get("target_words") or (1200 if is_key else 2600)
        chapter_block = f"""
    ========================================
    【本章定位】第 {idx}/{total} 章：{chapter_title or '未命名'}
    【必须覆盖，一个都不能少】{must}
    【相邻章节（只用于避免重复，不要展开）】{neighbors}
    【篇幅要求】约 {target_words} 字（中文字符计），明显不足或大幅超出都算不合格。
    【紧迫度】{chapter.get('urgency', '未评估')}
    【边界铁律】只讲本章范围；不得复述其他章节内容；不得自行新增无关知识点。
    """
    must_cover = chapter.get("must_cover") or []
    if must_cover:
        chapter_block += ("\n【必须引用页码】本章资料页码：" + "、".join(f"P.{n}" for n in must_cover) +
                          "。每个知识点末尾必须标注来源页（如（P.12）），且只能使用这些页码；"
                          "若某页没有可用内容，也要在该页对应处写一句『该页仅含图示/无新增考点』。")

    if lang == "English":
        heading = chapter_title or "[Title]"
        structure = f"""
    ## Core Concept: {heading}
    > 📌 Source: {source_str}

    (Open with 2–3 sentences that set up the problem naturally. Do not use generic headings like "Why Learn This".)

    ### {idx}.1 Definitions
    ### {idx}.2 Principles & Formulas
    ### {idx}.3 Worked Examples
    ### {idx}.4 Pitfalls & Exam Usage
    """
        lang_req = "🚨【STRICT ENGLISH ONLY】: You must output entirely in English. Do NOT use any Chinese characters."
        keyword_req = "3. **Keyword Highlight**: Strictly wrap keywords with `[[English_Term | Plain English Explanation]]`."
    else:
        heading = chapter_title or "[标题]"
        structure = f"""
    ## 核心考点：{heading}
    > 📌 出处：{source_str}

    （先用 2~3 句话自然引入：这一节要解决什么问题、它和前后知识的联系。
    不要写“为什么学这个”“核心原理”这类空标题，直接进入正文。）

    ### {idx}.1 概念与定义
    ### {idx}.2 原理与公式
    ### {idx}.3 例题与拆解
    ### {idx}.4 易错与考场用法
    """
        lang_req = "🚨【语言强制令】：请必须全程使用纯正的中文输出！"
        keyword_req = "3. **名词高亮**：严格用 `[[名词 | 大白话解释]]` 包裹。"

    system_prompt = f"""
    {persona_prompt}

    🚨【人设铁律】你就是「{persona}」本人：语气、称呼、举例方式要体现这个人设，让阅读不枯燥。
    但人设**只影响表达方式**——绝不能改变知识点、公式、结论，也不能为了语气添加资料里没有的内容。

    ========================================
    【🎯 专属学情综合策略】：
    {learner_radar}
    {("【用户补充要求】" + user_note.strip() + "（与资料冲突时以资料为准，不要因此编造）") if user_note.strip() else ""}
    {mode_prompt}
    {weight_instruction}
    {chapter_block}

    🚨【资料边界铁律】🚨
    1. 只能使用用户提供的资料；资料没讲的不要编造，不确定就写"资料未提及"。
    2. 允许补充通用背景/记忆技巧，但必须单独标注 `【延伸】`，且不得与资料冲突。
    3. 出处页码只能来自资料里标注的页码；没有就写"资料未标注页码"，绝不编造。
    4. 资料里的知识点不要遗漏：本批资料出现的概念、公式、结论都要覆盖到。

    🚨【教材体格式（最高优先级）】🚨
    1. 像正式教材一样连续行文，段落之间用过渡句衔接；禁止把内容拆成一堆短项目符号。
    2. 小节标题必须是**具体知识点名称**（如「3.1 柱面坐标变换」），禁止「核心原理」「深度拆解」这种空话标题。
    3. 定义、定理用 `> **定义**：…` 引用块；易错点用 `> **易错**：…`；例题用 `**例 3-1**` 开头，紧跟题目与解答。
    4. 每个小节先给结论/定义，再解释为什么，再配一个例子；不要反过来堆铺垫。
    5. 图片标签必须放在它真正对应的段落之后，不得集中到章末。
    6. **公式必须独立成行**：用 `$$...$$` 单独占一段；只有单个符号（如 $T$、$n$、$p$）才用行内 `$...$`。
       禁止把三个以上公式塞进一句话里，禁止一行里出现连续多个等号推导。
    7. **例题固定结构**：
       **例 2-4**
       题：……
       解：
       $$……$$
       所以 ……
    8. 每个自然段不超过 4 行；多步计算一步一行，步骤之间空一行。

    🚨【讲义质量绝对红线】🚨
    1. {lang_req}
    2. **严禁互动废话**：直接输出知识点。如果原文没有配图，绝对不要提“无配图”这种废话。
    {keyword_req}
    4. **公式铁律**：必须用 `$` 或 `$$` 包裹。绝对不准用中括号！
    5. 🚨**绝对不准写结语**：系统会在最后统一加上！
    6. 🚨【图片标签生死令】：
       - 原文中如果出现 `[[[IMAGE: 文件名 | 图注: xxx]]]`，**绝对不能省略、不能改文件名、不能改图注**。
       - 必须紧跟在**描述这张图的那句话**之后；如果原文这段没有明确提到图，就放在该段讲完后的第一个空行处。
       - 禁止把同一个标签挪到别的章节；禁止把三张以上图片连续堆在一起；禁止集中放到章末。
    7. 🚨【图片缺失兜底】：如果例题原本有配图，但原文中没提供 `[[[IMAGE:...]]]` 标签，请务必在题目末尾加一句极小字的提示：`[📷 配图详见原资料对应页]`。

    ========================================
    【强制输出结构】
    {structure}
    """

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=text_model(),
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": raw_text}],
                temperature=0.3, max_tokens=max_tokens(), timeout=120, **model_extra()
            )
            choice = response.choices[0]
            if getattr(choice, "finish_reason", None) == "length":
                usage = getattr(response, "usage", None)
                logger.warning(
                    "输出被截断 finish_reason=length tokens={} 章节={}",
                    getattr(usage, "completion_tokens", "?"), chapter_title or "-",
                )
            return choice.message.content
        except Exception as e:
            logger.warning(f"AI 调用失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1: return ""
            time.sleep(3)
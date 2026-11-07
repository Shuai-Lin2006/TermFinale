import time
from openai import OpenAI
from core.config import get_key, load_env, max_tokens, model_extra, text_model
from loguru import logger

load_env()
client = OpenAI(api_key=get_key("DEEPSEEK_API_KEY", "sk-not-configured"), base_url="https://api.deepseek.com")


def call_ai_with_retry(sys_prompt, user_content, temp=0.1, min_budget=0, max_chars: int | None = None):
    """调用文本模型：网络异常重试 3 次；空输出（思考耗尽）自动加倍预算再试。

    不再无条件截断到 10k：整本 1001 页曾被悄悄砍成前 1.2%。需要截断的调用方
    必须显式传 max_chars，并在提示词里说明“这是节选”。
    """
    max_retries = 2
    if max_chars and len(user_content or "") > max_chars:
        user_content = user_content[:max_chars]
    for attempt in range(max_retries):
        budget = max(max_tokens(), min_budget)
        for _ in range(2):
            try:
                response = client.chat.completions.create(
                    model=text_model(),
                    messages=[{"role": "system", "content": sys_prompt},
                              {"role": "user", "content": user_content}],
                    temperature=temp, max_tokens=budget, timeout=75, **model_extra(),
                )
                choice = response.choices[0]
                content = choice.message.content or ""
                if content.strip():
                    if getattr(choice, "finish_reason", None) == "length":
                        logger.warning("输出被截断（budget={}），改用精简提示重试", budget)
                        user_content = user_content[:3000]
                        continue
                    return content
                if getattr(choice, "finish_reason", None) == "length":
                    logger.warning("输出为空（budget={}），压缩输入重试", budget)
                    user_content = user_content[:3000]
                    continue
                return ""
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"API 请求失败 (尝试 {attempt + 1}/{max_retries}): {exc}")
                if attempt == max_retries - 1:
                    return ""
                time.sleep(1)
                break
    return ""




def sample_context(text: str, max_chars: int = 14000, windows: int = 10) -> tuple[str, bool]:
    """全书均匀节选；返回 (文本, 是否被节选)。

    用于 analysis/exam 这类需要“看全书”的任务：直接塞整本会被模型丢页，
    只截前 10k 又只看到开头。均匀取 10 个窗口，至少覆盖全书头/中/尾。
    """
    text = text or ""
    if len(text) <= max_chars:
        return text, False
    windows = max(2, windows)
    win = max(600, max_chars // windows)
    n = len(text)
    step = max(1, (n - win) // (windows - 1))
    parts: list[str] = []
    for i in range(windows):
        start = min(n - win, i * step)
        head = text.rfind("【《", max(0, start - 300), start + 1)
        if head != -1:
            start = head
        parts.append(text[start:start + win].strip())
    body = "\n\n【…全书均匀节选…】\n\n".join(parts)
    note = (f"\n\n【资料范围】原文 {n} 字，本次只提供全书均匀节选（{len(body)} 字）。"
            "请基于节选做概览；不要假装读过未提供的页。")
    return body + note, True


def _note_block(user_note: str) -> str:
    note = (user_note or "").strip()
    if not note:
        return ""
    return (f"【用户补充要求】{note}\n"
            "（在不违背资料事实的前提下尽量满足；与资料冲突时以资料为准，不得因此编造。）\n\n")

def generate_logic_analysis(raw_text: str, mode: str, user_note: str = "",
                            constraint_block: str = "", retry_note: str = "") -> str:
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
    extra = "\n".join(x for x in (_note_block(user_note).strip(),
                                  (constraint_block or "").strip(),
                                  (retry_note or "").strip()) if x)
    if extra:
        sys_prompt = extra + "\n\n" + sys_prompt
    raw_text, _ = sample_context(raw_text, 16000)
    return call_ai_with_retry(sys_prompt, raw_text, temp=0.2)


def generate_logic_bundle(raw_text: str, lang: str = "中文", user_note: str = "",
                          constraint_block: str = "", retry_note: str = "") -> str:
    """一次生成「宏观架构 + 知识图谱 + 因果链 + 对照表」的复合逻辑分析。

    旧实现把「思维导图」和「文本逻辑」拆成两次生成：费钱、且图文常常对不上。
    """
    if lang == "English":
        sys_prompt = """
        【Role】Expert in academic reasoning and knowledge architecture.
        【Task】Produce a single "Logic Analysis" document with EXACTLY these four sections:

## 🧠 Macro Structure
(120-200 words: where the chapter starts, what it goes through, what it ends with.)

## 🗺️ Knowledge Map
```mermaid
graph TD
  A["Core Idea"] --> B["Sub concept (p.8)"]
```
(15-30 nodes, at least 3 levels, node text <= 12 words, wrap in double quotes, leaf nodes carry page numbers.)

## 🔗 Causal Chains
### Chain 1: <name>
- **Premise**: ...
- **Derivation**: ... (formulas wrapped in $)
- **Conclusion**: ...
- **Exam use**: ...

(4-8 chains covering the main line.)

## 📊 Concept / Formula / Question-Type Table
| Concept | Key formula | Typical question | Importance |
|---|---|---|---|
| ... | $...$ | Calculation | ★★★ |

【Hard rules】Only use the provided material. No fabrication. Keep page refs when possible.
        """
    else:
        sys_prompt = """
        【系统角色】顶尖学术推演专家 + 知识架构师。
        【任务】基于资料，输出一份「逻辑分析」复合文档，必须严格按以下四段结构，不得增删、不得调换顺序：

## 🧠 宏观架构
（150~250 字，说清本章从哪出发、经过什么、归结到什么，形成一条主线。）

## 🗺️ 知识图谱
```mermaid
graph TD
  A["核心概念"] --> B["子概念(第8页)"]
  A --> C["另一分支(第9页)"]
```
（15~30 个节点，至少 3 层；节点文字≤12 字；含中文或标点的节点必须用双引号包裹；叶子节点末尾标页码，如 B["角速度(第8页)"]。）

## 🔗 因果链
### 链 1：<链名>
- **前提**：...
- **推导**：...（公式用 $ 包裹）
- **结论**：...
- **对应题型**：选择题 / 计算题 / 证明题

（4~8 条链，覆盖全章主线，链与链之间要是递进关系，不要并列罗列。）

## 📊 概念-公式-题型对照
| 概念 | 核心公式 | 常见题型 | 重要度 |
|---|---|---|---|
| 转动惯量 | $J=\\sum m_i r_i^2$ | 计算题 | ★★★ |

【红线】
1. 只依据资料，严禁编造资料中没有的结论；
2. 页码尽量真实，找不到就写"见原资料"；
3. 图谱与文字必须互补：图给结构，文字给因果；
4. 不准写"以下是""希望对你有帮助"等废话；
5. 直接输出正文，不要任何开场白。
        """
    extra = "\n".join(x for x in (_note_block(user_note).strip(),
                                  (constraint_block or "").strip(),
                                  (retry_note or "").strip()) if x)
    if extra:
        sys_prompt = extra + "\n\n" + sys_prompt
    raw_text, _ = sample_context(raw_text, 16000)
    return call_ai_with_retry(sys_prompt, raw_text, temp=0.3)


def generate_extraction(raw_text: str, extract_type: str, with_answer: bool = True, user_note: str = "",
                        constraint_block: str = "") -> str:
    if extract_type == "nouns":
        sys_prompt = (
            "【任务】提取核心名词，每个都要能直接背。格式：\n"
            "- **名词**：一句话定义（大白话） | 考场怎么写 | [出处：《文件名》第X页]\n"
            "只写资料里出现的名词，不要编造；资料没写的不要补。"
        )
    elif extract_type == "points":
        sys_prompt = """【任务】从资料中提取 3~6 个真正会考的考点，宁缺毋滥。每个考点必须讲透，不能只给一句话。
判断标准：资料里明确讲过 + 期末可能考 + 能直接用来答题。
严格用以下格式，每一栏都不能省：
### 考点：<具体名称>
- **是什么**：2~3 句，说清定义与适用条件，用大白话
- **为什么重要**：它在整章里的作用、考试为什么爱考
- **怎么考**：选择题/计算题/简答题中的哪种，给出一个具体问法
- **怎么答**：分步骤写（1)(2)(3)），公式用 $ 包裹，能直接背下来用
- **易错点**：最常见的错法 + 怎么避免
- **延伸**（可选）：资料没写但常一起考的相关点，必须标注“【延伸】”
- [出处：《文件名》第X页]
红线：
1. 只讲资料里有的内容；资料没写的不要编，确需补充时放进【延伸】并注明。
2. 页码必须来自资料；找不到就写“资料未标注页码”。
3. 这段资料如果没有可考内容，直接输出“无”，不要硬凑。"""
    else:
        if with_answer:
            ans_req = "必须在每道题下方附带【答案】和【解析】。"
        else:
            ans_req = "仅输出题目，不要给答案。"
        sys_prompt = f"""【系统角色】资深资料提取专家。
【任务】把资料里出现的**全部原题**完整提取出来，一道都不能漏。

🚨【题号规则】
1. 沿用资料中的原始编号（如【例1.1】、4.、3-2），**不要重新编号**、不要把不同大题的题号连成一串。
2. 资料本身没有编号时，才按出现顺序编号。

🚨【跨页规则】
资料里页与页之间可能有页眉/页码，同一道题可能被拆在两页。
块首若出现"【接上页…】"，说明这道题上一段已在前面出现过：**必须合并成一道完整题目输出，不要重复输出两道**。

🚨【完整性规则】
3. 每题必须保留：题干、全部选项、全部小问、已知条件与单位；不得改写题干、不得增删条件。
4. 资料没有的题绝对不准编造；某段确实没有题目时，只输出"【本段无题目】"。
5. 依赖配图的题：保留 `[[[IMAGE: 文件名 | 图注: xxx]]]` 标记；没有标记就写 `[见图]`。
6. 公式用 `$` 包裹，选项各自换行。

{ans_req}"""
    extra = "\n".join(x for x in (_note_block(user_note).strip(),
                                  (constraint_block or "").strip()) if x)
    if extra:
        sys_prompt = extra + "\n\n" + sys_prompt
    return call_ai_with_retry(sys_prompt, raw_text, temp=0.2)




def _qwen_fallback(system: str, user: str, max_tokens: int = 3000) -> str:
    """DeepSeek 返回空时的备用文本模型（DashScope 兼容接口）。"""
    try:
        import os
        from openai import OpenAI
        from core.config import get_key
        client = OpenAI(api_key=get_key("DASHSCOPE_API_KEY", "sk-not-configured"),
                        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")
        resp = client.chat.completions.create(
            model=os.getenv("TERMFINALE_EXAM_FALLBACK_MODEL", "qwen-plus"),
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.5, max_tokens=max_tokens, timeout=120)
        return resp.choices[0].message.content or ""
    except Exception as exc:  # noqa: BLE001
        logger.warning("备用模型失败: {}", exc)
        return ""


def _clean_section_output(md: str, title: str, count: int, points: float) -> str:
    """单题型生成结果清洗：模型常违反指令，顺手把答案和别的题型也吐出来。

    只保留请求的题型、去掉答案分区；没有可识别内容时返回空串，让上层失败/重试，
    绝不把“题+答案+另一套题”的混合物交给验卷器。
    """
    import re as _re
    text = (md or "").strip()
    if not text:
        return ""
    text = _re.split(r"(?m)^#{1,3}\s*(?:答案|参考答案|答案与解析|答案及解析)", text)[0].strip()
    if not text:
        return ""
    lines = text.splitlines()
    start = None
    for idx, line in enumerate(lines):
        if _re.match(r"^##\s*", line) and title in line:
            start = idx
            break
    if start is None:
        # 没有目标标题：只有在没有其他 ## 题型时才敢兜底
        if any(_re.match(r"^##\s*", ln) for ln in lines):
            return ""
        body = "\n".join(lines).strip()
        if not body or not _re.search(r"(?m)^\s*\d{1,2}\s*[.、．)）]", body):
            return ""
        return f"## {title}（{count} 题，每题 {points:g} 分，共 {count * points:g} 分）\n\n{body}"
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if _re.match(r"^##\s*", lines[j]):
            end = j
            break
    body = "\n".join(lines[start + 1:end]).strip()
    if not body or not _re.search(r"(?m)^\s*\d{1,2}\s*[.、．)）]", body):
        return ""
    return f"## {title}（{count} 题，每题 {points:g} 分，共 {count * points:g} 分）\n\n{body}"


def _clean_answer_output(md: str) -> str:
    """答案清洗：只保留第一段答案，去掉重复答案分区/混进来的第二套题。"""
    import re as _re
    text = (md or "").strip()
    if not text:
        return ""
    # 多个答案分区：只保留第一个
    parts = _re.split(r"(?m)^(?=#{1,3}\s*(?:答案|参考答案|答案与解析|答案及解析))", text)
    if len(parts) > 1:
        text = parts[1]
    else:
        text = "# 答案与解析\n" + text
    # 混进来的“## 单项选择题（4 题，每题 5 分…）”说明模型又开了一套题
    paper_heading = _re.search(
        r"(?m)^##\s*\S+?（\s*\d+\s*题[^）]*）", text)
    if paper_heading:
        text = text[:paper_heading.start()].rstrip()
    return text.strip()


def _generate_sections(raw_text: str, lang: str, sections=None, train_type: str = "mock",
                       reference_exam: bool = False, *, blueprint=None, user_note: str = "",
                       constraint_block: str = "", retry_note: str = "",
                       with_answers: bool = True, course_name: str = "") -> str:
    """按用户给定结构逐题型生成，避免整卷超出单次输出上限。"""
    # 生成与校验必须共用同一份结构：有蓝图就按蓝图出题，否则退默认结构
    if not sections and blueprint is not None:
        sections = [(s.name, s.count, s.each) for s in blueprint.sections]
    if not sections:
        sections = [("单项选择题", 8, 3), ("填空题", 4, 4), ("计算题", 3, 12), ("综合题", 2, 12)]
    # 兼容 dict 结构
    parsed = []
    for item in sections:
        if isinstance(item, dict):
            name = str(item.get("name") or item.get("type") or "题目")
            count = max(1, int(item.get("count") or 1))
            points = max(1, int(item.get("points") or 1))
        else:
            name, count, points = item
        parsed.append((name, count, points))
    total_points = sum(count * points for _, count, points in parsed)

    lang_req = "STRICT ENGLISH ONLY." if lang == "English" else "中文作答。"
    style = {
        "单项选择题": "每题 4 个选项 A/B/C/D，只有一个正确",
        "多项选择题": "每题 4~5 个选项，至少两个正确，明确标注多选",
        "判断题": "每题一句话，判断对错并说明理由",
        "填空题": "每题 1~2 个空，答案简短",
        "名词解释": "给出术语，要求解释其定义与要点",
        "简答题": "问题要能分点作答，答案 3~5 个要点",
        "计算题": "必须给出完整已知、求、解过程",
        "推断题": "给出情境或数据，要求推理结论并说明依据",
        "综合题": "综合 2~3 个知识点，有完整情境与设问层次",
        "证明题": "给出条件与结论，要求写出完整证明过程",
        "翻译题": "给出英文/中文段落，要求准确翻译并保留术语",
        "写作题": "给出题目与要求，字数、体裁明确",
        "阅读理解": "给出短文与若干选择题，考查理解与推理",
        "完形填空": "给出短文与选项，考查语境与词汇",
        "编程题": "给出问题描述与输入输出要求，要求写出代码或算法步骤",
        "案例分析题": "给出真实案例，要求分析问题、依据与对策",
        "论述题": "给出观点型问题，要求分点论述并举例",
    }

    deep = ("题目必须有真实背景或应用情境，设问有层次、有深度，禁止一句话送分题；"
            "不要出现与资料无关的内容。") if train_type in ("mock", "predict") else (
            "参考资料中的原题，保留题型与考法；原题改数只改参数，原题变式要改条件组合或设问角度。")

    ref_hint = ("如果资料中包含历年真题，请优先模仿其题型分布、问法与难度。" if reference_exam else "")
    extra_rules = "\n".join(x for x in (_note_block(user_note).strip(),
                                        (constraint_block or "").strip(),
                                        (retry_note or "").strip()) if x)
    parts = []
    for i, (title, count, points) in enumerate(parsed):
        extra = style.get(title, "按该题型的常规考法命题")
        sys_p = f"""你是大学期末命题老师。{lang_req}
本次只出「{title}」这一种题型：{count} 题，每题 {points:g} 分，共 {count * points:g} 分。
题型要求：{extra}
命题要求：
- 严格基于给定资料，不超纲、不编造；
- {deep}
- {ref_hint}
- 每题末尾标注【考点：xxx】；
- 只输出这一种题型，用二级标题 `## {title}（{count} 题，每题 {points:g} 分，共 {count * points:g} 分）`，题号从 1 开始；
- 不要输出答案或解析。
{extra_rules}"""
        # 轮换资料片段，避免所有题型都只看第一页
        # 按题型在全书中均匀取样，而不是所有题型都挤在开头
        total = len(raw_text)
        chunk_len = min(2400, max(900, total // max(1, len(parsed))))
        start = int(i * max(0, total - chunk_len) / max(1, len(parsed) - 1)) if len(parsed) > 1 else 0
        chunk = raw_text[start:start + chunk_len]
        md = call_ai_with_retry(sys_p, chunk, temp=0.7, min_budget=2048)
        if not md.strip():
            md = call_ai_with_retry(sys_p, chunk[:800], temp=0.6, min_budget=2048)
        if not md.strip():
            logger.warning("主模型空返回，切换备用模型：{}", title)
            md = _qwen_fallback(sys_p, chunk, max_tokens=2500)
        cleaned = _clean_section_output(md, title, count, points)
        if cleaned:
            parts.append(cleaned)
        elif md.strip():
            logger.warning("单题型输出无法清洗，已丢弃：{}", title)
    if not parts:
        return ""
    head = (f"# {course_name} 期末试卷\n" if course_name else "# 期末试卷\n") + \
           f"**满分：{total_points:g} 分**\n\n"
    questions = head + "\n\n".join(parts)
    if not with_answers:
        return questions.rstrip()
    answer_sys = f"""你是答案撰写人。{lang_req}
按题号输出 `# 答案与解析`：
- 选择题给字母；判断题给对/错；填空题给答案；名词解释/简答给要点；
- 计算/推断/综合给关键步骤与最终结果；
- 每题解析不超过 2 句，只写考点 + 一个易错点。
不要重复题目。"""
    answers = call_ai_with_retry(answer_sys, questions[:8000], temp=0.2, min_budget=4096)
    if not answers.strip():
        answers = _qwen_fallback(answer_sys, questions[:8000], max_tokens=3000)
    answers = _clean_answer_output(answers)
    return questions.rstrip() + "\n\n" + answers.strip() if answers.strip() else questions


def generate_exam_paper(raw_text: str, train_type: str, num_sets: int, difficulty: int = 3, diy_config: str = "", user_note: str = "",
                        user_context: dict = None, lang: str = "中文", blueprint=None,
                        sections=None, reference_exam: bool = False, *,
                        constraint_block: str = "", retry_note: str = "",
                        with_answers: bool = True, course_name: str = "") -> str:
    if sections or blueprint is not None:
        return _generate_sections(raw_text, lang, sections=sections,
                                  train_type=train_type, reference_exam=reference_exam,
                                  blueprint=blueprint, user_note=user_note,
                                  constraint_block=constraint_block, retry_note=retry_note,
                                  with_answers=with_answers, course_name=course_name)

    if diy_config:
        paper_structure = f"【试卷结构（必须严格遵守）】：{diy_config}"
    else:
        paper_structure = ("【试卷结构（必须严格遵守）】：\n"
                           "一、选择题 8 题 × 3 分 = 24 分\n"
                           "二、填空题 4 题 × 4 分 = 16 分\n"
                           "三、计算题 4 题 × 12 分 = 48 分\n"
                           "四、综合题 1 题 × 12 分 = 12 分\n"
                           "合计必须为 100 分，四个大题一个都不能少。")

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

    sys_prompt = _note_block(user_note) + f"""
    【系统角色】大学期末考试命题组长。你有着极其丰富的出题经验，非常厌恶只会换数字的劣质题。
    【任务】生成 {num_sets} 套期末试卷。难度：{difficulty} 星。
    {type_req}
    {paper_structure}
    {lang_req}
    {constraint_block}
    {retry_note}

    🚨【出题红线：绝对防幻觉与反模板】🚨
    1. **严格贴合资料**：你只能考察资料中出现的知识点！符合大学期末考真实难度，不出弱智题，不出超纲题。
    2. **拒绝千篇一律**：同一套试卷中，不允许出现两道套路完全一样的题。可以尝试从计算题、证明题、概念辨析题中灵活切换。
    3. **严禁乱标页码**：这些题目是你新编的，原资料里根本不存在！所以**绝对不准**写“参考原资料第X页”！
    4. **图形文字化建模（极重要）**：如果新出的题需要配图（如受力分析、滑轮），你**必须用极其详尽的文字把图形描述出来**（例如：“一根长为L的杆，左端通过铰链固定，右端受水平向右的拉力F，此时杆与竖直方向夹角为θ...”）。确保学生不看图，光看文字就能列出方程。
    5. 选项独立换行。公式必须用 `$` 包裹。
    6. 只输出题目，不要输出答案、不要输出解析、不要写 `# 答案与解析`。
    7. 🚨 每题末尾必须标注考点：`【考点：具体知识点】`，不得省略。
    8. 🚨 资料里的 `[[[IMAGE: 文件名 | 图注: xxx]]]` 标记若与该题相关，必须原样保留在题干中。
    9. 🚨 各大题分值合计必须等于卷面满分（默认 100 分），题数与分值必须严格按上方结构执行。
    9.1 🚨 解析从简：每题解析不超过 2 句话，禁止长篇展开，否则会超长被截断。
    10. 🚨 输出格式：第一行必须是 `# <课程名> 期末试卷`，第二行必须是 `**满分：100 分**`；
        每个大题必须用二级标题，例如 `## 一、选择题（共 8 题，每题 3 分，共 24 分）`；
        小题用 `1.` 编号，选项 A/B/C/D 各占一行。
    11. 🚨 必须写全四个大题（选择/填空/计算/综合），任何一类都不能省略；只写题目，答案由后续步骤单独生成。
    """
    # 第一步：只出题（避免“题目+解析”超出单次输出上限）
    raw_text, _ = sample_context(raw_text, 14000)
    questions = call_ai_with_retry(sys_prompt, raw_text, temp=0.7, min_budget=8192)
    if not questions.strip():
        logger.warning("主模型多次返回空，切换备用模型")
        questions = _qwen_fallback(sys_prompt, (raw_text or "")[:8000], max_tokens=4096)
    if not questions.strip():
        return ""
    if not with_answers:
        return questions.rstrip()
    answer_sys = f"""你是大学期末考试命题组的答案撰写人。
下面是一份已经出好的试卷题目。请严格按题号输出 `# 答案与解析`：
1. 选择题只给答案字母；
2. 填空题给答案；
3. 计算题/综合题给关键步骤与最终结果；
4. 每题解析不超过 2 句话，只写“本题考查了什么 + 一个易错点”，严禁长篇展开。
{lang_req}
不要重复题目原文。"""
    answers = call_ai_with_retry(answer_sys, questions[:12000], temp=0.2, min_budget=8192)
    return questions.rstrip() + "\n\n" + answers.strip() if answers.strip() else questions
import os
import time
from openai import OpenAI
from core.config import get_key, load_env, text_model
from loguru import logger

load_env()
client = OpenAI(api_key=get_key("DEEPSEEK_API_KEY", "sk-not-configured"), base_url="https://api.deepseek.com")


def call_ai_with_retry(sys_prompt, user_content, temp=0.1):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=text_model(),
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


def generate_logic_bundle(raw_text: str, lang: str = "中文") -> str:
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
    return call_ai_with_retry(sys_prompt, raw_text, temp=0.3)


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
        🚨 2. 配图规则：资料里出现 `[[[IMAGE: 文件名 | 图注: xxx]]]` 时，若该题依赖此图，必须把该标记**原样**放在题干末尾，不得删除、改写或移动到文末；只有确实没有可用标记时，才写 `[📷 原题配图详见资料对应页]`。
        🚨 3. 选项换行，公式用 `$` 包裹。
        {ans_req}
        """
    return call_ai_with_retry(sys_prompt, raw_text, temp=0.2)


def generate_exam_paper(raw_text: str, train_type: str, num_sets: int, difficulty: int = 3, diy_config: str = "",
                        user_context: dict = None, lang: str = "中文", blueprint=None) -> str:
    if diy_config:
        paper_structure = f"【试卷结构（必须严格遵守）】：{diy_config}"
    elif blueprint is not None:
        paper_structure = "【试卷结构（必须严格遵守，不得增删题型）】：\n" + blueprint.render()
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
    7. 🚨 每题末尾必须标注考点：`【考点：具体知识点】`，不得省略。
    8. 🚨 资料里的 `[[[IMAGE: 文件名 | 图注: xxx]]]` 标记若与该题相关，必须原样保留在题干中。
    9. 🚨 各大题分值合计必须等于卷面满分（默认 100 分），题数与分值必须严格按上方结构执行。
    """
    # 🚨 温度提升到 0.7，激发 AI 的创造力，不再只会套死模板
    return call_ai_with_retry(sys_prompt, raw_text, temp=0.7)
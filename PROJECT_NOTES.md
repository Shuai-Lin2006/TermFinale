# TermFinale 项目笔记（AI 协作前必读）

> 生成时间：2026-11-02　基于当时工作区代码逐行通读
> **状态：v2 重构已落地**（见 [`docs/CHANGES_v2.md`](docs/CHANGES_v2.md)）。
> 第 1–11 节记录的是**重构前**的代码与问题，保留作为"为什么这么改"的依据；**第 12 节是重构后现状**。
> 行号以 `v2` 分支为准；若对不上，以实际代码为准（本文件是地图，不是法律）。
> 用途：**改动任何代码前先读第 7 节（隐形协议）和第 8 节（已知问题，多数已修）。**

---

## 1. 一句话定位

macOS 桌面端（CustomTkinter）的**期末复习流水线**：导入 PPT/PDF/DOCX → 本地解析（抽文本 + 抽图片 + 视觉模型写图注）→ 按课程参数拼 prompt → 调 DeepSeek 生成 Markdown → 渲染成**单文件 HTML**（KaTeX 公式 / Mermaid 思维导图 / 名词弹窗 / 搜索 / 打印）→ 存到桌面并在 SQLite 记账。

不是聊天框，是“一次点击跑完一条链”的批处理工具。

---

## 2. 运行环境

| 项 | 实际情况 |
|---|---|
| 解释器 | `.venv/bin/python` = **Python 3.14.8** |
| GUI | customtkinter 6.0.0（Light 主题写死） |
| AI | openai 3.37.0，两家供应商：DeepSeek(`deepseek-chat`) + 阿里云百炼(兼容接口，视觉) |
| 解析 | python-pptx 1.0.2 / PyMuPDF 2.0 / python-docx 1.2.0 / Pillow 13.0 |
| 渲染 | Markdown 3.11.2 |
| 数据 | SQLAlchemy 2.1.6 + SQLite（`term_finale_pro.db`，位于项目根） |
| **缺失** | **没有 requirements.txt / pyproject.toml**，环境靠 `.venv` 现状复现 |
| 启动 | `cd TermFinale && .venv/bin/python main.py`（**必须在项目根目录**，下面有解释） |

密钥在 `.env`：`DEEPSEEK_API_KEY`、`DASHSCOPE_API_KEY`、`ZHIPU_API_KEY`（后者仅 `test_api.py` 用）。
⚠️ `.env` **已被 git 跟踪**（`.gitignore` 对它无效），密钥进过提交历史。

---

## 3. 文件职责（含“是否真的在用”）

| 文件 | 行数 | 状态 | 职责 |
|---|---|---|---|
| `main.py` | 1395 | ✅ 主入口 | 单个类 `TermFinaleApp`，**50 个方法**，四个 onboarding 页 + 仪表盘 + 课程表单 + 上传页 + 生成页 + 复习中心 + 笔记 + 归档 + 预览。全部 UI、线程、DB 读写都在这 |
| `models/user_profile.py` | 82 | ✅ | `CourseInfo`：4 个模块的权重算法（硬度 / 所需小时 / 紧迫度 / 诊断），输出 `final_priority_weight`、`status`、`warning_msg` |
| `core/database.py` | 70 | ✅ | 4 张表 + `init_db()` + `get_db_session()`；`BASE_DIR` 是全项目路径的锚点 |
| `core/parser.py` | 134 | ✅ | 三种格式解析 → 统一成 `["【《文件名》第 N 页】\n正文"]` 的 page 列表；图片落盘 `assets_images/` |
| `core/ai_vision.py` | 60 | ✅ | 单图 → 一句话图注（全学科 prompt）；失败返回 `"原题配图"` |
| `core/ai_engine.py` | 130 | ✅ | 5 人设 + `build_learner_radar()` 学情策略 + `generate_super_guide()`（讲义单块生成） |
| `core/exam_engine.py` | 108 | ✅ | `generate_logic_analysis` / `generate_extraction` / `generate_exam_paper`；自带重试 |
| `core/exporter.py` | 332 | ✅ | **最复杂的一个**：Markdown → 单文件 HTML，含占位符保护、章节编号、目录、图片 base64 内联、KaTeX/Mermaid 注入 |
| `core/text_exporter.py` | 333 | ❌ **死代码** | 与 `exporter.py` 约 95% 相同（仅 mermaid 正则更宽松：`graph TD/LR/TB` 且允许无闭合反引号）。**无任何文件 import 它** |
| `ui_main.py` | 374 | ❌ **死代码** | 旧版四页原型（含主题切换、更粗字体），无引用；`user_config.json` 读 `username` 的兼容逻辑就是它留下的 |
| `core/test_html.py` | 31 | ⚠️ 手工脚本 | 渲染自测；`from core.exporter import ...`，**只能在项目根用 `python -m core.test_html` 跑**，直接 `python core/test_html.py` 会 ImportError |
| `test_chem.py` | 20 | ⚠️ 手工脚本 | 单图视觉自测，同上需 `-m` |
| `test_api.py` | 17 | ❌ 无关 | 用 `zhipuai==glm-4v` 测智谱连通性，与当前 DASHSCOPE 方案无关 |

**目录**：`assets_images/`（290 文件 / 13MB，解析产物，文件名即 ID）、`ppt_images/`（236KB，**无代码引用**，疑似历史遗留）、`.idea/`、`__pycache__/`、`app.log`（loguru 输出）。

---

## 4. 数据层（SQLite，已验证实际表结构）

```
courses(id, name, major, school_level, credits, days_left, target_score,
        user_difficulty, is_major, persona)
materials(id, course_id→courses.id, file_path, file_type['core'|'ref'], filename)
generated_files(id, course_id, file_path, created_at 'MMDD_HHMM',
        file_type['guide'|'analysis'|'extract'|'exam'|'note'])
user_config(id, motto)
```

- 关系：`Course.materials` / `Course.generated_files` 均 `cascade="all, delete-orphan"`。
- `file_path` 存的是**绝对路径**（材料＝用户上传原文件位置；生成物＝桌面）。
- 当前实测数据：3 门课、3 条材料（同一份桌面 PDF）、25 条生成记录、1 条 motto。
- 注意：`materials.file_path` 指向**用户的原始文件**（如 `~/Desktop/xxx.pdf`），这直接导致第 8 节的 P0-1。

---

## 5. 四条流水线（调用链）

### 5.1 讲义生成（唯一有“权重/人设/语言”的一条）
```
show_generation_mode_select (选人设+语言, main.py:662)
  → start_generation (:723)  ← 先做每日 20 次限额检查（写 user_config.json）
    → 线程 run_backend_task (:772)
        读 materials → 逐文件 extract_text_from_file (parser)
        拼 weight_prompt（core_ratio>0.5 / <0.5 / ==0.5 三档话术）
        截断：仅当 core+ref 同时存在时，总页数上限 15（core≈15*ratio）
        build_chunks：2 页/块，块首带上一页末 150 字回溯，前缀【核心重点】/【参考资料】
        逐块 generate_super_guide(...) → 检查 AI 是否吞掉 [[[IMAGE:]]] 标签，缺则补回
        清理 AI 私自写的“结语” → 用 --- 拼接 → 末尾追加 OUTROS[lang][persona]
        export_to_html → 桌面 {课程}_{精简|全量}_{MMDD_HHMM}.html
        写 generated_files(file_type='guide') → show_preview_screen
```
课件块数 = 页数/2，**每块一次 API 调用**，串行；进度条与预计剩余时间按已用时长线性外推。

### 5.2 逻辑分析（复习中心）
`show_ai_analysis` → `get_selected_texts()`（勾选的资料**整篇**拼接，不切块）→ 单次 `generate_logic_analysis(text, mindmap|text_logic)` → HTML（`doc_type` 为“思维导图”/“逻辑分析”）。

### 5.3 资料提取
`show_extract` → 整篇文本按 **2000 字硬切** → 每块 `generate_extraction(chunk, nouns|points|questions, with_answer)` → 拼接。

### 5.4 训练试卷
`show_training` → 可选自定义题型结构（10 种题型 × 数量 × 分值，实时算总分，≠100 会二次确认）→ `generate_exam_paper(text, train_type∈{original,variant,mock,predict}, num_sets, difficulty 1-5, diy_config, user_context, lang)`（温度 0.7，是唯一高温调用）。

> 5.2/5.3/5.4 共用 `run_generation_task (:1180)`，只有 `doc_type`、存储 `file_type`、prompt 不同。

---

## 6. 视觉与图片链路（最容易崩的一环）

```
parser 判定尺寸>50px 且长宽比<10 → 存字节到 assets_images/{name}
  → ai_vision.analyze_image_with_ai() → caption（失败回落"原题配图"）
  → 返回标签字符串 "[[[IMAGE: 文件名 | 图注: caption]]]"
  → 拼进 page 文本 → 喂给 AI（prompt 第 6 条“原封不动保留”）
  → exporter 正则抓出 → base64 内联进 HTML（文件名到 assets_images 里找）
```
- 生成端 `parser.py:78/102/123` 命名规则：`slide{页}_{目录文件数+1}.{ext}`、`pdf{页}_{n}.png`、`doc_{n}.{ext}`。
- 渲染端**只认文件名**，所以图片一旦被覆盖/删除，旧讲义就缺图。

---

## 7. ⚠️ 隐形协议（改代码时绝不能破坏）

这些是模块间靠**字符串**耦合的约定，改任何一端都必须同步另一端：

1. **图片占位符** `[[[IMAGE: 文件名 | 图注: xxx]]]`
   生产者 `parser.py:58`，消费者 `exporter.py:19`，AI prompt 约束 `ai_engine.py:110`，补回逻辑 `main.py:845-859`。改格式＝三处一起改。
2. **名词弹窗** `[[名词 | 大白话解释]]`
   `ai_engine.py:93/80` 让 AI 生成，`exporter.py:48` 解析成 `<span class="keyword">`。注意 exporter 在 48 行**之前**（11 行）还有一次把 markdown 的 `[文字 | 说明]` 转成 `[[...]]` 的补救正则。
3. **章节标题**：`## 核心考点：xxx`
   `exporter.py:66` 靠正则把它改写成 `## 第 N 章：xxx` 再生成目录（`exporter.py:69-80`）并打 `id="chapter-N"`。AI 若输出别的标题格式 → **无目录、无分页锚点**。
4. **出处** `> 📌 出处：《文件名》第 N 页` / `[出处：...]`
   `ai_engine.py:62-63` 反向用正则从原文抽文件名页码；`exporter.py:132-135` 转成小字 `.meta-info`。
5. **公式必须 `$...$` / `$$...$$`**：`exporter.py:82-88` 先把公式整体挖出来占位，防止 markdown 把 `_` `*` 吃掉。
6. **结语由程序统一追加**：`main.py:876-877` + `OUTROS`；prompt 明令 AI 禁写，生成后还会正则删掉 AI 偷写的结语。
7. **人设 key 必须是 `老师 / 学术AI / 暴力极客 / 温柔小姐姐 / 阳光小哥哥`**——见 P1-4。
8. **占位符机制**：`@@IMAGEBLOCK{n}@@ / @@MERMAIDBLOCK{n}@@ / @@KEYWORD{n}@@ / @@MATHBLOCK{n}@@`，必须“先恢复、后清理”，顺序错了就白屏（`exporter.py:95-123`）。
9. **所有路径以 `core.database.BASE_DIR`（项目根）为锚**；运行目录不是项目根时 `assets_images` 与 `term_finale_pro.db` 会指错。
10. **`file_type` 四个取值 `guide/analysis/extract/exam/note`** 与 UI 分组、历史查询、`exporter` 的 `doc_type` 三处对应。

---

## 8. 已知问题（按严重度，全部有代码依据）

### P0 — 会丢数据 / 会炸
1. **删科目会删掉用户桌面上的原始课件**
   `main.py:400-419`：`for m in c.materials: os.remove(m.file_path)`，而 `m.file_path` 就是上传时的原文件路径（实测指向 `~/Desktop/物一1_CH03刚体力学基础(1).pdf`）。用户点一次“删除科目”，原始 PDF 就没了。**优化时第一优先修。**
2. **`.env` 被 git 跟踪**：密钥已进历史；`git rm --cached .env` 只能止血，历史仍需清理。
3. **停止生成的竞态**：`stop_generation (:767)` 立刻 `show_dashboard`，但工作线程只是“下次循环时”检查 `stop_event`。期间后台仍可能继续调 API、写桌面文件、写 DB，并通过 `after()` 去 configure **已销毁**的 `progress_label`（TclError），或在 `:895` 无条件 `show_preview_screen`（此处未检查 stop_event）。

### P1 — 功能实际是坏的
4. **人设菜单与 PERSONAS 的 key 对不上**
   `main.py:677-681` 的选项是“温柔小姐姐 (适合零基础) / 学术AI / 老师 / 温柔小哥哥 / 暴力极客”，取 key 用 `split(" ")[0]`：
   - `温柔小哥哥` **不在** `PERSONAS` 里 → 静默回落到“温柔小姐姐”，选了没用；
   - `阳光小哥哥` 有 prompt 也有结语，但**菜单里选不到**。
5. **视觉模型名疑似不存在**：`core/ai_vision.py:26` 用 `model="qwen3.8-max"`，代码注释自己都写着“如果 404 请换 `qwen-vl-max`”。异常被 `:57-60` 吞掉并返回 `"原题配图"`，所以**表面不报错，实际所有图片图注都退化成同一句“原题配图”**。
6. **`open -a "Microsoft Edge"` 的 fallback 永远不会生效**：`main.py:1353-1358`、`:1340-1348` 用 `subprocess.run` 包在 `try/except` 里，但 `open` 找不到 App 时返回非 0 而**不抛异常** → 没装 Edge 的机器上点“打开”静默无反应。
7. **没有依赖清单**：换机器 / 打包 / CI 都复现不了（还踩在 Python 3.14 这种新版本上）。

### P2 — 质量与体验隐患
8. **图片命名会冲突**：`doc_{img_index}.{ext}`（`parser.py:123`）在不同 docx 间必然重名 → 后解析的覆盖先解析的，旧讲义图片变错图。`pdf{n}_{x}.png` 一律 `.png` 扩展名，但 PyMuPDF 给的可能本就是 JPEG 字节 → 导出 `data:image/png` 与内容不符，Chromium 系通常能容错，但属于隐患。`slide`/`pdf` 用 `len(os.listdir)+1` 也依赖目录状态，天然易撞。
9. **编辑“上传资料”会累积重复项**：`show_upload_setup:523-529` 把 DB 材料 append 进 `self.temp_materials` 但**不清空**；`handle_course_submit` 的 edit 分支（`:510-517`）也不重置 → 反复进出编辑页会出现重复条目，保存后 DB 里就有重复 materials。
10. **页数上限有漏洞**：`main.py:804-809` 的 15 页截断只在“core 与 ref 同时存在”时生效；只有一类资料时**不截断**，几百页 PDF 会变成上百次串行 API 调用（费用与时长都不设上限）。
11. **渲染依赖外网 CDN**：`exporter.py:169-172` 的 KaTeX / Mermaid 都从 `cdn.bootcdn.net` 拉。断网或墙内 CDN 抖动 → 公式不渲染、思维导图空白（虽然加了虚线框兜底）。与“本地化工具”的定位冲突。
12. **“导出 Word”实为 HTML 改名 .docx**：`exporter.py:202-208`，Word 能打开但会提示格式不符。
13. **i18n 覆盖不全**：切到 EN 后，人设菜单、难度菜单、“打开”、“生成类型：”、“总分/分值”提示等仍是硬编码中文（`main.py:677-681, 1050-1052, 1069-1071, 1108-1121, 1130-1131, 719/944/1350`）。
14. **限额可绕过**：每日 20 次记在本地 `user_config.json`，改文件即清零；且 `show_onboarding_2:256` 写配置时用 `{"name": name}` 覆盖，会把 usage 一并抹掉。
15. **章节编号靠正则硬匹配**：AI 若把 `## 核心考点：` 写成 `## 考点：` / 带 emoji / 三级标题，目录与 `#chapter-N` 锚点全丢（`exporter.py:66`）。
16. **`clear_ui` 全量重建**：每次切换页面 `destroy` 所有子控件再重建（`:214-217`），没有页面栈/缓存；“返回”靠重新调用上一页函数，状态靠实例属性硬撑，`after()` 回调很容易打空。

### P3 — 清理项
17. `core/text_exporter.py`（333 行）与 `exporter.py` 约 95% 重复且无人引用——**它里面那个更宽松的 mermaid 正则反而更健壮**，建议比对后合并，删掉冗余文件。
18. `ui_main.py`(374)、`ppt_images/`、`test_api.py` 均为无引用遗留。
19. `main.py` 1395 行 / 单类 50 方法，UI、线程、DB、限额、日志全揉在一起，无分层。
20. `assets_images/` 无去重、无 GC、无引用计数：材料删了图片还在，13MB 只增不减。

---

## 9. 改动前的纪律（我给自己定的）

1. **先备份再动手**：改前 `git stash` 或复制一份 `.bak`；当前有大量未提交改动（`AM`/`M`），不先提交就没法回滚。
2. **小步 + 每步可验证**：一次只改一个关注点，改完立刻编译（`python -m py_compile`）+ 起 GUI 走一遍。
3. **回归路径（每次改完都跑）**：
   启动 → onboarding / 仪表盘 → 新建科目 → 上传 PDF → 生成讲义（全量）→ 打开 HTML 看公式/图片/思维导图/名词弹窗 → 复习中心三个功能各点一次 → 笔记保存 → 归档列表 → 删除科目（**在修好 P0-1 前别拿真文件试**）。
4. **绝不擅自改第 7 节的字符串协议**；必须改时三端同步并当场验证 HTML。
5. **不删文件、不改 `.env`、不碰 `.git` 历史**，除非你明确要求。

---

## 10. 建议的优化顺序（等你点头再动）

| 顺序 | 事项 | 理由 |
|---|---|---|
| 1 | 修 P0-1（删除科目只删 DB 记录 / 或先移入废纸篓） | 唯一会毁用户数据的 bug |
| 2 | 修 P1-4 人设映射 + P1-5 视觉模型名 | 一行改动，功能立刻真实生效 |
| 3 | 加 `requirements.txt` + 首次运行环境自检（缺密钥时友好提示） | 可复现才谈得上优化 |
| 4 | 修 P1-6 打开文件逻辑（`subprocess` 返回值判断 + `webbrowser` 兜底） | 影响所有“打开/预览”路径 |
| 5 | 合并 `text_exporter.py` 的 mermaid 正则、删死代码 | 降低后续改动的心智负担 |
| 6 | 拆 `main.py`：`ui/`（页面）+ `services/`（流水线）+ `core/`（纯逻辑） | 结构性优化，风险最大，放最后且分多次 |

---

## 11. 第二轮诊断：内容质量与 UI（2026-11-02 晚，实测数据）

### 11.1 输出质量的量化事实

| 指标 | 实测 | 结论 |
|---|---|---|
| 同课程同 PDF，全量(1057) vs 精简(1100) 的 6-gram 重合 | **10.4%**；全量内容仅 19.7% 出现在精简中 | 两次生成≈两篇独立作文，run-to-run 方差极大 = 用户说的"不稳定" |
| 全量 vs 精简 净字数 | **24554 vs 25313**（精简反而 +3%） | "保命流"未产生压缩效果，产品定位（7天冲刺）与输出矛盾 |
| 32 页 PDF 生成的章数 | **16 章**，每章 1500–2700 字 | 章 = 2 页 PPT 片段，无全局主线 |
| 章节标题 | `第 1 章：核心考点：刚体力学基础…` | 双前缀（`exporter.py:66` 改写时保留原文） |
| 训练试卷 | 7188 字，含"答案与解析"，无"参考原资料" | 试卷链路相对健康 |
| 五步结构完整率 | 中文版 16/16 | prompt 的结构约束有效，但也是"每章同构"的来源 |

### 11.2 内容质量根因（改 prompt 治不了的）

- **C1 方差无约束**：prompt 只有"五步 + 严禁"负面清单，没有"内容必须来自原文条目"的硬锚点；块间无共享大纲。
- **C2 mode 形同虚设**：`ai_engine.py:57-60` 仅两句差异，而"五步结构"强制产生固定体积，mode 无法压缩。
- **C3 章无语义**：`main.py:811-823` 按 2 页切块，章节标题由 AI 从 2 页中猜。
- **C4 输入已失真**：`parser.py` 输出纯文本流，丢失标题层级/表格/公式结构；`clean_text_lines:24` 会丢弃 `len<=3` 的符号行（常为公式、选项）。
- **C5 4096 输出硬顶 + 无 finish_reason 检测**：`ai_engine.py:121-126`。
- **C6 无质量闭环**：不存 raw md、不记 token、无固定评测集、无自动校验 → 改 prompt 属盲改。

### 11.3 UI 现状量化（main.py）

- 裸颜色字面量 39 处（`#E5E5E5` 独占 21 处）；硬编码 `padx/pady` 150 处、`width/height` 92 处 → 无设计 token，改风格需动几十行。
- 6 处 `winfo_children()` 全量销毁重建 → 切页闪烁、滚动位置丢失。
- 13 处 `messagebox` 阻塞弹窗；68 个 emoji 当图标（Windows 渲染不一致）。
- 字体写死 `PingFang SC`，Windows 无此字体 → 打包后排版崩。
- 强制 `Light` 模式，无深色模式；生成页仅一条进度条，无分块日志。

### 11.4 修订后的施工顺序（按"立刻有感"排序）

| 批次 | 内容 | 验收标准 |
|---|---|---|
| 1 止血+可观测 | 删除保护、`logger.add`、raw md 落盘、`finish_reason` 记录、requirements | 删科目不删原件；每次生成有 `debug/` 证据 |
| 2 内容质量 v1 | 全局大纲先行 → 按大纲分批写；精简流结构性压缩；生成后自动校验 | 两次生成重合 >60%；精简字数 < 全量 50% |
| 3 解析质量 | 标题层级、表格、公式、双栏排序 | 喂给 AI 的文本保留章节结构 |
| 4 UI | 设计 token、组件化、页面栈、字体回退、深色模式 | 换配色只改一处；Windows 不崩排版 |
| 5 工程/分发 | 清死代码、拆 main.py、WAL、缓存 GC、PyInstaller + Python 3.12 | 粉丝双击可运行、崩溃有日志 |

### 11.5 目视审计（实跑 11 页截图，存 `docs/probe/ui/`）

| # | 视觉缺陷 | 出现页面 | 代码原因 |
|---|---|---|---|
| U1 | OptionMenu 变成整条**蓝色色块**，抢占视觉重心 | 课程表单/模式选择/训练 | `CTkOptionMenu` 默认 `fg_color` 用主题色，width 300~400 |
| U2 | 内容只占左侧 ~800px，右侧大片空白 | 全部 | 卡片 `fill="x"` 但无 max-width / 双列 |
| U3 | 参考卡片内部约 400px 空白 | 上传页 | 布局高度未约束 |
| U4 | 第三张卡片文字被**裁切**（"生成整套冲刺试"） | 复习中心 | `width=280` 且无 `wraplength` |
| U5 | 复选框**双框**（自带框 + 文案里的 ☑️） | 训练页 | i18n 文案里带 emoji |
| U6 | 主按钮对齐不一致（有的右浮、有的居中） | 各页 | 各页 pack 参数不同 |
| U7 | 滚动条粗黑、压在卡片上 | 全部 | CTkScrollableFrame 默认样式 |
| U8 | "打开"按钮对比度过低，像禁用态 | 历史记录 | `#F0F8FF` 底 + 浅蓝字 |
| U9 | 仪表盘主区空白率约 80% | dashboard | 只有欢迎语+名言 |
| U10 | 紧迫度显示 100/100/91 → 算法饱和 | dashboard 侧栏 | urgency 上限被顶满 |
| U11 | 课程卡只有名字+分数，无剩余天数/进度 | dashboard 侧栏 | 信息未建模 |
| U12 | Emoji 当图标（📚🗑️📄✏️🧠🔍📝📛🌐🚀） | 全部 | 无图标系统 |
| U13 | 历史记录出现重复条目 | 复习中心 | 生成记录去重缺失 |
| U14 | 两处"历史记录"区块内容重复（讲义页 2 条 / 复习页 7 条） | 模式选择/复习中心 | 分区查询未去重 |

**正面**：配色克制、留白充足、PingFang 渲染清晰、圆角统一（12）、边框统一。问题集中在"控件默认样式没收敛"+"信息层级缺失"，不是审美取向错误。**U1/U4/U5/U6/U8 是半小时级修复**，能立刻去掉大半"廉价感"。


---

## 12. v2 重构后的现状（2026-11-02）

### 12.1 新结构

```
main.py                 只剩 UI（约 1400 行），通过 services 调用业务
launcher.py             打包入口（崩溃日志兜底）
app/desktop/            theme.py（设计 token） + components.py（9 个组件）
services/               task.py / guide_service.py / review_service.py（零 tkinter）
core/
  paths.py config.py logger.py maintenance.py platform_utils.py personas.py
  parsing/figures.py    图形区域检测与渲染
  generate/             outline.py（大纲） exam_builder.py（组卷+验卷）
  quality/qa.py         10 项生成质量校验
  parser.py exporter.py database.py ai_engine.py exam_engine.py ai_vision.py
models/user_profile.py  压力模型（含 advice）
tests/                  test_weights / test_maintenance / test_config
tools/                  build.py / smoke.py
legacy/                 归档的旧实现（ui_main_v0 / text_exporter_v1 / test_api_zhipu）
```

### 12.2 旧问题对照（第 8 节那批）

| 编号 | 旧问题 | 状态 |
|---|---|---|
| A1 | 删科目真删桌面原件 | ✅ 已修（第 11 轮）：只删本软件生成的产物，不动 `materials.file_path`；已用模拟删除验证「原件仍在 / 生成物已删 / DB 记录已清」 |
| A2 | 停止生成是假停止 | 🟡 部分：进度回调已做控件存活判断，工作线程仍靠 stop_event 轮询 |
| B1–B6 | 人设 key / 视觉模型名 / Edge 打开 / 重复材料 / 标题双前缀 / 补图位置 | ✅ 全部修复并验证 |
| C1–C7 | 内容不稳定 / 精简无效 / 2页一章 / 解析丢结构 / 4096 截断 / 无评测 / 矢量图 | 🟡 C1/C2/C3/C5 已在 P3 重构；C4（标题/表格结构化）留在 P8；C6 已加 debug 与 QA；C7 已修 |
| D1–D8 | UI 粗糙 | 🟡 D1/D2（token、组件）已做；D3（字体栈）已做；D4 emoji、D5 messagebox、D6 深色、D7/D8 部分完成 |
| E1–E7 | 工程债 | ✅ requirements / 日志 / 缓存 / 死代码 / WAL 完成；E6（拆 main.py）部分；E7 打包已完成 |

### 12.3 新增的隐形协议（务必与第 7 节一起看）

| 协议 | 位置 | 说明 |
|---|---|---|
| `on_progress(ProgressEvent)` | `services/task.py` | 服务层只上报进度，不碰控件；UI 用 `_on_service_progress` 桥到主线程 |
| `[[[IMAGE: 文件名 \| 图注: xxx]]]` | `core/parsing/figures.py` → `exporter.py` | 图由解析器锚定，AI 只负责写讲解 |
| `Outline` / `Chapter` | `core/generate/outline.py` | 章节/必考点/篇幅；AI 失败自动退回启发式 |
| `Blueprint` | `core/generate/exam_builder.py` | 组卷先定题型×数量×分值，再验卷 |
| `paths.*` | `core/paths.py` | **禁止再出现** `os.path.dirname(__file__)` 存数据 |
| `theme.*` | `app/desktop/theme.py` | **禁止再写裸色值**，新代码一律取 token |

### 12.4 回归方式

```bash
python tools/smoke.py          # 6 项离线冒烟（不联网）
python -m tests.test_weights   # 权重模型单调性
python tools/build.py          # 打包（会检查 Python 版本）
```

界面回归：`/tmp/ui_regress.py` 那类脚本（截图 8 页）已多次使用；需要时按 `docs/HANDOVER.md` 重建。

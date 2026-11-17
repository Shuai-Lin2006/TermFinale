# v3 全量测试报告（2026-11-09）

> 结论：核心闭环 + 四类任务 + 课程卡片 + 中/EN 切换 + 全站 AI 助教 + 个人资料 + 自动大纲/页图 + DOCX 输入 + 讲义 Word 导出均已跑通；
> 仍不能称“终极发布”，因为人工复核/golden set、OCR 图片输入、任务 Word 导出、Word 客户端版式和打包未完成。

## 1. 单元/集成测试

```bash
PYTHONPATH=. .venv/bin/python -m unittest \
  tests.test_tfv2_lecture tests.test_tfv2_page tests.test_tfv2_ingest_pptx \
  tests.test_tfv2_ingest_pdf tests.test_tfv2_ingest_text tests.test_tfv2_outline \
  tests.test_tfv2_render tests.test_tfv2_authoring tests.test_tfv2_assemble \
  tests.test_tfv2_pdf tests.test_tfv2_answer_audit tests.test_tfv2_figure_report \
  tests.test_tfv2_coverage_audit tests.test_tfv2_content_gate tests.test_tfv2_library \
  tests.test_tfv2_build tests.test_tfv2_retrieval tests.test_tfv2_store \
  tests.test_tfv2_language_gate tests.test_tfv2_llm_json tests.test_tfv2_product \
  tests.test_tfv2_tasks tests.test_tfv2_docx
```

结果：**163 tests OK**（77 v2 + 86 v3）。v3 包含 product 17、tasks 8、docx 5、multi 2、exam 3、figures 24、agent 24、pdf_gate 2、language 1。

## 2. 浏览器验收

`tools/product_acceptance.py`（Edge/Playwright）最近一次：

- `nav_svg=9`（侧栏不再用字体符号，乱码已消除）
- `course_cards=4`、`course_page=true`（课程卡片 → 课程页）
- `artifact_quality=true`、`artifact_sections=8`
- `word_link=true`、`word_ok=true`（原生 `.docx` 200 + 正确 MIME）
- `reader_frames=2`、`reader_katex=653`、`reader_math_ready=true`
- `profile=true`、`ai_drawer=true`、`new_fields=true`（重点/不考）
- `notes_page=true`、`workbench=true`、`new_form=true`
- `theme_toggle=true`、`mobile_sidebar_open=true`
- `page_errors=[]`

英文 UI：`#langBtn` 切换后：
- 导航 `Today / Courses / Workbench / Practice / Review / Notes / Settings`
- 首页 `ONE THING TO DO TODAY / Continue reading / Do now / Courses`
- 课程 `Courses / Open course / Needs review`
- 工作台 `Workbench / Key points / Terms / Original questions / Generate paper / Logic analysis`
- 设置 `Settings / Appearance / Site theme / Models`
- 动态覆盖单位 `85/85 pages`（英文），切回中文恢复。

### 2.1 UI 全按钮 sweep

`tools/ui_sweep.py`（Edge/Playwright）：

- 8 个路由全部可加载：今日、课程、工作台、练习、复习、笔记、设置、新建；
- 个人资料保存、主题切换、中/EN 切换、课程卡→课程页→质量报告→阅读器；
- 阅读器：搜索按钮/搜索计数（1/61）、AI 打开/关闭、导出菜单打开/关闭；
- 全站 AI 抽屉打开/关闭；
- 工作台 5 个 tab、运行按钮、新建页自定义提示词/权重提示字段；
- 移动端 390×844 菜单打开；
- `new_custom_prompt=true`、`new_weight_hint=true`、`multi_form=true`；
- `page_errors=[]`，`ok=true`。

### 2.2 AI 助教 / 个人资料手工测试

- 全站右下角 `AI`：首页（无资料）可自由对话；返回“像通用 AI 一样自然对话…”，0 JS 错误。
- 讲义页：上下文显示“当前资料：第三章 电路的暂态分析”，快捷按钮“解释这一节/出 2 道题/提炼重点/7 天计划”；回答带页码（44、45、59）。
- 会话持久化：关闭/重开抽屉仍能看到上一轮。
- 左下角个人资料：默认“学习者/学”，设置改名“小明”后头像变“小”、姓名即时更新；API 默认可恢复“学习者”。

## 3. 逐页结构审计

`tools/page_audit.py` → `docs/evidence/v3_page_audit.md`、`.json`。

| 产物 | 页 | block 引用 | 语义审计 | 缺口 |
|---|---:|---:|---|---|
| v2_circuit | 6/85 scope | 6 | 无 | 未做语义审计 |
| v2_circuit_full | 85/85 | 85 | 80 covered + 5 overview | 无 |
| v2_english | 3/3 | 3 | 无 | 未做语义审计 |
| v2_medical | 24/24 | 无 sections.json | 22 covered + 1 visual + 1 overview | 无 block 级页覆盖；第 17 页 visual |
| v2_ring_full | 50/50 | 48 | 38 covered + 10 visual + 2 overview | 缺 block 页 8、13（visual） |

- 只有 `v2_circuit_full` 同时满足“block 全页 + 语义审计 0 partial/missing/visual”，所以只有它标“可读”。
- `v2_medical`、`v2_ring_full` 是 visual 页待复核；`v2_ring_41*` 两个缺 block 页的旧样例已归档到 `data/archive/legacy_artifacts/`；`v2_english`、`v2_circuit` 没有语义审计，只能“待复核”。
- 这是结构排查，不是学科专家逐页签字。

## 4. 端到端生成

| 场景 | 结果 |
|---|---|
| 6 页医学 PDF | 1 节、outline=true、自动抽到 2 张页图、Gate 过、PDF 生成、状态待复核 |
| 1 页医疗 DOCX | LibreOffice 转 PDF → 页账本 1 页 → 生成成功、outline=true |
| 1 页 PDF | 生成成功、outline=true；重点“内脏神经系统”落到正文；页脚为“可涵盖…约100%的内容…”；结语按人设 |
| 1 页 PDF + 不考词 | 模型若写入不考词会硬失败；本轮实测生成结果未出现不考词，通过 |
| 1 页 PDF + 权重 5 | `内脏神经系统=5` 解析为权重；正文出现 8 次，通过；权重 ≥4 只出现一次会失败 |
| 35 页高数 PDF | 5 节、页覆盖 100%、Gate 过、`导数=5/连续=3` 权重生效（导数 104 次），自定义提示词写入 manifest |
| 24 页医学 PDF | 3 节、页覆盖 100%、Gate 过、9 张图（视觉模型逐图图注），无文本层页用整页扫描图明确标注 |
| 多资料合并（API） | 2 份资料权重 5/1：合并 7 页、2 节、100% 覆盖、权重写进 constraints；高权重切分更细 |
| 多资料合并（UI） | 新建页多选 2 份、权重 5,1、提交 → Job 完成、生成物进库（待复核）；0 JS 错误 |
| 多资料权重效果 | 2×6 页、权重 5/1 → 3 节：权重 5 拆成 2 节（4+2 页），权重 1 只 1 节（6 页） |
| 计算/简答提取 | 2 道计算 + 1 道简答，答案标“需人工审计”，选择题仍独立答案审计 |
| 试卷 PDF | 在 LLM 前拒绝，清理 artifact/上传，不留残缺目录 |
| 提取考点（全部 85 页） | 72 条，页覆盖 100%，状态 `validated`；按 12 页分段+补漏，不再只抽前几页 |
| 提取原题（电路例题节） | 支持计算/简答；实测抽出 2 道计算题 + 1 道简答题，状态 `partial`（页覆盖 38%，不冒充全量）；选择题仍做 4 选项校验 |
| 模拟试卷 | 2 题，第二遍独立解题答案审计一致，`validated` |
| 混合试卷 | 1 选择 + 1 计算 + 1 简答，`validated`；选择题独立答案审计通过，计算/简答 `manual=true`，UI 显示“参考答案”与人工审计提示 |
| 100 分训练卷（默认蓝图） | 电路：10 选择 + 5 填空 + 4 计算 + 2 简答，**21 题、总分 100、`validated`**；9 道选择题审计冲突经三审/换题解决 |
| 训练模式四模式 | 模拟 `validated`；原题改数 `validated`；预测 + 真题参考 `validated`（reference_used=true）；原题变式 `validated` |
| 资料原图复用 | 出卷按 source_page 映射 artifact figure_list，显示资料原图；无图才用 figure_description |
| AI 重写本节 | 阅读器按钮存在；预览/替换/撤销 |
| 整份 AI 改写 | 质量报告页 + 全站 AI 抽屉“整份改写”均可发起；新草稿、逐节 diff、重新 Gate/PDF；一键替换原稿先自动备份；实测 accept 更新原稿、restore 恢复成功；可丢弃草稿 |
| 资料原图复用 | 出卷按 source_page 映射 artifact figure_list；无图才用 figure_description |
| 任务 PDF | 提取/导图/试卷 docx→PDF 200，7 页 |
| 生成语言 | 讲义/多资料/工作台/出卷均有 gen_lang；英文 1 页讲义通过语言门禁；英文提取 21 条、0 中文字符 |
| 三语阅读器 | 壳简/繁/EN 循环；阅读器工具栏切“搜尋/EN/简”，0 JS 错误 |
| 图片/扫描 PDF OCR | PNG 1 页 OCR→1 页讲义 100%；无文本扫描 PDF 回填 332 字；扫描化学试卷 3 页 OCR 含 Markdown 表格；扫描页讲义 Gate 通过 |
| 结构化示意图 | 12 道电路计算题 100 分 `validated`；8 道简单串联题用模板重画并嵌入 Word/PDF；化学 RDKit、流程、函数图路由已通；复杂拓扑不冒充精确图 |
| Qwen-Image 接入 | 百炼 `qwen-image-3.0` 实测 200；约 $0.025/张；已接讲义可选装饰背景，默认关；同 Key，无需新注册 |
| 全站 AI 整份改写 | AI 抽屉“整份改写”入口存在；API 生成草稿/替换/恢复通过 |
| 异步任务队列 | 讲义/多资料/试卷/任务均走 job；试卷/任务可轮询进度、取消；取消后不落库 |
| 任务原生 Word | 提取考点/思维导图/试卷 docx 200，docx 可打开 |
| 三语切换 | 简 → 繁 → EN → 简；`zh-Hant` 导航/设置/表单完整，0 JS 错误 |
| 思维导图 | 电路全资料 31 节点，节点带页码范围，覆盖 85/85 页，状态 `validated` |
| 逻辑分析 | 七件套完整，12 个页码引用，`validated` |

### 4.1 讲义标准逐项

| 标准 | 现状 |
|---|---|
| 人设/深度 | 人设 prompt + 5 种结语；深度受目标分/天数/基础影响 |
| 标头 | 标题/课程/目标/天数/基础/资料/覆盖页（见 `docs/evidence/lecture_page1.png`） |
| 摘要/目录/页码 | 标题下先“本资料讲什么”+知识地图/考点分布，再目录（带成稿页码），正文从“第一章/第一节”开始 |
| 每节出处 | 每节末尾“出处：第 X–Y 页” |
| 重点/不考 | 表单字段 + prompt + 关键词硬检查（未落重点/出现不考词直接失败） |
| ≤159 页全覆盖 | 大纲缺页自动补“补充”段；scope/页脚按实际覆盖算；测试 1 页/6 页均 100% |
| 图片 | 按页插到对应讲解段后；无匹配时放在小结前；图注+页码+人工复核提示 |
| 教材式排版 | 单栏正文、目录、页脚；见 `docs/evidence/lecture_page5.png`；不使用大卡片 |
| 结语 | 正文末尾单独大段，5 种人设不同文本 |
| 页脚 | “本资料由 TermFinale 智能体生成，可涵盖《…》约 …% 的内容；具体请以实际资料为准…”一行小字 |

## 5. 原生 Word

`/artifact/v2_circuit_full/lecture.docx`：

- 3.7 MB，144 段，14 张 inline 图；
- 0 个 `$`/反斜杠原始 LaTeX；
- TOC、正文、图注、出处、页脚、PAGE/NUMPAGES 字段；
- docx 测试 5 项通过。

限制：
- 未在 Microsoft Word 客户端做版式验收；
- 本机 LibreOffice headless 没有 CJK 字体映射，docx→PDF 预览中文显示方框，不能作为 Word 视觉通过；
- TOC 页码用 spec 估算，不在 Word 里重算；
- 公式是线性 Unicode 文本，不是 OMML；矩阵/对齐环境会退化。

## 6. 仍缺

1. 人工复核工作流已接（复核人/意见/日期），但还没有学科专家实际签字和 golden set；讲义“可做题”仍需学生实测。
2. OCR/图片/扫描件输入：图片、扫描 PDF、复杂表格已接 OCR，表格转 Markdown；复杂手写/低清扫描仍 best effort。
3. AI 已支持阅读器重写本节、质量报告页/全站 AI 抽屉整份改写、一键替换+备份+恢复；仍未做 AI 规划器/工具调用。
4. 四类任务已补原生 Word + PDF（`/api/documents/{id}/docx|pdf`）。
5. 训练模式已把真题解析成结构化题型/分值表；但真题文本复杂的扫描卷/表格仍可能解析不准，需人工核对。
6. 物理/电路题优先复用资料原图；无匹配图时输出详细 figure_description，仍没有真正文生图。
7. 考点/名词已按 12 页分段+补漏；本轮电路全 85 页考点 72 条 100% 覆盖并通过；名词尚未跑同等规模样例。
8. 自动配图是视觉识别+页锚定+段落匹配，不是语义配图；需逐图核对。
9. Word 客户端版式、Windows、打包/公证（本轮按用户要求不做）。
10. 三语壳已接（含阅读器），生成内容仍保持源语言/生成语言，不做机器翻译。


## 本轮逐页机器排查（2026-11-10）

- 116 项单元测试通过；
- 页面结构审计 5 份在库产物：`v2_circuit_full` 85/85 block 页、0 缺页；`v2_ring_full` visual 10 页、0 缺 block；`v2_medical` 无 sections.json，block 级 n/a；`v2_english`、`v2_circuit` 无语义审计，保持待复核；
- PDF 逐页：所有在库 PDF **0 空白页**；Word 图数/段落可打开；
- 阅读器：电路 8 节/14 图、医学 5 节/2 图、英文 3 节/0 图；图片 broken=0、KaTeX error=0、横向溢出=0；
- UI：桌面 9 路由 + 移动端 9 路由，0 JS 错误；修复移动端设置页横向溢出（grid/card min-width）；
- 2 个缺 block 页的旧样例 `v2_ring_41`、`v2_ring_41_gentle` 已归档到 `data/archive/legacy_artifacts/`，不再进库/审计；源文件未删；
- `tools/golden_eval.py`：15 份在库文档，validated 文档 0 结构/分值/重复题错误；历史 rejected 文档保留但不冒充；
- `tests/test_tfv2_figures.py`：电路串联、化学 SMILES、流程图、函数图 4 项渲染测试通过。


## 非人工项推进（2026-11-10 第二段）

- 长任务队列：讲义/多资料/试卷/工作台任务全部 job 化；试卷与任务可轮询进度、取消；取消不落库；
- 掌握度：拉普拉斯平滑掌握分 + 置信度 + weak/learning/strong 标签；复习间隔扩到 1/2/4/7/15/30 天；
- truth 评测：新增 `tools/truth_eval.py` 与 `docs/golden/truth_cases.json` 模板，人工填 must_contain/must_not_contain 后自动跑；
- 机器回归：116 tests、golden eval 15 文档 0 validated 结构错误、页面审计/PDF/阅读器/UI/mobile 全通过；
- 未完成：AI 规划器/工具调用、复杂学科图全自动、Electron 打包（本机无 node/npm）、真学生效果。


## Agent P0（2026-11-10）

- 工具注册表 8 个：search/read_page/get_artifact/get_learning_state/review_plan/practice/exam/lecture；
- 意图规划：复习计划、检索、读页、出题、出卷、新建讲义；写操作只返回 action，不自动落库；
- 所有结果带 citations；trace 记录工具/参数/成败；
- 全局 AI 抽屉“执行任务”已接；实测 7 天复习计划、检索“换路定则”、解释第 6 页均通过；
- 4 项 agent 单测；全量 120 tests。


## Agent P1（2026-11-10）

- `/api/agent/plan`：只规划，不执行；生成/出卷标 `requires_confirmation`；
- `/api/agent/jobs?confirm=true`：后台执行，可轮询/取消；当前可执行出卷（按目标里的题量，最少 12），并接复习计划；
- 生成讲义仍返回“去新建讲义”action，不绕过上传；
- UI：执行任务 → 计划卡 → 执行计划 → job 进度/取消 → 结果；
- 修复 `job.result` 已是对象时 UI 还 JSON.parse 的 bug（试卷/任务/Agent 三处）；
- 6 项 agent 单测；全量 122 tests。


## Agent P2（2026-11-10）

- LLM 规划器：工具白名单校验、最多 4 步、非法工具丢弃、失败回退确定性规划；
- 多步执行：get_learning_state → search_material → make_review_plan 实测 trace 全 ok；
- 出卷计划：LLM 返回 generate_exam + make_review_plan，`needs_confirmation=true`；
- 运行历史：`/api/agent/runs` + AI 抽屉“最近任务”；
- UI 计划卡显示 planner 来源（llm/fallback）；
- 确认后的计划通过 steps 原样执行，不会二次规划跑偏；
- 10 项 agent 单测；全量 126 tests。


## Agent P3（2026-11-10）

- 计划编辑：AI 抽屉计划卡可改 JSON steps 后应用；
- 工作流保存/载入：`agent_workflows` + `/api/agent/workflows`；计划卡“保存工作流”；
- 长期目标：`agent_goals` + `/api/agent/goals`；
- 只读工具自动重试 2 次，trace 记录 attempts；
- 执行使用确认后的 steps，不会二次规划；
- 11 项 agent 单测；全量 127 tests。


## Agent P4（2026-11-10）

- 断点续跑：job 每步把 steps+result 写入 result；失败/取消后 `/api/agent/runs/{id}/resume` 跳过已完成步骤，只跑剩余；
- `run_workflow(resume=True)` 支持跳过已完成；修复 steps 清理时丢掉 result/ok 的 bug；
- UI 最近任务里失败/取消任务有“继续”按钮；
- 计划编辑/工作流保存/长期目标/只读重试仍保留；
- 12 项 agent 单测；全量 128 tests。


## Agent P5（2026-11-10）

- 长期目标：`next_run/last_run/enabled` 迁移；`due/advance/plan` API；AI 抽屉“长期目标/生成今日计划”；
- 工作流版本：同名保存自动 version+1；`/api/agent/workflows/{id}/diff` 返回 unified diff；
- 计划编辑/保存/载入、resume 保留；
- 14 项 agent 单测；全量 130 tests。


## Agent P6（2026-11-10）

- 独立只读步骤并行执行（ThreadPoolExecutor，最多 4）；trace 标 parallel；
- resume 与并行兼容：已完成步骤跳过；
- 长期目标 due/advance/plan、工作流版本/diff 已接；
- 已做 depends_on 拓扑排序（含环回退）和 read_page→search 自动修复；仍未做：并行 DAG 层、LLM 自动重规划、可视化参数表单、常驻目标调度器；
- 17 项 agent 单测；全量 133 tests。


## P7 R1（2026-11-10）：DAG 分层并行

- `_topo_levels`：按 depends_on 分层；同层只读步骤 ThreadPool 并行；
- 跨层等待依赖；有环回退原序；
- resume 与分层兼容；
- 18 项 agent 单测；全量 134 tests。

## P7 R2（2026-11-10）：失败重规划

- 步骤失败后 job 标 failed（不再假 done），保留 steps/result；
- `/api/agent/runs/{id}/replan`：只对失败后的剩余步骤生成新计划 + diff；
- LLM 规划失败回退 `read_page→search_material`；
- UI 失败结果出现“重规划”，确认后执行新计划，不自动重复扣费；
- 19 项 agent 单测；全量 135 tests。

## P7 R3（2026-11-10）：可视化计划表单

- `TOOLS` 增加 args schema；`/api/agent/tools` 返回参数说明；
- 计划卡“表单编辑”：工具下拉 + 参数输入 + 加一步/删一步/应用；
- JSON 编辑保留；
- 20 项 agent 单测；全量 136 tests。

## P7 R4（2026-11-10）：常驻目标调度

- `agent_goals.auto/artifact_id`；`due_auto_goals`；
- `run_due_goals`：只自动执行不需要确认的步骤；生成/出卷只生成计划；
- `POST /api/agent/goals/run-due`；FastAPI startup 常驻线程每 5 分钟检查一次（`TERMFINALE_GOAL_SCHEDULER=0` 可关）；
- AI 抽屉“运行到期目标”；
- 21 项 agent 单测；全量 137 tests。


## 全学科图编译器（2026-11-10）

- `figure_compiler.py`：域名注册表 + spec 校验 + 渲染 + 失败关闭；
- 支持：电路（串联模板）、物理（受力/几何）、数学（点列）、化学（RDKit）、计算机（流程）、统计/柱/线/饼图、概念图；
- 医学/生物/地理/历史：**不生成精确图**；仅图表可用，其余原图/描述；
- `GET /api/figures/subjects` 返回支持矩阵；
- 8 项 figure 单测；全量 142 tests。

## 图编译器扩展（2026-11-10）

- 并联电路拓扑模板；
- 刚体/受力模板（斜面+力箭头）；
- 符号数学：sympy 表达式→matplotlib；
- 化学反应：RDKit reaction SMILES；
- 医学/生物/地理/历史失败关闭；
- Agent 自动修复：失败后预算 1 次、只重规划只读步骤、diff 记录；
- 142 tests。


## P8 R1（2026-11-10）：通用图适配器

- 新增几何、表格、时间线、示意地图、通用 elements 适配器；
- 医学/生物：图表/表格/时间线允许；解剖结构仍失败关闭；地理允许示意地图，并明确非精确边界；
- 9 项 figure 单测；全量 143 tests。


## P8 R2（2026-11-10）：网表/多步反应/原图管线

- 电路串联网表：components 列表，支持 4+ 元件；
- 化学反应序列：steps → 多张 RDKit 反应式纵向 Step 1/2；
- source-only：资料原图复制/校验，医学/生物/地理/历史不生成精确结构；
- 11 项 figure 单测；全量 145 tests。


## P8 R3（2026-11-10）：跨学科图基准

- `tools/figure_benchmark.py`：19 个跨域 spec，覆盖电路/物理/数学/几何/化学/CS/图表/表格/时间线/地图/概念/医学原图/失败关闭；
- 结果 **19/19 PASS**：`docs/evidence/figure_benchmark.json`；
- 修复：map 被误判 timeline；geometry 无 expression 时回退 elements；source-only 医学允许但解剖结构仍失败关闭；
- 修复 Matplotlib 中文标题缺字（PingFang/Arial Unicode 回退）；
- 全量 145 tests。


## 3D 场景（2026-11-10）

- `figure_compiler` 新增 `3d` 域：matplotlib-3d；
- 对象：box/sphere/line/arrow/label + camera；
- 不是物理求解器，是 3D 场景/刚体示意渲染；
- 图基准扩到 21 案例；全量 147 tests。


## P8 R2b（2026-11-10）：网表 ERC + 原图自动匹配

- 电路节点/支路网表增加 ERC：两端元件悬空即拒绝；
- source-only 支持 `artifact_id + page`，从 artifact figure_list 自动匹配原图和页码；
- 图基准 22/22；全量 149 tests。


## P8 R3b（2026-11-10）：语义契约基准

- `tools/figure_semantic_benchmark.py`：9 个案例，验 domain + labels + 尺寸 + 失败关闭；
- 结果 9/9；labels 收集补 date/title；
- 不是 VLM 视觉核对，语义真值仍需人工/VLM 抽检；
- 16 项 figure 单测；全量 150 tests。


## PDF 硬门禁（2026-11-10）

- `validate_pdf`：空白页、raw LaTeX、替换符、目录占位标题/重复标题；
- `build_project` 写 PDF 后强制过门禁；不过即拒绝交付；
- 习题 PDF 走浏览器+KaTeX，并在导出后过门禁；
- `/api/documents/{id}/pdf` 过门禁，坏 PDF 不再返回 200；
- 图裁剪 pad 30→48、trim pad 8→18，降低标签被切风险；
- 2 项 pdf gate 单测；全量 152 tests。


## P9 R2（2026-11-10）：3D 场景增强 + 原图裁剪

- 3D 新增 cylinder/plane/ground、box rotation、标签；
- source-only 自动裁空白边（pad 18，仅在内容占比 >40% 时裁）；
- 图基准仍 22/22、语义契约 9/9；figures 24 项；全量 156 tests。


## P9 R3（2026-11-10）：Agent 记忆/自修复

- agent_memories 表 + save/list/recall；LLM 规划注入最近 3 条记忆；
- 任务结束自动记录成功/失败轨迹；
- `/api/agent/memories` 可查；
- 自动修复预算 1→2，仅只读步骤；
- agent 24 项测试；全量 157 tests。

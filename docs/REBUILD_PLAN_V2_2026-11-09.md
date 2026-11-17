# TermFinale 彻底重构路线 V2（2026-11-09）

> 这版不是把 V1 计划排得更细，而是换一个更彻底的判断：
> **不在旧内容管线上继续打补丁，而是并行重建一个 v2 内核；旧 App 先保留可用，v2 跑通后再切换。**
>
> 验收标准仍是 `docs/ULTIMATE_FORM_LOCKED.md`；实测问题见 `docs/AUDIT_REPORT_2026-11-08.md`。
>
> **2026-11-09 进展**：v2 地基已跑通三份真实产物：`v2_ring_41/`（老师版 4.1，Gate 17/17，PDF 11 页）、`v2_ring_full/`（全章 50 页，Gate 1–50 全通过，PDF 28 页）、`v2_ring_41_gentle/`（详细版 4.1，17/17，PDF 14 页）。标头已改为课程在上、成稿从第一章/第一节开始、人设不写入讲义；阅读器已带搜索/编辑/导出 PDF/Word/HTML/打印 + `tfv2/api/reader_app.py` 本地 `/api/ask`。64 项 unittest 通过。已补 4.3 非苯芳烃、图片页逐页覆盖报告、答案审计、图源报告、2 张资料原图和真实分页；全章已改为温柔小姐姐语气+多段结语。已加讲义库/阅读器 UI、通用 `project.json` 构建 CLI、任意长度选中问 AI、检索引用/多轮对话/出题/改稿预览/撤销/7 天计划、PDF 摄入和符号清洗；医学 PDF 已用 `tfv2.build` 出 14 页试跑讲义；英文 PPT 已出中文讲解样章；旧 App 已加 `/v2` 讲义库入口；电路 PPTX 页账本/清洗通过。进度约 62%（见 `docs/PROGRESS_TO_ULTIMATE.md`）。旧 App 只加了入口、尚未真正迁移；学科复核/正式图片替换是下一步。

---

## 0. 为什么我改了路线

V1 的计划是“按现有模块逐步修”。重新看代码和实测结果后，我认为那样做会失败，原因不是工期，而是**架构方向错了**：

1. **旧管线把“模型输出的自由 Markdown”当源数据**，然后用正则/2-gram 事后猜结构、猜出处、猜答案。
   - `core/quality/constraints.py` 1127 行，仍在用 `### 考点：`、`P.`、正则题号做校验；
   - 提取 points 因为输出没有 `### 考点：`，0% 覆盖也能通过；
   - 试卷因为只查题数/分值/答案数量，错答案也能通过。
2. **旧代码耦合太深**：`server/app.py` 1566 行、`services/guide_service.py` 804 行、`review_service.py` 690 行，任务、校验、导出、进度、DB 混在一起。在旧模块里改一个门禁，很容易碰坏另一个任务。
3. **UI 建立在“假指标”上**：生成数当进度、资料存在率当覆盖率、0/0 当 100%。这不是 UI 问题，是数据契约错了；先改 UI 会返工。
4. **语言策略是“全文单语”**，和“源内容保留原语言、讲解用生成语言”冲突；这也不是换几句 prompt 能解决的。

**所以：不要“修旧管线”，要“重建内容内核”。**

但不是重写全部：

- 保留 Electron 壳、设计 token、上传/资料模型、部分解析能力、备份/Key/主题；
- 重写内容生成、任务管线、质量门禁、学习闭环、语言角色；
- 旧 App 继续可用，v2 用独立端口/独立测试数据目录跑，跑通再切。

---

## 1. 新路线的核心：把“生成”变成“内容编译器”

旧路线：

```
资料 → 一个大 prompt → Markdown → 正则校验 → 存 HTML
```

新路线：

```
资料 → 页账本 → 课程图谱 → 证据包 → 结构化章节 → 质量门禁 → 渲染 → 学习数据
```

### 1.1 三个不可妥协的设计

1. **结构化证据是源，Markdown/HTML 只是渲染结果。**
   - 模型不直接产出最终排版；
   - 每个 claim 必须带 `source_span_ids`/页码；
   - 渲染器负责标题、出处、公式、图片、章节顺序。
2. **生成和校验分离。**
   - 模型只负责“写”；
   - 页码、覆盖、老师必考、答案、语言角色、图片，由确定性代码检查；
   - 过不了门禁的 artifact 不能进入阅读器/DB 的“已交付”状态。
3. **任务级 schema，不是任务级 prompt。**
   - 讲义、提取、试卷、分析各有自己的数据模型；
   - 模型输出 JSON（或受控 block），不靠正则猜。

---

## 2. 目标架构

### 2.1 新包 `tfv2/`

```
tfv2/
  domain/        Pydantic 模型：Page, SourceSpan, Curriculum, ChapterDraft,
                 PointsDoc, NounsDoc, QuestionsDoc, Paper, AnswerAudit,
                 AnalysisDoc, QualityReport, LanguagePolicy
  ingest/        PDF/PPTX/DOCX/OCR；页账本；公式修复；内容 hash 缓存
  curriculum/    大纲、章节切分、标题清洗、老师约束；无有效大纲即失败
  authoring/     章节成文：证据包 → 段落/claim/例题/易错/小结
  extract/       points / nouns / questions 三条独立管线
  exam/          blueprint、题库、provenance、答案求解/校验、组卷
  analysis/      七件套：主线/层级/因果/题型/易混/顺序/出处
  quality/       按 artifact 的 gate；覆盖/出处/老师/答案/图片/语言/结构
  render/        Markdown/HTML/PDF/Word；正文不出现 P.x；章末出处
  learn/         练习、判分、错题、间隔复习、掌握度、计划
  agent/         无处不在的 AI：planner/executor/tools/memory/policy；问答/改写/出题/排复习
  jobs/          持久化任务、step、checkpoint、cancel、resume、retry
  llm/           模型客户端、prompt registry、结构化输出、成本/延迟账本
  storage/       SQLite repository、迁移、文件存储
  api/           FastAPI v2 路由；旧 API 兼容层
```

### 2.2 数据模型（先定 schema，再写 prompt）

| 表/模型 | 关键字段 |
|---|---|
| `source_pages` | material_id, page_no, text, quality, images, ocr_used, formula_damage, content_hash |
| `source_spans` | page_no, start/end, text, kind（定义/公式/题目/例题/图注） |
| `artifacts` | id, course_id, type, status（draft/validated/delivered）, schema_version, language_policy, quality_report_id |
| `artifact_blocks` | artifact_id, block_type（claim/example/pitfall/summary/question）, text, source_span_ids, page_refs |
| `lecture_specs` | artifact_id, header, toc, summary, closing, footer, layout_version, coverage |
| `lecture_blocks` | section_id, block_type（paragraph/formula/example/pitfall/figure）, text, source_span_ids, figure_id, doc_page |
| `questions` | stem, options, answer, analysis, provenance（source_question_id/page）, audit_status |
| `answer_audits` | question_id, method, independent_answer, agrees, confidence, reviewer |
| `agent_actions` | id, course_id, context, action, preview, status, undo |
| `jobs` | id, type, status, progress, checkpoint, error, result |
| `learner_*` | attempts, mistakes, mastery, review_schedule |

**规则**：

- `artifact.status = delivered` 才能被阅读器/学习闭环使用；
- `done` 不代表通过；`validated` 必须带 `QualityReport`；
- 任何 claim 没有 `source_span`，不能进 `delivered`。

### 2.3 任务流（可恢复）

```
Job:
  1. ingest        → PageLedger
  2. curriculum    → Outline
  3. authoring     → ChapterDraft[]（逐章）
  4. quality       → QualityReport（逐章 + 整篇）
  5. assemble      → Artifact
  6. final gate    → delivered / rejected
  7. render        → HTML/MD/PDF/Word
```

每一步：

- 输入/输出幂等；
- checkpoint 落 SQLite；
- 服务重启后 `recover()` 把 running 标记为 interrupted 并续跑；
- 失败保留位置/原因/重试次数，不丢已完成章节。

### 2.4 LLM 层

- **结构化输出**：JSON schema；解析失败→修复/重试，不靠正则。
- **prompt registry**：每个 prompt 有版本、输入 schema、golden cases；改 prompt 必须跑回归。
- **证据包**：一章只给该章页码 + 相关 quote；不把整本书塞进去。
- **两遍写作**：draft → 对照证据自检/修订；最终仍由确定性 gate 判定。
- **模型路由**：抽取/大纲用便宜模型，成文/答案审计用强模型；记录 token/成本/延迟。
- **语言角色**：prompt 明确“讲解用 {gen_lang}；原文/原题/术语保留 {source_lang}；翻译单独标记”；不再写“STRICT ENGLISH ONLY/纯正中文”。

---

## 3. 旧代码怎么处置

| 代码 | 处置 | 原因 |
|---|---|---|
| `desktop_shell/`、Electron 壳 | 保留 | 已可用；只改启动参数/端口 |
| `web/assets/app.css`、设计 token | 保留/复用 | 视觉基础可复用 |
| `core/paths.py`、`config.py`、`logger.py` | 保留 | 基础设施 |
| `core/parser.py` | 包一层/逐步替换 | 页账本可用，但公式/OCR/缓存要重做 |
| `core/database.py` | 迁移/扩展 | 保留用户数据；加 v2 表 |
| `server/app.py` | 拆成 `api/` routers | 现在任务/校验/导出/DB 混在一起 |
| `core/quality/constraints.py` | 拆成 `quality/gates/*` | 1127 行单体，规则互相污染 |
| `services/guide_service.py` | 重写为 `authoring/` pipeline | 大纲兜底/模板句/证据误杀都在这里 |
| `services/review_service.py` | 拆成 extract/exam/analysis 三条管线 | 现在共用一个入口，约束互相干扰 |
| `core/ai_engine.py` | 改 prompt registry | prompt 硬编码，无法版本化/评测 |
| `core/exam_engine.py` | 保留思路，重写答案审计 | 现在只查结构，不查答案对错 |
| `web/generate.html`、`reader.html` | 第二阶段重做 | 先有 v2 artifact JSON，再改 UI |
| `main.py`（1664 行） | 先确认是否被 launcher 使用；v2 不依赖 | 旧桌面入口，避免双维护 |
| `core/generate/card_guide.py` | 退役 | 卡片拼接不是目标形态 |
| `core/local_bridge.py` | 评估后退役/收窄 | 旧问答兼容层，避免和新 RAG 冲突 |

**原则**：不删用户数据；不一次性删旧代码；v2 通过 feature flag/独立端口接入，旧 App 可回滚。

---

## 4. 16–18 周路线（一个人 + 兼职学科 reviewer）

> 时间是工程估算；内容质量取决于 reviewer 和学生反馈，不是纯代码工期。

### Phase 0（第 1 周）：v2 骨架 + 标准 + 基线

- 建 `tfv2/` 骨架、Pydantic schema、SQLite 迁移、任务表。
- 建 golden set：文本 PDF、扫描 PDF、英文 PPT 各 1 份。
- 建测试：schema 单测、gate 单测、E2E 冒烟、内容 rubric。
- v2 跑在 8904，独立测试数据目录；旧 App 不受影响。
- 不写新功能；只搭“可验证的空壳”。

**验收**：v2 能启动、能建课程、能存/取 PageLedger；旧 App 仍可用。

### Phase 1（第 2–4 周）：内容编译器 v0

- `ingest`：页账本、内容 hash、公式质量、OCR 标记。
- `curriculum`：真实大纲；`fallback` 过滤资料头；无有效大纲即失败。
- `authoring`：一章一次；证据包 → 结构化段落/claim/例题/易错/小结。
- `lecture_spec`：标头（标题 + 用户情况）、教材式目录（含页码）、全篇摘要、正文、每小节出处、图片、结语、页脚、教材排版。
- `quality`：覆盖/出处/结构/老师/语言/页脚/图片 v0；单份资料 ≤150 页必须 ≥98%。
- `render`：Markdown/HTML/PDF/Word；正文不出现 P.x；每小节末尾“出处：第 X–Y 页”；页脚一行小字；不要大卡片。
- **交付：环烃 1 章样章**（自然成文、例题、易错、小结、分节出处、干净图、结语、页脚），人工评分 ≥4/5。

**验收**：不再出现 677 字模板；不再两章同名；学生能读完并做课后题；标头/目录/摘要/分节出处/图片/结语/页脚齐全。

### Phase 2（第 5–7 周）：四类任务

- 提取：points/nouns/questions 三 schema；每条必须有页码；原题逐字；含/不含答案。
- 试卷：blueprint + provenance + 答案审计（数值/选项唯一性/量纲）+ 组卷。
- 分析：七件套 schema；空结果 fail；因果链可回溯。
- **交付：四类任务各 1 份真实样例，全部过 locked 门禁。**

**验收**：points 0% 覆盖不能通过；mock 错答案不能通过；original/variant 有 provenance；分析不再空结果。

### Phase 3（第 8–9 周）：阅读器 + 学习闭环

- Reader v2 直接吃 artifact JSON：TOC、搜索、选中提问、笔记、错题、导出。
- 标头：标题 + 用户情况（目标/天数/基础/资料数/覆盖）；人设只影响生成语气、不写入标头；移除开发者/随机祝福/源文件名。
- 练习支持选择/填空/计算/综合；判分走答案审计；错题带答案/解析/页码。
- 掌握度按知识点/章节；复习计划按剩余天数/目标分排期。
- **AI 无处不在 v0**：每个页面有 AI 入口；上下文 = 课程/页/选中/笔记/错题；能问答、解释、出题、改这一节、排复习；写操作预览/撤销。
- **验收**：练习→错题→复习→掌握度全链路跑通；进度真实；AI 动作可追溯、可撤销。

### Phase 4（第 10–11 周）：语言 + UI + 设置

- UI 语言完整字典；UI 语言/生成语言/试卷语言分离。
- 四角色语言：源内容保留、讲解用生成语言、译文标记。
- 空/错/加载、窄窗口、长公式、键盘/对比度、死按钮。
- AI 入口/动作/权限/错误态/撤销；自由对话与“只改这一节”的预览。
- 备份/恢复 UI；输出目录统一；设置页隐藏绝对路径/Key 尾号。
- **验收**：英语界面除源内容外 0 中文残留；0 死按钮；恢复可用；AI 不静默改数据。

### Phase 5（第 12–13 周）：可靠性

- Job 落库 + checkpoint + resume + crash recovery。
- 输出命名带秒/任务 id；不覆盖；统一 outputs。
- 1000 页长文档；并发/限流/成本账本。
- 旧数据迁移：缺失文件标“需重生成”，不写“已保存”。
- **验收**：kill 服务后能续；1000 页完成；无数据丢失。

### Phase 6（第 14–16 周）：评测与发布

- golden set 四类任务 + 人工评分 + 与直接问顶级 AI 对比。
- 盲测 10 名学生；学习效果/可做题率/耗时/成本。
- Mac 签名/公证；Windows 实体机；官网；GitHub；10 人内测。
- **验收**：内容/UI/数据/答案/安装包全过才发布。

---

## 5. 前 10 天（如果现在开始）

| 天 | 做什么 | 产出 |
|---|---|---|
| D1 | 冻结新功能；建 `tfv2/` 骨架；golden set 清单 | v2 空壳 + 3 份资料 |
| D2 | schema：Page/SourceSpan/ChapterDraft/QualityReport；SQLite 迁移 | 可验证的数据契约 |
| D3 | ingest 页账本 + 内容 hash + 质量标记 | 35 页 PageLedger |
| D4 | curriculum：真实大纲 + fallback 过滤 + 失败策略 | 环烃/高数正确大纲 |
| D5 | evidence packet + authoring schema | 一章的输入/输出 |
| D6 | authoring 一章：自然成文 + 例题 + 易错 + 小结 | 环烃 1 章草稿 |
| D7 | quality gate：覆盖/出处/结构/老师/语言 | QualityReport |
| D8 | renderer：正文/章末出处/公式/图片 | HTML/MD 样章 |
| D9 | 人工评审 + 修订 | 评分 ≥4/5 |
| D10 | 对比旧输出；决定是否扩章 | go/no-go 记录 |

**D10 之前不扩全章、不做 UI 重写、不接新功能。**

---

## 6. 验收门禁（v2 必须带报告）

- **Artifact**：`delivered` 才能进阅读器；`draft/validated/rejected` 分开。
- **Coverage**：单份资料 ≤150 页 ≥98%，缺失页列出；>150 页概览。
- **Citation**：每个 claim 有 source span/page；每小节有出处；原题 100% 原样。
- **Teacher**：必考 100% 覆盖；不考 0 命中。
- **Answer**：独立审计；错答案 0；选项唯一；答案在选项内；量纲/边界。
- **Image**：图源/使用/丢弃报告；0 PPT 截图/色块/logo；图注/来源页。
- **Language**：UI 干净；源内容保留；译文标记；生成语言一致。
- **Structure**：标头/目录/摘要/正文/结语/页脚齐全；0 空章/重复章/只有标题；0 重复题/空题。
- **AI**：每个页面有入口；动作可追溯、可撤销；不静默改数据；回答带出处。
- **System**：job resume；输出不覆盖；1000 页。
- **Release**：签名/公证/Windows/官网/内测/盲测。

**任何一条不过，状态不能是 delivered。**

---

## 7. 我需要你提供的

1. **允许我读你电脑里的课程资料**：先选 1–2 门做样章；可以自己设“重点/不考”做测试，不伪造“老师说”。
2. **3–5 个真实学生**：你来找；愿意读样章、做题、给反馈。
3. **学科 reviewer**：至少数学/化学各 1 位，帮我们判断答案/概念对错；没有 reviewer 时，v2 只能交付“需人工复核”的题。
4. **API 预算**：你已确认不设上限；我仍会记成本账本，先小规模跑。
5. **发布资源**：Apple 开发者账号、Windows 机器、内测名单（后期）。

没有 1/2/3，我能把系统做出来，但不能保证“内容真的对学生有用”。

---

## 8. 这版路线和 V1 的区别

| 维度 | V1 | V2 |
|---|---|---|
| 改造方式 | 在旧模块上逐步修 | 并行重建 v2 内核，旧壳兼容 |
| 源数据 | 自由 Markdown + 事后正则 | 结构化证据/claim + 渲染 |
| 任务 | 一个 review_service 共用 | 四条独立管线 + schema |
| 质量 | constraints.py 单体 | 按 artifact 的 gate + QualityReport |
| 语言 | prompt 强制单语 | 四角色语言策略 |
| 任务状态 | 内存 JOBS | SQLite job + checkpoint + resume |
| UI | 先改 UI | 先有 artifact，再改 UI |
| 风险 | 改一处坏三处 | 旧 App 可回滚，v2 可对比 |

---

## 9. 一句话

> **不要试图把“自由生成的 Markdown”验成真的；要让“真的证据”生成 Markdown。**
>
> 先并行造一个可验证的 v2 内容编译器，用环烃 1 章证明它；再复制到四类任务；最后才换 UI、接学习闭环、发布。

> 2026-11-09 全量压力测试：85 页电路 PPTX 结构 85/85、PDF 16 页、AI/练习/导出通过；但语义 covered 38/85、partial 37、missing 8、105 个缺失点、0 图。详见 `docs/evidence/v2_circuit_full/TEST_REPORT.md`。

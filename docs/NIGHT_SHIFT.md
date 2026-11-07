# TermFinale 夜间工作日志（2026-11-07 夜 → 2026-11-08 早）

> 目标：先保命，再内容可信，最后 UI。今晚不推送 GitHub、不重置数据、不删原资料。
> 早上交付：完成项 + 证据 + 未完成项 + 截图。

## 状态总览

| 项 | 状态 | 证据 |
|---|---|---|
| DB 备份 | ✅ | `~/Library/Application Support/TermFinale/backups/night_20261107_234346.db`（98KB，47 课/368 生成物可读） |
| 本地基线提交 | ✅ | `ccc9e2d baseline: 保存当前工作区...`（未推送） |
| 测试数据隔离 | ✅ | `is_test` 迁移完成：46 测试 / 1 正式；API 默认过滤 |
| 本地 API 鉴权/备份/reset | ◐ | 备份 API、reset 保护、exam_date 防御已完成；token/CORS 待做 |
| 日志 | ✅ | `server/app.py` 启动即 setup_logging（新进程生效） |
| 85 页 OCR | ✅ | 85/85 页、按页码排序；第 74 页标记“OCR 未识别” |
| PDF 空页 | ✅ | 3 页合成 PDF → 3 条（空页占位） |
| 公式 `<`/`&` | ✅ | 合成 HTML 渲染 4 个 KaTeX 节点、0 残余 `$` |
| 页码校验【】文件名 | ✅ | `source_pages("【《有机化学【蜂考系统课】.pdf》第 5 页】") == {5}` |
| 覆盖率按页 | ✅ | 10 页只引用 6 页 → coverage 0.6、missing [7,8,9,10]（回归测试） |
| 幽灵页 | ✅ | 资料前缀不再算独立页；split_pages 回归测试 |
| 长文档 10k 截断 | ✅ | 删除无条件 10k；analysis/exam 全书均匀节选 |
| 1001 页大纲 | ✅ | 10 章、覆盖 1001 页、101 页/章；不再造 170 个“补充”章 |
| >150 页概览 | ✅ | 160 页 PPT：2 章 2 次调用、每章 4 页抽样、validation ok |
| 老师重点 | ✅ | 只考/必考/不考/页码/基团歧义解析；考点级硬校验；13 项单测 |
| 真实高数验收 | ✅ | 8 页提取、33.7s、8/8 页引用、0 超范围考点 |
| 试卷容错 | ✅ | answer_mode=forbidden、答案标题后缀、额外标题只 warn |
| 图片串名/缓存投毒 | ✅ | 图片名加资料哈希前缀；空图注不再写缓存 |
| UI | ☐ | 明早开始（按用户的“先算法后 UI”要求） |

## 关键证据

### 85 页 PPT
```
PPT 图片页回填：7 页成功 / 1 页失败（共缺 8 页）
pages: 85  missing: []  sorted: True
p74: [本页 OCR 未识别出文字]
```

### 公式
```
katex nodes: 4   raw $ left: 0
v_2<v_1 → <annotation>v_2&lt;v_1</annotation>
```

### 长文档
```
1001 pages → chapters: 10 covered: 1001 sizes: [101×9, 92]
160-page PPT overview → calls: 2, page headers per call: [4,4], validation ok: True
```

### 老师重点真实验收（FINAL高数，1–8 页）
```
teacher_rules.only_topics = ["隐函数求导","高阶导数间接法","参数方程二阶导","变化率实际问题"]
coverage = 8 页 / 8 引用 / 1.0
validation.ok = True
topics 全部落在白名单内
```

## 本轮改动文件

- `core/database.py`：is_test 字段 + 迁移提交修复 + `looks_like_test_course`
- `server/app.py`：日志、token 待办、is_test 过滤、exam_date 防御、备份 API、reset 保护、公式渲染转义
- `core/parser.py`：`ext` 遮蔽修复、LibreOffice 查找、OCR 重试/占位、排序、PDF 空页/混合 OCR、PARSER_VERSION、图片前缀
- `core/parsing/figures.py`：图片文件名加资料前缀
- `core/ai_vision.py`：失败不再返回“原题配图”
- `core/exporter.py`：数学块 HTML 转义
- `services/review_service.py`：PAGE_SPLIT/幽灵页、按页覆盖率、老师规则解析
- `services/guide_service.py`：>150 页概览模式、老师规则、页标签截断
- `core/generate/outline.py`：全书均匀摘要、均衡分章、去“补充”章
- `core/generate/outline_store.py`：缓存指纹加范围/模式
- `core/quality/teacher_note.py`：新增
- `core/quality/constraints.py`：考点级规则、答案模式、试卷容错
- `core/exam_engine.py`：去掉 10k 截断、全书节选、题型均匀取样
- 测试：81 项全绿（新增 teacher_note、coverage、split_pages、exam tolerance）

## 明天待办

- [ ] API token + CORS 白名单（P0 安全）
- [ ] 171 页真实提取/账本验收
- [ ] 化学 10 基团真实验收
- [ ] 试卷答案逐题自洽（更严格）
- [ ] 图片语义/纯色占位生成后校验
- [ ] UI：深色高级 SaaS 方向重构（首页/阅读/复习计划/课程详情/练习）
- [ ] CI 全量 6 模块 + 新测试
- [ ] 更新 README/已知限制/AGENTS 交接

## UI 第一版（00:03–00:10）

- 新增 `web/assets/premium.css`：深色近黑画布、薄荷强调、衬线标题、等宽标签、卡片边界、响应式。
- 重写 `web/dashboard.html`：今日主卡 + 3 指标 + 最近生成 + 我的课程；修掉 `recentGrid` 空指针、假 demo 卡、旧导航。
- 重写 `web/review_plan.html`：今日目标卡（到期错题/预计用时/进度）+ 按课程 + 下一步。
- 全站接入 premium.css + 深色默认；修正 `app.css` 的 `data-accent` 把主色覆盖成深灰的问题。
- 阅读页：封面收窄、正文优先、TOC 无 h2 时用 h3 兜底、工具按钮缩小。
- 截图：`/tmp/tf_verify/ui2/dash4.png`、`plan2.png`、`reader2.png`。
- 待办：courses/practice/generate/settings 页面重写；阅读页工具折叠；移动端/浅色回归。

## 生成工作台 + 任务约束（00:10–00:14）

- `generate.html` 新增“老师重点 / 补充要求”+ 任务约束：页码范围、禁止词、违规即失败、试卷答案开关。
- 请求体带 `options.constraints`；后端 `TaskConstraints` 已支持。
- 修复审计问题：套数写死、题型合计校验在 showRunning 之后、SSE 无错误态、materialMode 隐藏。
- 完成态显示 `validation` 的硬违规/提示。
- 截图：`/tmp/tf_verify/ui2/generate2.png`。

## 课程页（00:14–00:16）

- `courses.html` 卡片改为 premium：状态、课程名、天数/资料/生成、进度、资料/生成/打开。
- 空态/骨架沿用 premium；保留新建/编辑/删除/生成物弹窗。
- 截图：`/tmp/tf_verify/ui2/courses2.png`。
- 待办：practice / settings / reader 工具栏 / 浅色回归 / 移动端。

## 设置 / 练习（00:16–00:20）

- `settings.html`：修复死的“清除全部数据”脚本；新增“备份与恢复”（立即备份/最近备份）；reset 先备份、只删上传副本、要求 confirm；数据目录显示。
- `practice.html`：指标条 + 错题本优先 + 训练卷网格；判分错误态/防连点；删除 `quizCourse=7` 兜底。
- 截图：`/tmp/tf_verify/ui2/settings2.png`、`practice2.png`。

## 阅读页工具折叠 + 浅色/窄窗（00:20–00:24）

- 阅读页工具收进“⋯”：默认只留“搜索”；编辑/Word/PDF/打印/主题展开后出现。
- 浅色主题验证（`?theme=light`）：象牙底 + 深绿主色，可用。
- 1024 宽度：hero 右侧改为横向信息条，环与文字不再挤压。
- 截图：`reader3.png`、`dash_light2.png`、`dash_1024b.png`。

## 应用后端切换（00:10）

- 原 8903 旧进程已停止，用新代码重启；`/api/courses` 返回 1 门真实课（全量 47），测试课程默认隐藏。
- 测试用 8904 已停止；最终截图走 8903：`final_dashboard.png`、`final_generate.png`、`final_reader.png`。
- Electron 已开窗口需 **Cmd+R 刷新一次**才能加载新 UI；后端已是新代码。

## 课程详情 / 资料 / 笔记（00:24–00:33）

- `course_detail.html` 重写：course hero + 6 项统计 + 资料卡 + 生成物卡；修复 `Files 1` 文案、日期、重复返回。
- `materials_stats.html` 重写：3 指标 + 按课程分组 + 缺失标记。
- `notes.html` 重写：指标 + 笔记卡（展开/删除/字数）+ 空态。
- `upload.html` 已随 premium 主题统一（未重写）。
- 截图：`course_detail_v2.png`、`materials_stats_v2.png`、`notes_v2.png`、`upload_v2.png`。

## API 鉴权 + CORS 白名单（00:33–00:38）

- 页面首次加载下发 HttpOnly SameSite=Strict `tf_token`；`/api/*`（health 除外）校验。
- CORS 只允许 `http://127.0.0.1:<port>` / `http://localhost:<port>`；跨站 Origin 直接 403。
- 实测：无 cookie `/api/courses` → 403；加载 dashboard 后带 cookie → 200（1 门课）；`Origin: evil` → 403。
- 新测试 `tests/test_security.py` 4 项；全套 **85 项**通过。
- 注意：Electron 已开窗口需 **Cmd+R** 刷新一次以拿到 cookie。

## 试卷答案自洽 + CI（00:38–00:42）

- 答案覆盖 <80% 判硬失败；题号后为空判失败；答案重复题号仍为提示。
- 新增 2 项答案自洽测试；全套 **87 项**通过。
- CI 改为 `unittest discover` 全量；pyflakes 覆盖 `server/app.py`、`desktop.py`、`tools/build.py`；新增 server import smoke。

## 900 窄窗导航 + 移动 tab（00:42–00:46）

- premium.css 在 900 以下补 `.mobile-tab`；app.js 全局注入移动 tab（reader 已有则跳过）。
- dashboard 内联移动 tab；900px 截图确认可切页。
- 截图：`dash_900b.png`。

## 真实试卷验卷（00:46–00:55）

- 真实调用 FINAL高数（8 页，题型 4/2/2=100 分，只考 4 个考点）：**1 次通过**，15.7s。
- 结果：9 题区识别为 8 题、8 个答案、1 个答案分区；`validation.ok=True`，无 warning；`only_topics` 4 个全部命中。
- 发现并修掉一个真 bug：模型在单题型里又输出“答案 + 第二套题”，旧验卷只 split 第一个答案分区，把后续题目算成答案而**误判通过**。
  - `_clean_section_output`：单题型只保留请求题型、切掉答案；
  - `_clean_answer_output`：只保留第一段答案、切掉第二套题；
  - `_check_answer_mode`：多个答案分区/答案后混入题目 → 硬失败；
  - `_stems`：不再把试卷标题当题干；题数统计只看题目区。
- 真实证据：`/tmp/tf_verify/exam_real2.md`、`exam_real2.log`。
- 测试增至 **93 项**全绿（新增 exam cleanup 5 项、多答案分区 1 项）。

## README / 版本 / 浅色回归（00:55–01:00）

- README 三张预览图替换为夜间新 UI：今日工作台 / 阅读器 / 生成工作台。
- `build_info.VERSION` 0.2.0 → 0.3.0，构建时间 2026-11-08 01:00。
- 浅色复习计划截图：象牙底 + 深绿主色，可用；`plan_light.png`。
- 首次启动欢迎页在空 profile 下截图：`welcome2.png`，分屏编辑感，保留。

## 171 页真实提取（01:00–01:10）

- 真实 171 页《有机化学【蜂考系统课】》全量提取：**6.6 分钟 / 40 块 / 42 次块尝试 / 140,259 字 / 210 个考点**。
- 覆盖率诚实结果：**156/171 页被引用 = 91.2%**；缺页 `[1,2,26,34,36,49,121,136,139,144,155,158,159,164,167]`（1、2 为封面/群号，26 为纯图页，其余多为练习题/答案页）。
- 最终校验原有 3 个考点缺出处 → 硬失败；新增 `repair_topic_citations` 用考点标题与原文页 2-gram 匹配补回真实页码，**3 条全部修复，validation.ok=True**；匹配不到不编页码。
- 生成页完成态新增“逐页覆盖 91% · 未引用 N 页：页号…”（黄色警示），不再只报字数。
- 证据：`/tmp/tf_verify/extract171.md`、`extract171_repaired.md`、`extract171b.log`；测试 95 项全绿。

## 最终交付包（01:10）

- 新增 `docs/MORNING_REPORT.md`：可验证成果、证据、未完成项、早上验收命令、GitHub 建议。
- 证据固化到 `docs/evidence/`（真实试卷 md/log、171 修复稿/log）；截图固化到 `docs/screenshots/`。

## 171 缺页补提取（01:10–01:15）

- 逐页补提取 13 个内容页（26/34/36/49/121/136/139/144/155/158/159/164/167）：**169/171 = 98.8%**，仅缺 1、2 封面/群号；`validation.ok=True`。
- 已写进 `_run_extract`：块级补跑后仍缺的、长度 ≥80 的页，单页再补（最多 16 页）；补不出来继续报缺页。
- 证据：`docs/evidence/extract171_filled.md`、`fill171.log`；测试 95 项仍全绿。

## 1001 页真实概览（01:15–01:25）

- 真实 1001 页《数学分析讲义》概览：7 章 / 抽样 33 页 / **35.9s** / 15,725 字 / `qa_ok=true`；不是逐页提取。
- 修复误报：概览模式的 coverage 原会显示 33/1001=3.3%，UI 会像“缺 968 页”；现在 `coverage_mode=overview_sample` + `sampled_pages`，生成页显示“长文档概览：7 章 · 抽样 33/1001 页（不是逐页覆盖）”。
- 证据：`docs/evidence/guide1001.md`、`guide1001.log`；测试 97 项。

## 收尾 UI 小修（01:25–01:30）

- 设置页头像改为“更换头像”按钮（隐藏原生 file input）；版本显示 0.3.0 / 2026-11-08 01:00。
- 练习页无错题时不再显示 “0 / 0”，改为 “0”。
- 截图：`docs/screenshots/settings.png`（旧版）；`/tmp/tf_verify/ui2/settings3.png` 最新。

## API 端到端 + 只考过滤（01:35–01:45）

- 临时库 + 8906 服务，带 cookie 完整走 `/api/jobs` + 轮询：4 页提取 **4/4 覆盖 / 22.1s / validation.ok=True**，质量检查全过。
- 抓出并修掉两个真实缺陷：
  1. 模型把“第2页内容说明 / 第2.2节考点范围说明”当考点 → `clean_extract_topics` 清掉元信息块；
  2. 模型把“反函数导数/复合函数求导”写进只考范围 → `filter_out_of_scope_topics` 用字符子序列匹配白名单过滤（“隐函数求导”⊂“隐函数求导法”，但不⊂“复合函数求导”），不再整份硬失败。
- 生成页显示“按老师只考过滤 N 条”；覆盖率指标新增 `scope_filtered`。
- 测试 **100 项**全绿；证据 `docs/evidence/api_e2e.log`。
- 测试产出写到桌面的 `FINAL高数_资料提取_1108_0042.html` 已清理（只删测试产物）。

## 备份恢复工具（01:45–01:55）

- 新增 `tools/restore_backup.py`：完整性/表校验 → 默认 dry-run → `--yes` 前用 SQLite backup API 另存当前库 → 清旧 WAL/SHM → 原子替换；不删上传副本/原资料。
- 真实备份（47 课/47 资料/368 生成物）在 `/tmp` 恢复验证通过；新增 5 项测试，测试总数 **105**。
- 恢复日志：`docs/evidence/restore_test.log`。

## 本地 CI 门禁（01:55–02:00）

- `compileall` 全通过；`pyflakes` 覆盖 main/launcher/desktop/server/services/core/models/tools 全净（清掉 parser 一个未使用变量）。
- 测试 105 项全绿。

## 上传页终版（02:00–02:10）

- `upload.html` 重写：大拖拽区/格式 chips/上传队列/进度条/失败态/500MB 校验/已有资料列表/空课程态；文件名转义。
- 截图：`/tmp/tf_verify/ui2/upload3.png`，固化 `docs/screenshots/upload.png`。
- 测试仍 105 项全绿。

## 阅读器浅色回归（02:10）

- reader 支持 `?theme=light`（之前只读 localStorage）；浅色正文/侧栏/工具均正常，截图 `reader_light.png` 固化 `docs/screenshots/reader-light.png`。

## 欢迎页窄窗（02:15）

- 欢迎页补 900px 上下分栏；空 profile 临时库截图 `welcome_900.png`，固化 `docs/screenshots/welcome-900.png`。分屏左栏在窄窗不再横向挤压。

## 1001 章名可用性（02:15–02:25）

- 真实 1001 页概览重跑：8 章 / 抽样 50 页 / 43.5s / 18,676 字 / qa ok。
- 发现大纲章名被正文句子污染；加 `clean_outline_titles` 使用点兜底 + `_retitle_first_heading` 覆盖每章首个 `##`；不可读标题退成“第N部分 · 第X–Y页”。
- 证据更新：`docs/evidence/guide1001.md` / `guide1001.log`；测试 109 项。

## 会话 token 持久化（02:25–02:35）

- 修复“后端重启后旧 cookie 全失效、必须手动刷新”：token 写入数据目录 `.session_token`（0600），启动优先复用。
- 实测：拿 cookie → 重启 8903 → **同一 cookie 仍 200**；无 cookie 仍 403；文件权限 `-rw-------`。
- 测试 110 项全绿。

## 上传→解析→生成真实链路（02:35–02:45）

- 临时库真实 multipart 上传 2 页 PDF → 解析 2/2 → 提取 15 个考点 → 2/2 覆盖 / 32.3s / `validation.ok=True` / 质量检查全过。
- 同时验证上传 API、cookie、任务轮询、解析器、覆盖账本；证据 `docs/evidence/upload_e2e.log`。
- 测试 110 项全绿。

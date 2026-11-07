# TermFinale v1.0 发布路线图

> 配套审计：[AUDIT_2026-11-07.md](AUDIT_2026-11-07.md)
> 原则：先保命，再可信，再好看，再发布；每一道门都要有可复现证据，不靠感觉。
> 说明：软件不存在“零 bug”。本文的“可发布”= P0 清零、发布范围内 P1 清零、P2 有记录、所有门有证据、可回滚。

---

## 0. 发布定义（四根柱子）

| 柱子 | 可发布标准 | 证据形式 |
|---|---|---|
| 内容可信 | ≤150 页覆盖 ≥98% 且缺页逐页列出；>150 页章节概览边界清晰；1001 页在预算内可跑；0 裸 LaTeX/0 KaTeX 错误；图片 0 错配；老师规则 0 违规 | 逐页 ledger、生成物、校验 JSON、评测报告 |
| 学习工作流 | 首页 3 秒知道今天做什么；读完→做题→错题→复习闭环可走通；无死按钮/假功能 | 录屏、e2e 脚本、按钮审计表 |
| 可发布产品 | Mac 签名+公证、Windows 安装包+实机冒烟、自动更新、崩溃日志、备份恢复、隐私/协议、AGPL 合规 | codesign/spctl/stapler、安装包、日志、备份还原演练 |
| 可证明 | 固定评测集 + 与“直接问 AI”的双臂对照 + 门槛入 CI | 评测报告、CI 失败演示 |

**发布门 = 以上四根柱子全部通过 + P0=0 + 发布范围 P1=0。**

---

## 1. 总览与顺序

```
Week 0     Phase 0 保命与基线（72h）
Week 1-3   Phase 1 内容可信（主线）
Week 1-3   Phase 3 发布工程（并行，等账号/机器）
Week 3-5   Phase 2 UI/UX 重构
Week 3-5   Phase 4 评测集与回归（并行）
Week 5-6   Phase 5 内测（10 人）+ 修
Week 7     v1.0 发布 + 官网 + GitHub Release
```

为什么这个顺序：
1. 现在代码有 102 个提交未推、13 个未跟踪但被 import 的文件、DB 无备份——任何“先做功能”都可能白做或丢数据。
2. 内容可信是产品唯一壁垒，UI 美化不能盖住“覆盖率是假的”。
3. 签名/公证/Windows 有外部依赖（账号、机器），必须最早启动、并行等待。
4. UI 放在内容之后，避免为错误内容做漂亮界面。
5. 内测前必须有评测集，否则无法判断“改好了没有”。

---

## 2. Phase 0：保命与基线（72 小时）

### 2.1 代码与版本
- [ ] `git add` 全部未跟踪依赖：`core/quality/constraints.py`、`gate.py`、`core/material_kind.py`、`core/lang_convert.py`、4 个 web 页面、2 个测试模块、`HANDOFF.md`、`docs/AUDIT_*.md`；确认 `node_modules`/`.venv`/`dist`/`build` 不入库。
- [ ] 本地 commit；跑全量测试；推 `release/0.1` 分支（不直接 main）。
- [ ] 打 tag `v0.1.0-baseline`；Release 上传可启动 zip。
- [ ] CI 跑全 6 个测试模块 + `pyflakes server/app.py desktop.py tools/build.py`；故意改坏一条断言验证 CI 会红。
- [ ] 单一版本源（`VERSION` 或 pyproject）；`build_info.py` 生成到 `build/` 并 gitignore；发布前 clean tree。

### 2.2 数据安全
- [ ] `PRAGMA wal_checkpoint(TRUNCATE)`；退出/定时 checkpoint。
- [ ] `POST /api/backup` → `data_dir/backups/`（sqlite backup API，轮转保留 N 份）。
- [ ] `POST /api/restore`：先自动备份当前库，再恢复；版本校验。
- [ ] `migrate_legacy` 改用 sqlite backup，处理 -wal/-shm。
- [ ] `/api/reset`：只删 `data_dir/uploads` 与 `outputs`；强制先备份；要求 `{"confirm":"DELETE-ALL"}`；不删用户桌面原文件。
- [ ] 备份演练：备份文件单独 `sqlite3` 打开能读到全部课程；`kill -9` 后重启数据仍在；恢复后课程/生成物完整。
- [ ] `exam_date` 写入校验 + 读侧防御。

### 2.3 安全
- [ ] 启动生成一次性 token；中间件校验所有 `/api/*`（`/api/health` 除外）。
- [ ] CORS 白名单只允许自身 origin；拒绝非本机 Origin。
- [ ] 前端所有 fetch 带 token（Electron/浏览器注入）。
- [ ] 验证：`Origin: https://evil` 预检失败；无 token `POST /api/reset` → 401；正常 UI 不受影响。
- [ ] 上传大小/类型/路径校验；课程名输出文件名 sanitize。

### 2.4 数据隔离
- [ ] `courses` 加 `is_test`（迁移，默认按已知前缀回填）；生成物/错题/笔记可继承。
- [ ] `/api/courses`、`/overview`、`/practice`、`/mistakes`、统计默认过滤；`?include_test=1` 才显示。
- [ ] 设置页开关“显示测试数据”；归档不删。
- [ ] 验证：首页/复习/练习截图无 BATCH/TEST；真实课数正确。

### 2.5 可观测性
- [ ] `server/app.py` 启动即 `setup_logging()` + 异常钩子；日志落 `data_dir/logs`，轮转。
- [ ] job 失败落 `debug/<job>/`：prompt、model、页范围、原始输出、异常栈。
- [ ] 设置页“导出诊断包”（日志+版本+系统信息，脱敏）。
- [ ] `python-multipart` 进 requirements；Key 保存 `chmod 600`。
- [ ] 验证：故意让 job 抛异常，`logs/app_*.log` 有完整栈。

### Phase 0 门
clean checkout 能启动；备份可恢复；无 token 危险接口 403；首页无测试数据；日志有文件；CI 全绿。

---

## 3. Phase 1：内容可信（2-3 周）

### 3.1 逐页账本（先修“假覆盖率”）
- [ ] 解析层返回 `(pages, total_pages)`：PDF 用 `len(fitz.open)`，PPTX 用 `len(prs.slides)`，其它用实际页数。
- [ ] 每页 ledger：`{n, status: parsed|ocr|empty|failed, reason, cited, chunk}`。
- [ ] 覆盖率 = `cited ∩ ledger / total_pages`；≤150 页 <98% 判失败并逐页列出缺页。
- [ ] UI 展示：每页状态、缺页列表、重跑按钮；不再展示“块覆盖率”冒充页覆盖率。
- [ ] 验证：171 页 PDF 的 ledger 分母=171；85 页 PPT 分母=85。

### 3.2 解析与 OCR
- [ ] `parser.py:409` `ext` 改名 `img_ext`；`_fill_missing_ppt_pages` 必定执行。
- [ ] 回填后按页码排序；OCR 失败重试 1 次/换模型；失败页写占位并计入 ledger。
- [ ] 缓存 key 加解析器版本（`v4` + 代码哈希）；旧缓存自动失效。
- [ ] PDF 按页判定（该页文字 <8 字 → OCR），不再只判整本 <50 字。
- [ ] PPTX 递归处理 Group/OLE；满版图单独 OCR；空页写 `[本页无可提取文字]` 占位。
- [ ] OCR/图注显式 `timeout=60~120`；视觉 Key 缺失预检并报错，不静默少页。
- [ ] 图注缓存：失败不写；key 加模型/提示词版本；提供清缓存入口。
- [ ] 验证：85 页 ≥84/85（第 74 页单独标注）；171 页 ledger 完整；断网/缺 Key 有明确错误。

### 3.3 长文档
- [ ] 删除 `call_ai_with_retry` 无条件 10k 截断；改为调用方显式分块。
- [ ] analysis/exam/chapter：map-reduce（页/章摘要→汇总→回填），不再整本塞。
- [ ] guide 大纲：>150 页走“目录/标题/抽样页 → 章级概览”；不再生成“补充：N–N 页”。
- [ ] 1001 页：章数上限 + 预算上限（调用次数/时长）+ 未覆盖页清单；超限明确失败或降级，不静默。
- [ ] 双资料 15 页上限改为“权重配额 + 明示覆盖范围”。
- [ ] 验证：1001 页 analysis 命中后 900 页关键词；guide 章节标题可读；调用次数在预算内。

### 3.4 公式与图片
- [ ] 统一渲染预处理：`\(\)/\[\]`→`$`；数学块 HTML 转义 `& < >`；导出/reader/PDF 共用。
- [ ] `syntax_issues` 加“正文裸 LaTeX 命令”硬检查；生成后自动修复或重试。
- [ ] 图片文件名加资料哈希前缀（`fig_<filehash>_pNN_n.png`）；整页图兜底保留；缺图输出占位并计数。
- [ ] 图注与内容语义校验按 `(file,page)` 键；生成后纯色/空白图检测。
- [ ] Mermaid 本地打包或静态渲染；普通代码块不再被当 mermaid。
- [ ] 验证：公式语料（含 `<`、`&`、分段函数、矩阵）0 KaTeX 错误；两份 PDF 同页图不串；断网导出正常。

### 3.5 老师重点（核心差异化）
- [ ] 新增 `core/quality/teacher_note.py`：解析“第 5 页例 3 必考 / 隐函数求导必考 / 参数方程不考 / 只考 A、B、C”。
- [ ] 歧义消解：note 说“基团”但没列全 → 去原文定位列表；解析失败标“存疑”，不反问。
- [ ] `TaskConstraints` 扩展：`must_topics`、`ban_topics`、`only_topics`、`literal_ban_tokens`、`page_refs`。
- [ ] 校验粒度：考点/章节标题/试卷【考点】标签命中即失败；正文顺带提及只提示；违规带行号+命中词。
- [ ] 提示词注入 + 重试 2 次 + 失败列违规位置、不交付。
- [ ] 验证：高数“只考 4 类”0 超范围；化学 10 基团 0 命中；导数定义里的“极限”不误杀。

### 3.6 试卷
- [ ] 原卷结构识别：题型/题量/分值（从上传试卷解析）；无原卷时用蓝图。
- [ ] 生成与校验共用 blueprint；`strict_counts` 只对用户明确结构生效。
- [ ] `answer_mode=forbidden` 时 `validate_paper` 不要求答案分区；`# 答案与解析（详解）` 可识别。
- [ ] 额外 `##`（考试说明/草稿纸）只 warn，不硬失败；题型白名单只校验已知题型。
- [ ] 答案自洽：每题恰好一个答案；选择题 A-D；填空非空；重复/矛盾检测；覆盖 ≥95%。
- [ ] 改数题：题干相似度 + 数字变更校验；变式题必须标“改编自第 X 页/原题 X”。
- [ ] 验证：三份期末卷逐题核对；故意改错答案能被抓；结构不符能重试/裁剪。

### Phase 1 门
85 页 ≥84/85；171 页 ledger 可证；1001 页预算内；高数/化学 0 违规；公式 0 裸 LaTeX；图片 0 串图；试卷答案 100% 覆盖。

---

## 4. Phase 2：UI/UX 重构（2-3 周）

### 4.1 设计系统
- [ ] 单一 token：颜色/字号/间距/圆角/阴影/动效；对比度 ≥4.5；暗色覆盖全部页面。
- [ ] 字体：标题/正文/数据/公式统一；行宽 60-75 字符；长公式横向滚动。
- [ ] 组件库：按钮/输入/卡片/表格/弹窗/抽屉/空态/错误态/加载态/骨架屏；按钮 loading/success/failure/disabled。

### 4.2 信息架构
- [ ] 首页：今日目标 → 继续学习（一门课）→ 最近生成 → 课程列表；删“下一步建议/预计提分”噪音；最近生成修复。
- [ ] 阅读页：正文为主；目录/速查/重生成/AI 收进可折叠工具；首屏见正文；TOC 修复（完整标题、extract 也有）；阅读进度真实；窄窗目录抽屉。
- [ ] 复习计划：今日 X 题/预计 Y 分钟/进度条 → 按课程/章节/掌握度分组 → 单题入口带 `?mistake=id`；完成态。
- [ ] 课程详情：目标/进度 → 资料（含老师重点）→ 生成物；修 `Files 1`、`core` chip、死链接。
- [ ] 练习页：错题优先 tab；判分错误态；提交去重；`quizCourse=7` 删除。
- [ ] 设置：Key、备份/恢复、显示测试数据、导出诊断、隐私/协议入口；危险区不贴边。

### 4.3 修复死按钮/假功能
- [ ] reset 绑定修复；阅读页编辑要么接 `PATCH /api/files/{id}/content`，要么移除“保存”文案。
- [ ] 套数下拉生效；materialMode 常显；题型合计校验前置；SSE/`job_id` 错误态；`es.onerror`。
- [ ] 全局搜索接真实检索或移除 ⌘K；课程/笔记/错题统一搜索。
- [ ] 上传页编辑链接、失败汇总、无课程空态；孤儿页处理。

### 4.4 三语言与可访问性
- [ ] 改 `data-i18n` 键值驱动；English/繁中全量走查（无 CJK 残留，输入/aria/title 也覆盖）。
- [ ] Hant 用短语表 + 白名单，不做单字替换。
- [ ] 键盘 Tab/焦点陷阱/Esc/aria；Lighthouse/axe 0 对比度违规。
- [ ] 断网/Key 失效/解析失败/生成失败/空数据/加载中的统一状态与重试。

### 4.5 UI 测试
- [ ] 截图矩阵：1440/1024/900 × 明/暗 × zh/en/zh-Hant × 首页/阅读/计划/课程/练习/设置。
- [ ] 按钮审计脚本：每个可点击元素有 handler、有反馈、无 `href="#"`。
- [ ] e2e（Edge headless 或 Playwright）：新建课→上传→生成→阅读→做题→错题→复习。
- [ ] 导出矩阵：HTML/PDF/Word × 三语言 × 长公式 × 图片。

### Phase 2 门
无死按钮；三语言无残留；对比度/键盘通过；窄窗可用；e2e 全绿；截图矩阵签字。

---

## 5. Phase 3：发布工程（2-3 周，与 Phase 1/2 并行）

### 5.1 自包含桌面壳（二选一，推荐 Electron + 打包后端）
- [ ] Electron 主进程用 `app.getAppPath()/resourcesPath` 定位 web 与后端；不再硬编码开发路径。
- [ ] 后端 PyInstaller `--onedir` 打进 `Resources/backend`；启动参数/端口/数据目录显式。
- [ ] 单实例锁；health 校验 JSON `{"ok":true}`；失败弹 dialog + 日志；退出 await 后端；端口冲突处理。
- [ ] 首次启动：数据目录、迁移、隐私同意、Key 引导。
- [ ] 验证：把项目目录改名后启动仍可用；双开只聚焦第一实例；kill 后端有提示。

### 5.2 Mac 签名/公证
- [ ] Developer ID Application 证书；hardened runtime；entitlements（audio/network 按需）。
- [ ] `notarytool submit --wait` + `stapler staple`；DMG 制作。
- [ ] universal2 或明确 arm64+x64 两个包；体积门。
- [ ] 验证：`codesign -dv` Developer ID+Team；`spctl -a -vvv` accepted；干净 Mac 双击直接打开；离线启动。

### 5.3 Windows
- [ ] spec 的 EXE 加 icon/version；`python-multipart`；依赖锁定。
- [ ] `build_windows.ps1` 每步检查 `$LASTEXITCODE`；产物存在校验；zip/安装器（NSIS/Inno）。
- [ ] Windows CI（windows-latest）构建 + artifact；实机 Win11 冒烟。
- [ ] 验证：干净 Win11 上传 PDF→生成→导出→重启数据还在；中文路径正常。

### 5.4 更新/崩溃/备份
- [ ] 自动更新（electron-updater 或自建）：签名 feed、灰度、回滚。
- [ ] 本地崩溃日志 + 可选崩溃上报（默认关、明示、可导出）。
- [ ] 自动备份（启动/退出/升级前）+ 恢复 UI + 导出/导入。
- [ ] 卸载不删用户数据（或询问）。

### 5.5 合规
- [ ] LICENSE 改 AGPL-3.0；THIRD_PARTY_NOTICES（PyMuPDF/KaTeX/Mermaid 等）；源码获取说明。
- [ ] PRIVACY.md / TERMS.md：数据流向（DeepSeek/百炼/CDN/音频）、保留期、删除方式；首启同意；设置入口。
- [ ] Key 存 keyring 或明示明文 + `chmod 600`；音频上传披露。
- [ ] 版本/tag/CHANGELOG 一致。

### Phase 3 门
Mac 公证通过；Windows 实机冒烟；自动更新可回滚；崩溃日志可导出；备份恢复演练；AGPL/隐私/协议齐。

---

## 6. Phase 4：评测与回归（1 周 + 长期）

- [ ] `evaluation/sets/v1/`：三份终极测试 + 三份期末卷 + 5-10 份代表资料；每份 10-20 条 ground truth（考点/页码/答案）。
- [ ] 双臂：TermFinale vs 直接问 AI（同一资料+强提示词）；盲评 2 人。
- [ ] 指标：覆盖率、页码正确率、无出处率、错讲率、题目可用率、答案正确率、耗时、成本。
- [ ] 门槛入 CI；低于门槛非 0；报告归档带日期。
- [ ] 错误库：每个真实失败 → fixture + 回归测试。
- [ ] 提示词/模型变更必须跑评测；记录版本。

### Phase 4 门
一条命令产出双臂报告；门槛可失败；连续 3 次改动无回归。

---

## 7. Phase 5：内测与发布（1-2 周）

- [ ] Beta 包：版本、sha256、下载、安装说明、已知限制、反馈模板。
- [ ] Key 模式二选一：自带 Key + 报销（推荐）或独立限额 Key/代理；不共享。
- [ ] 10 人内测：每周 triage；P0 24h、P1 72h；内容事故（错讲/漏页/答案错）单独标签。
- [ ] 发布检查表：四根柱子门、官网、GitHub Release、回滚方案、客服话术。
- [ ] 发布后：崩溃 triage、更新通道、隐私/协议、CHANGELOG。

---

## 8. 贯穿全程的测试流程

### 8.1 测试金字塔
- 单元：纯函数（parser 分页、ledger、constraints、teacher_note、exam_builder、exporter）。
- 集成：服务层 + 假 LLM（成功/空/超时/401/429/截断/乱格式），临时 DB + 临时 HOME，不写用户数据。
- e2e：真实 server（临时端口）+ headless Edge + 固定资料；覆盖新建课→上传→生成→阅读→做题→错题→复习。
- 手工矩阵：Mac/Win、明/暗、三语言、窄窗、导出、升级/卸载。

### 8.2 夹具与快照
- 公式语料（`<`、`&`、分段、矩阵、`\(\)`）。
- 页/块 fixture（含【】文件名、Group/OLE PPT、混合扫描 PDF、1001 页）。
- 提示词快照（老师规则/试卷结构/语言）。
- 导出色标（HTML/PDF/Word）。

### 8.3 故障注入
- API：超时、401、429、空返回、截断、乱码、慢响应。
- 文件：损坏 PDF、加密 PDF、0 页、超大、缺 soffice、缺字体。
- 系统：磁盘满、DB 锁、断电/kill -9、端口占用、双开。
- 数据：迁移失败、备份损坏、恢复中断。

### 8.4 数据安全演练（每次发布前）
- 备份 → 删库 → 恢复 → 课程/生成物/笔记/错题完整。
- 生成中 kill -9 → 重启 → 任务 interrupted、无半成品覆盖。
- reset 后原资料仍在、仅上传副本/生成物被清。

### 8.5 性能与长任务
- 85/171/1001 页：耗时、内存、调用次数、成本、取消延迟。
- 3 个任务并发；断点续跑；低电量/休眠行为。
- 报告写进 `docs/perf_<date>.md`。

### 8.6 安全
- 无 token/错 Origin/路径穿越/超大上传/恶意文件名/重置接口。
- 依赖漏洞扫描（pip-audit/npm audit）；许可证扫描。

---

## 9. 发布门矩阵（签字表）

| 门 | 检查项 | 证据 | 状态 |
|---|---|---|---|
| G0 数据 | clean checkout 启动、备份恢复、reset 不删原件、日志 | 命令输出/录屏 | ☐ |
| G1 内容 | 85/171/1001、三份终极测试、公式/图片/试卷 | ledger/校验 JSON/评测 | ☐ |
| G2 UI | 无死按钮、三语言、a11y、窄窗、e2e | 截图矩阵/脚本 | ☐ |
| G3 发布 | Mac 公证、Win 冒烟、更新/崩溃/备份、AGPL/隐私 | codesign/安装包/演练 | ☐ |
| G4 评测 | 双臂报告、门槛、错误库 | 报告/CI | ☐ |
| G5 内测 | 10 人、P0=0、已知限制 | 反馈表/issue | ☐ |

---

## 10. 风险登记

| 风险 | 概率 | 影响 | 应对 |
|---|---|---|---|
| Apple 账号/证书缺失 | 高 | Mac 无法发布 | 立即确认；Beta 先未签名并明示 |
| 无 Windows 实机 | 高 | Windows 无法验收 | 借/租 VM；CI 构建不能替代实机 |
| 模型 API 变更/涨价 | 中 | 内容不稳定/成本升 | 评测门槛 + 模型可切换 + 预算上限 |
| 内容质量波动 | 高 | 用户不信任 | 硬校验 + 重试 + 明示缺页/存疑，不静默 |
| 数据丢失 | 中 | 致命 | 备份/恢复 + checkpoint + reset 不删原件 |
| UI 范围失控 | 中 | 延期 | Phase 2 结束后冻结，只修 P0 |
| 许可证 | 中 | 开源侵权 | 先定 AGPL/商业授权，再 push |
| 上下文/交接丢失 | 高 | 返工 | 所有决策落盘 docs/，HANDOFF 更新 |

---

## 11. 需要你提供/决定

1. 授权 git 提交/推送；先 `release/0.1` 分支。
2. 许可证：AGPL-3.0（推荐）或购买 Artifex 商业授权。
3. Apple Developer 账号/证书；没有则 Beta 未签名。
4. Windows 实机/VM。
5. 桌面壳：Electron + 打包后端（推荐）或 pywebview。
6. 测试数据：`is_test` 默认隐藏、归档不删。
7. 评测集版权/真值/是否入私有库。
8. 内测 Key 模式（自带+报销 推荐）。
9. 化学“命名违规”口径/脚本。
10. >150 页承诺（概览 vs 逐页）。
11. 老师重点输入位置（课程+任务 推荐）。
12. 验证 API 预算上限。

---

## 12. 第一周日程（建议）

| 天 | 内容 | 产出 |
|---|---|---|
| D1 | git 入库/分支/tag；CI 全量；DB checkpoint+backup | 可回滚基线 |
| D2 | 鉴权/CORS/reset/exam_date；日志；python-multipart | 安全补丁包 |
| D3 | is_test 迁移+过滤；首页 recentGrid/死按钮/假编辑 | 干净首屏 |
| D4 | 逐页 ledger + 解析层总页数；85 页复测 | 真实覆盖率 |
| D5 | 公式转义/`\(\)`/裸 LaTeX；图片前缀/缓存 | 公式/图片门 |
| D6 | `source_pages` 修复；长文档 10k 截断止血 | 校验恢复 |
| D7 | 回归测试 + 审计文档更新 + 周报 | 第一周证据 |

---

## 13. 交接纪律

- 每个决策写进 `docs/`（本文件 + AUDIT + HANDOFF）。
- 每个修复附：改了什么、怎么验、通过/不通过、证据。
- 长任务落盘、可续跑；不把“检查”说成“已修复”。
- 不重置用户数据、不删原资料、不把测试数据混进正式界面。

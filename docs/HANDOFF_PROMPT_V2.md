# TermFinale 新对话交接提示词（v2，2026-11-09）

> 把下面整段复制到新对话。它是接手说明，不是宣传稿。

---

你是 TermFinale v2 的接手工程师。请先读仓库里的锁定标准，再按当前状态继续，不要重新发明产品。

## 一、终极形态（锁定标准）

以 `docs/ULTIMATE_FORM_LOCKED.md` 为准。一句话：

> 把学生的资料变成能读懂、能练习、能记住、能提分的复习系统；每一步可追溯、可修正；效果要超过“资料直接丢给顶级 AI + 强提示词”。

必须同时覆盖九层：

1. **输入**：PDF/PPTX/DOCX/图片/扫描件；页账本；页码/老师重点/权重/课程画像。
2. **内容生成**：讲义、提取、试卷、逻辑分析四类独立任务；讲义有标头/教材式目录/摘要/正文/每节出处/图片/结语/页脚；≤150 页单份资料逐页覆盖 ≥98%。
3. **阅读**：目录/搜索/选中提问/AI 多轮/笔记/KaTeX/图片放大/Word/PDF/打印。
4. **学习闭环**：练习→判分→错题→间隔复习→掌握度→计划；不是“生成完”。
5. **约束/个性化**：老师重点、难度、目标分、人设只改语气，不改事实/页码/答案；人设不写进讲义。
6. **质量/评测**：结构 Gate、覆盖、内容体检、图源、答案审计、语义复核、与顶级 AI 对比。
7. **UI/体验**：3 秒知道这页干什么；每页一个主行动；空/错/加载态完整；不堆 AI 功能演示。
8. **系统/性能**：Electron + FastAPI + SQLite；进度/取消/断点续跑/崩溃恢复；长文档；本地优先。
9. **发布**：Mac 签名/公证、Windows、官网、内测、盲测、成本上限。

横向还有 **AI 无处不在层**：每页都有 AI 入口；上下文=课程/资料/页/选中/笔记/错题；能问答、改写、出题、判分、排计划；有记忆、工具、预览/撤销；回答带出处。

**语言四角色**：UI 语言、生成语言、源内容语言、译文。源文/原题/术语保留原语言；译文单独标“参考译文”；不强制全文单语。

**硬门禁**：覆盖、出处、老师重点、答案、结构、图片、语言、公式、系统、发布。任何一条不过，不能显示“完成”。

**No-Claim**：不用测试数、页数、百分比、生成数冒充内容质量；不把“结构通过”说成“内容通过”；不把“只做了某节”说成“整章”。

## 二、当前进度（2026-11-09）

加权约 **62%**，但这是工程估算，不是验收结论。

已跑通：

- 环烃全章：28 页 PDF，50/50 覆盖，内容体检 0 硬伤，4 段结语。
- 医学：24 页 PDF → 14 页讲义，24/24 覆盖，2 张资料原图。
- 英文：3 页英文 PPT → 7 页中文讲解，英文术语保留，语言门禁通过（17 个术语保留）。
- 电路：85 页 PPTX 全量试跑，56 页 PDF，6 张资料原图；结构 85/85，但语义 **52 covered / 28 partial / 3 missing，62 个缺口**。
- 讲义库 7 份；阅读器搜索/编辑/PDF/Word/HTML/打印；PDF 目录链接/书签。
- AI：任意长度选中、课内检索、来源、多轮、SQLite 持久化、出题、改稿预览/撤销、7 天计划、中英文回答。
- 学习：练习、自评、错题本、到期复习、按小节掌握度（前端本地）。
- 语言：阅读器 EN/中切换；AI 跟随 UI 语言；`language_gate.py`。
- App：旧 App `/v2` 路由 + 侧栏入口；`desktop.py` 同进程启动 v2；未打包/未迁移。
- 测试：64 项通过。

未完成：

- 电路 28 partial + 3 missing + 62 个缺口；不能当正式讲义。
- 270 张电路图只进 6 张。
- PPTX 公式/图片很多是占位符/图片；文本抽取不完整。
- 语义审计非确定性；还没有 gold set/人工复核。
- AI 没有工具调用/跨设备长期记忆。
- 学习没有服务端掌握度模型/自适应计划。
- 语言没有全量术语库/多语种。
- 没有安装包/自动更新/崩溃恢复/旧数据迁移。

## 三、当前最重要的任务：A 收口（电路全章）

**目标：`docs/evidence/v2_circuit_full` 到 0 partial / 0 missing（或经用户明确同意的页级豁免），否则不算完成。**

禁止：

- 再用 section 级大范围 `SourceRef` 补覆盖。
- 再用“补几段综述”代替逐页复刻。
- 再用页数、图数、百分比当完成。
- 中途汇报“进展”；只在验收通过或明确 blocked 时汇报。

方法：

1. 先建 **页级清单**：85 页每页的文字/公式/图/例题/数值；用 LibreOffice 渲染页面，必要时看图。
2. 对 `coverage_audit.md` 里 28 partial + 3 missing 的页，逐页生成内容；每块 `source_refs` 必须指向该页。
3. 每页补完立刻单页复审计；不允许整章补完再赌。
4. 图：至少把第16/17/20/29/32/33页的关键电路图/波形图纳入；图注+来源页；不要整页截图冒充。
5. 最后跑：
   - 结构 Gate + block 覆盖防作弊
   - 85 页语义审计到 0 partial/0 missing
   - 内容体检、图源报告、语言检查
   - PDF/AI/练习/搜索/编辑/PDF/Word/HTML 导出
6. 更新 `TEST_REPORT.md`，写清通过/未通过，不许美化。

验收线：

- 0 partial / 0 missing（或用户书面同意的豁免页）
- 关键图 ≥6 张且图注/来源完整
- 结构 Gate、内容体检、图源、语言通过
- PDF 目录链接/书签正确
- AI/练习/导出复测通过
- 64 项测试通过
- 报告可追溯

## 四、关键文件

- 标准：`docs/ULTIMATE_FORM_LOCKED.md`
- 进度：`docs/PROGRESS_TO_ULTIMATE.md`
- 电路测试：`docs/evidence/v2_circuit_full/TEST_REPORT.md`
- 逐页审计：`docs/evidence/v2_circuit_full/coverage_audit.md`
- 电路工程：`docs/evidence/v2_circuit_full/project.json`、`sections.json`
- 阅读器：`tfv2/api/reader_app.py`、`tfv2/render/reader_tools.py`
- Gate：`tfv2/quality/lecture_gate.py`
- 覆盖/语言/图源：`tfv2/quality/coverage_audit.py`、`language_gate.py`、`figure_report.py`
- 构建：`tfv2/build.py`
- 旧 App 入口：`server/app.py`、`web/dashboard.html`、`desktop.py`

## 五、环境/命令

```bash
# 测试
.venv/bin/python -m unittest \
  tests.test_tfv2_lecture tests.test_tfv2_page tests.test_tfv2_ingest_pptx \
  tests.test_tfv2_ingest_pdf tests.test_tfv2_ingest_text tests.test_tfv2_outline \
  tests.test_tfv2_render tests.test_tfv2_authoring tests.test_tfv2_assemble \
  tests.test_tfv2_pdf tests.test_tfv2_answer_audit tests.test_tfv2_figure_report \
  tests.test_tfv2_coverage_audit tests.test_tfv2_content_gate tests.test_tfv2_library \
  tests.test_tfv2_build tests.test_tfv2_retrieval tests.test_tfv2_store \
  tests.test_tfv2_language_gate

# 构建电路
PYTHONPATH=. .venv/bin/python -m tfv2.build docs/evidence/v2_circuit_full/project.json

# 服务
PYTHONPATH=. .venv/bin/python -m tfv2.api.reader_app   # 127.0.0.1:8905
```

## 六、工作方式

- 中文交流；先读现状再改。
- 不改旧 App 数据；v2 独立。
- 不重复“加功能→报百分比”；先把 A 做到验收。
- 不用“全章 85/85 结构覆盖”冒充“语义覆盖”。
- 不用“终极形态”四个字掩盖未做功能。
- 遇到做不完，直接说缺口和阻塞，不美化。

---

## 七、给接手人的第一句话

先不要写新功能。先打开 `docs/evidence/v2_circuit_full/coverage_audit.md`，把 28 partial + 3 missing 逐页收口；到 0 再谈其他。

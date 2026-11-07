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

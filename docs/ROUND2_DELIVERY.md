# 第 2 轮完成报告：不交付治理（2026-11-13）

## 这轮只做了什么

- 新增 tfv2/product/delivery.py：四档交付状态 + 硬/软门禁分类 + 缺口清单。
- 四档：validated（通过）/ review（待复核）/ partial（部分交付）/ rejected（硬错误）。
- 硬错误：总分≠100、题数严重不足、答案与解析矛盾、SymPy 失败、近重复>阈值、无题目/无来源。
- 软问题：页覆盖 35–45%（低覆盖交付为 partial）、单题审计冲突（review）、审计未完成（review）、少图/表格不完美。
- 讲义：有 PDF/HTML 的 draft 不再标 rejected，改 partial；无产物才 rejected。
- 提取：有 items 但页覆盖不足 → partial；无 items → rejected。
- 文档列表/详情：读库时重新跑 delivery，不把旧的 validated 永久当真；partial 保留 status、缺口、可导出标记。
- UI：docStatusLabel 新增“部分交付”中/繁/英，partial 徽标不再显示“部分覆盖”。

## 交付对象新增字段

- status：validated / review / partial / rejected
- delivery.hard_issues：硬错误列表
- delivery.soft_issues：软问题列表
- delivery.missing_pages：缺哪些页
- delivery.missing_questions：缺哪些题（当前为 0，逐题缺口后续补）
- delivery.exportable：能否导出
- delivery.retryable：能否重试/续跑

## 验收结果

- 新增 tests/test_delivery.py 11 项：
  - 正常卷 validated；
  - 低覆盖 partial，且 missing_pages 正确；
  - 1 个答案冲突 review；2 个冲突 rejected；
  - 总分 90 rejected；
  - 审计未完成 review；
  - 无题 rejected；
  - 提取低覆盖 partial、空提取 rejected、完整提取 validated；
  - 讲义 draft 有 PDF → partial。
- 全部 **429 项测试通过**（上轮 418，新增 11 项）。
- 负优化检查：原有测试全过；没改生成算法、没改 PDF/Word 渲染、没改排除逻辑。

## 和之前比，提升在哪（大白话）

之前：
- 门禁一失败就 rejected，用户拿不到东西；
- 低覆盖卷、单题冲突直接整卷拒绝；
- 讲义 PDF 失败只给草稿，状态还是“未通过”；
- 提取低覆盖直接 rejected，即使条目已经有价值。

现在：
- 硬错误才拒绝；软问题照样交付，标“待复核/部分交付”；
- 低覆盖卷会告诉你缺哪几页，仍可打开、导出；
- 讲义草稿有 PDF 就标“部分交付”，不再假装全废；
- 提取有内容就交付，缺页写清楚。

## 这轮没做（不假装）

- 真正的“逐题断点续跑”没做：现在保留 partial 产物、任务可 retry，但不会从第 7 题接着生成；这是下一轮可补的。
- 任务 PDF 导出仍会跑 PDF 门禁；如果 PDF 本身坏，导出会拒绝（这是有意的，不导坏文件）。
- UI 只加了状态文案/徽标，没有加“缺口清单”详情页；按路线 UI 大改在第 9–13 轮。

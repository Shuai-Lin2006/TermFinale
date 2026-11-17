# UI 前重规划 V2（2026-11-15）

## 真实差距

### 已经能用的

- 273 页扫描模电：20 页范围精准生成通过（521.9s，gate true，review）；
- 12 页高数样章：lecture / extract / exam 各 2/2 validated；
- 3 章同次 3/3 validated，701s；
- 页账本、页码范围、OCR、token 账本、workspace、子进程超时；
- 531 项测试通过。

### 2026-11-15 更新

- 100 页扫描模电 30–129：**delivered**，gate true，audit 90 covered + 10 overview；
- questions：2/2 有题（重庆 10、竞赛 5），仍 partial；
- 三语言 10 页：简/繁/英 gate 全过，Word 可导出；
- 536→537 项测试通过；
- 300 页整书、开源基准、全量三语言、UI 仍未做。

### 还差的

1. questions 未 validated：重庆卷仅 3 题带答案；竞赛卷 0 有效题；
2. 100 页 30–129 已 delivered；第二章节 130–229 仍 review（audit 14 covered）；
3. 300 页真实整书未跑；
4. 开源基准（MinerU/Docling/Marker）未完整对比；
5. 视觉质量：表格/图注/layout 仍跳过；
6. 三语言（简/繁/英）只跑 10 页，全量未跑；
7. 成本只到 token，CNY 账单未接；
8. UI 完全没有；
9. release gate 仍 false。

## 结论

- 后端大约 60–70%，不是“差一点”；
- UI 0%；
- “开源第一梯队”评分约 48%，还差 52%；
- 没有证据宣称第一梯队；
- 距离“可发布 beta”约 8–10 轮，距离“第一梯队”还要看基准。

## UI 前 9 轮

| 轮 | 交付 | 验收 |
|---|---|---|
| 1 | questions 逐页/版式解析 | 2 份带答案数学卷 2/2 有题，答案不丢 |
| 2 | 100 页扫描模电精准 | 100 页 gate 通过，时间/成本记录 |
| 3 | 真实 273 页分章/范围策略 | 章节覆盖率 100%，可只跑选定页 |
| 4 | 开源基准 | 20 页解析/表格/公式不低于最好基线 90% |
| 5 | 视觉质量恢复 | 表格/图注/layout 回归，无原始 LaTeX |
| 6 | 三语言 PDF/Word | 简/繁/英 3 组合目标语言正确、无乱码 |
| 7 | 成本账本/预算 | 真实 CNY 或明确 null；超预算停 |
| 8 | 页面问答/块状讲义/进度后端 | UI 前 API 可用，引用可回页 |
| 9 | release gate beta | 4 模块、100 页、3 章、3 语言全绿；UI 仍 off |

## 每轮规则

- 一轮一个主交付；
- 两次不过换架构/工具；
- 不把 partial 当 validated；
- 不进入 UI，直到第 9 轮门禁全绿。

## 进度

- 第 1 轮 questions 逐页：2/2 有题（重庆 10、竞赛 5），仍 partial；533 项测试。
- 第 2 轮 100 页模电：30–129 跑完，1869s；gate/content/pdf/language 全 true；audit 90 covered + 10 overview，audit_ok true，delivered；536 项测试。

## 下一步

第 1 轮收尾：失败页重试，把覆盖率做上去；然后第 2 轮 100 页模电精准。
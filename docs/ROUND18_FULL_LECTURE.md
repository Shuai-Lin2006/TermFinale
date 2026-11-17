# 第 18 轮完成报告：24 页整本讲义（2026-11-14）

## 实跑

- 资料：24 页解剖学 PDF；
- 当前管线重新生成，id gen_20261114_200319_66ad2a；
- 耗时 **568.5 秒（9.5 分钟）**，≤10 分钟；
- 页数 24；
- sections 3；
- blocks 全部有来源。

## Gate / 覆盖 / padding

- manifest gate：passed=true，issues 空；
- content_gate：issues 空；
- pdf_content_gate：issues 空；
- coverage_matrix：covered_pages 24 / page_count 24，**100%**；
- padding.audit_lecture：passed=true，8 项检查 0 问题。

## 与旧产物对比

- 旧 24 页产物 coverage 100%、padding 0、gate 通过，但 sections 8；
- 新产物 sections 3，仍覆盖 24/24 页，gate 通过；
- 说明覆盖不是靠“多切节”堆出来的，但章节粒度偏粗，后续可调。

## 测试

- 471 项测试通过（本轮未新增代码测试，验收是真实产物）。

## 如实说

- 耗时 9.5 分钟，接近 10 分钟上限；视觉图注超时拖慢，仍有优化空间。
- sections=3 对 24 页偏粗；页面覆盖 100%，但“每节讲得够不够细”不是页覆盖能证明的。
- 这是单份 24 页样本，不是所有学科都同样稳定。

## 下一步

第 19 轮：PDF 排版标准（字体/分页/孤行/图/表）。
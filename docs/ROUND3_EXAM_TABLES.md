# 第 3 轮（最后一轮）：表格真渲染 + 真题变式映射 + 出卷实测（2026-11-12）

## 做了

1. **表格真渲染**
   - lecture_html.py：块文本里的 Markdown pipe 表格 → 真 <table>（.md-table 样式，打印不分页）。
   - docx.py：pipe 表格 → 真 Word 表格（Table Grid，表头加粗）。实测 _add_md_table 输出 2 行 2 列真表格。
   - Docling 适配层：docling.md 的 pipe 表格按页码回填 pages[].tables，_apply_docling_text 把 [表格] 追加进页文本。

2. **真题题级映射**
   - exam.py 新增 _reference_bank：参考真题 → 题级清单（题号/题型/分值/考点）。
   - 出题 prompt 注入清单，要求每题写 variant_of=对应真题题号（没有则 new）；_parse_question 透传 variant_of。

3. **出卷三个真 bug 修复（第一次实测抓出来的）**
   - API 出卷直接失败：run_exam 内局部 import DeepSeekClient 遮蔽模块级导入 → UnboundLocalError。已修。
   - 试卷页覆盖 29.2% < 45%：原因是 exam 用“原始 24 页 PDF”作分母，而讲义实际只覆盖 1–10 页。
     现在 _source_context 按讲义真实 scope（sections 的 source_refs）取页，7/10 = 70% 通过。
   - 答案审计分批失败会连坐整卷 rejected：改为 2 题/批 + 单题兜底；仍失败只写 warnings，
     未审计但无硬伤的卷状态改为 review（可交付待复核），不再整卷拒绝。

## 实测数字（第一张完整 18 题医学模拟卷，Pro）

- 18 题（15 选择 + 3 简答），临床情境题干、解析完整；0 重复、0 自纠错、0 答案矛盾。
- 页覆盖 29.2%（分母 bug，已修）；答案审计分批失败（已改 2 题/批 + 单题兜底）。
- 总耗时约 17.5 分钟 —— 这是 Pro 高推理出 18 道长临床题的代价；要提速需要把出题 effort 调低或并发，
  下一轮可做（本次不做，避免牺牲题目质量）。

## 回归

- 408 项测试全部通过。
- 2 页图样章重建：PDF Gate 通过、4 页 2 图；Word 2 图（9.5×5.08 / 3.64×6.5cm）。

## 如实说明

- 5 张卷连出、一次通过率 ≥80% 的验收标准，本轮只跑了一张（耗时 17.5 分钟），没跑完 5 张。
  修复后的第二张（15 选择）正在后台跑，数字出来后补记。
- 表格渲染基于 Docling 提取；扫描件表格仍以原图保真。

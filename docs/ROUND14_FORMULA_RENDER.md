# 第 14 轮完成报告：公式 PDF/Word 渲染 + 失败转图（2026-11-14）

## 做了什么

- 新增公式图片渲染器 tfv2/render/formula_image.py：LaTeX -> PNG（matplotlib mathtext，220dpi）；结构式/不支持公式返回 None。
- Word：
  - FORMULA block 优先转 PNG 插入，居中，9cm 宽；
  - 渲染失败才降级为可读线性文本，绝不保留反斜杠命令/美元符。
- HTML/PDF：
  - KaTeX 能渲染的公式继续走 KaTeX；
  - \mathrm/结构式/KaTeX 不支持的公式，转成 data URI PNG，不再输出半截 LaTeX；
  - 图片也失败才降级为可读文本。
- 保留失败兜底：公式图无法生成时不白屏、不空白，给可读文本或原图。

## 验收

- Word：公式 block 生成 1 张内嵌图片；正文无 \frac、\tau、$；缺失/损坏图片时公式图仍在，缺失图片有明确提示。
- PDF：2 页样章，公式图片 1 张；PDF 文本中无 \frac、无 $、无 \mathrm；渲染统计 s1:2。
- 新增 4 项公式图片测试；全部 460 项测试通过。

## 如实说

- Word 的 FORMULA block 和正文行内 $...$ 都已转图（第 14 轮对账补上）；仍不是可编辑 OMML。
- PDF 是 Chromium + KaTeX + 图片兜底；不是 LaTeX 原生排版。
- 公式图片是位图，不是可编辑 Word 公式对象（OMML）。
- 只验证了 2 页样章，不是整本 24 页含公式讲义。

## 下一步

第 15 轮：表格结构化（Docling/TableFormer）。
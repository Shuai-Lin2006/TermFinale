# 第 16 轮完成报告：表格 PDF/Word 真渲染（2026-11-14）

## 做了什么

- HTML 表格改成标准 thead/tbody：
  - 表头在打印时用 display:table-header-group 重复；
  - 每个 tr 设置 break-inside:avoid，行不被拦腰截断；
  - 长表允许跨页，不再整表 break-inside:avoid 导致溢出。
- PDF：检测到管道表时强制关闭 Paged.js，走原生 Chromium 分页。
  - 原因：Paged.js 在长表最后一页不重复 thead；第一次实测第 4 页表头丢失。
- Word：
  - 首行加 w:tblHeader=true，跨页重复表头；
  - 每行加 w:cantSplit，行不跨页断裂。

## 验收

- Word 长表：首行 tblHeader 存在；所有行 cantSplit 存在。
- HTML：thead/tbody 存在，打印 CSS 有 table-header-group。
- PDF 30 行长表：
  - 共 3 页；
  - 表格出现在第 2–3 页；
  - 第 2、3 页都有表头“序号/名称/说明”；
  - 修复前第 4 页表头丢失，修复后 3 页且最后一页有表头。
- 新增 2 项测试；全部 470 项测试通过。

## 如实说

- 合并单元格、跨页拆分单元格还没做；本轮解决表头重复和行断裂。
- PDF 是 Chromium 分页，不是 LaTeX 表格排版。
- 只测了 30 行长表，不是整本 24 页含多表讲义。

## 下一步

第 17 轮：图片相关性 + 图注 + 尺寸上限。
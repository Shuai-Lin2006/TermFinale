# 第 12 轮完成报告：原题元数据 + CSV/Anki 导出（2026-11-14）

## 做了什么

- 原题提取新增 year（年份）、points（分值）、exam（试卷名）；source_no 原题号已有。
- 年份必须能在原文/题干中找到，找不到就留空，不让模型编年份。
- 新增导出模块 tfv2/product/exports.py：
  - questions CSV：no/year/exam/source_no/qtype/stem/options/answer/analysis/points/source_page/quote；
  - Anki CSV：Front/Back/Tags，可直接导入 Anki；
  - CSV 公式注入防护（= + - @ 开头加单引号）；
  - UTF-8 BOM，Excel/Anki 打开不乱码。
- 新增接口 GET /api/documents/{id}/export.csv?format=questions|anki。

## 验收

- 用 15 题模拟真题提取原题：
  - 15 条，状态 validated；
  - 年份 2025、原题号 1–15、分值 5.0 都写入；
  - CSV 表头正确；
  - 0 解析/答案问题。
- 新增 6 项测试：CSV 元数据、Anki Front/Back、注入转义、年份/分值、年份从题干取、编造年份被清空。
- 全部 453 项测试通过。

## 如实说

- 模拟真题全是简答题，所以 qtype 都是 short_answer；真实卷的选择/计算题型要靠原卷。
- 分值只有原卷/模型给出才写；没有就 0，不猜。
- 年份只认原文/题干里出现的 4 位数，不按当前年份补。
- Anki 导出是 CSV，不是 .apkg；Anki 里选“导入 CSV”即可，字段是 Front/Back/Tags。

## 下一步

第 13 轮：公式区域检测 + pix2tex OCR + 质量门。
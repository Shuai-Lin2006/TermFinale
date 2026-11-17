# 页面事实层试验（2026-11-15）

## 第一版

- 页面事实 JSON 注入 prompt；
- 10 页 audit：2 covered / 5 partial / 3 overview。

## 第二版：本地补事实块

- 从每页事实中补 5 条到 section；
- 10 个 block；
- 重建 gate true；
- audit：**2 covered / 4 partial / 1 missing / 3 overview**；
- 比第一版更差。

## 结论

- 只追加“原文事实”不能通过 audit；
- audit 要求解释/步骤，不是关键词列表；
- 当前“生成后补块”路线停止；
- 评分仍约 **48%**，距第一梯队 **52%**。

## 下一步

真正需要“逐事实生成解释”，而不是补摘录：

1. 每条事实生成一个解释 block；
2. 本地检查事实→block 映射；
3. 缺哪条只重写哪条；
4. 2 页组达到 8/10 再扩。
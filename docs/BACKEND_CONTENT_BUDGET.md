# 内容预算试验（2026-11-15）

## 改动

- section prompt 增加“本段必须覆盖的原文线索”；
- 每节最少 block 数：max(6, min(12, 页数*2))；
- 真实大纲 section 上限 4 页。

## 20 页内容页复测

- 范围：原书 170–189；
- 5 节；
- 耗时 569.7s（9.5 分钟）；
- gate/content/PDF/language 全 true；
- audit：**3 covered / 11 partial / 6 overview（习题页）**；
- status review。

## 结论

- prompt 增加了线索和最少 block，但没有实质提升覆盖；
- 技术 gate 仍然能过，内容仍不够；
- 当前瓶颈不是“节大小”，而是模型实际输出密度/覆盖约束没有被强制执行；
- 评分仍约 **48%**，距第一梯队 **52%**。

## 下一步

1. 生成后检查本段 block 数/字数；
2. 低于阈值自动重试一次，并在 prompt 里列出缺失页/缺失线索；
3. 用同样 20 页复测，比较 covered；
4. 不再只改 prompt 就重跑 100 页。
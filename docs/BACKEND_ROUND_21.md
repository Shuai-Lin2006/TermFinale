# Backend Round 21：章级质量报告（2026-11-15）

## 新增

tfv2/product/book_report.py：

- 读 chapter index + 每章 worker_result；
- 每章记录：status、pages、artifact_id、seconds、gate/content/pdf、error；
- 汇总：validated/done/failed/pending、total seconds、all_validated；
- 成本故意记 null：没有 token 账本就不编数字。

## 真实 3 章报告

文件：docs/evidence/book_report_3ch.json

- chapters 3；
- validated 3；
- done 0；
- failed 0；
- seconds **701.22**；
- all_validated true；
- cost_cny null（待账单接入）。

## 测试

**503 项通过。**

## 成本 / 存储

- DeepSeek 余额：**¥117.11**；
- 磁盘可用：**8.1 GiB**，高于 5G；
- 未删用户资料。

## 判定

- 章级质量报告：完成；
- 3/3 validated 可审计：完成；
- 成本账本：未完成（null，不伪造）；
- 完整视觉质量：未恢复；
- 第一梯队：未证明。

## 下一步

Round 22：成本账本——把每次模型调用的 token/耗时写进 book report，不再用 null；同时不改 UI。
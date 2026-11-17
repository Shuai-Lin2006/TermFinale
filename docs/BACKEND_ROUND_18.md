# Backend Round 18：全局预算 + 失败重试（2026-11-15）

## 改动

- run_subprocess 增加 global_budget_sec；
- 每章实际超时 = min(单章 timeout, 剩余全局预算)；
- 预算耗尽立即停止，未跑章保持 pending；
- 失败章可 retry_failed_once（预算内）；
- 超时错误现在报实际 effective 秒数，不再报虚数。

## 3 章全局 900s 实测

| 章 | 状态 | 章节用时 |
|---|---|---:|
| ch01 | validated | 253.9s |
| ch02 | failed | 25.99s（剩余预算只够 26s） |
| ch03 | validated | 200.1s |

- 总耗时 **900.1s（15 分钟）**；
- 预算被严格执行；
- **2/3 validated**，ch02 未完成。

## 测试

**502 项通过。**

## 成本 / 存储

- DeepSeek 余额：**¥118.84**（本轮约 ¥1.28）；
- 磁盘可用：**9.3 GiB**，高于 5G；
- 临时目录已清理。

## 判定

- 全局预算：完成；
- 预算内不无限烧：完成；
- 同次 3/3 validated：未完成（2/3）；
- 第一梯队：未证明。

## 下一步

Round 19：ch02 不再靠加大预算，改为**失败章单独重试+优先 Qwen**；如果仍失败，保留 failed，不拖累已 validated 章。
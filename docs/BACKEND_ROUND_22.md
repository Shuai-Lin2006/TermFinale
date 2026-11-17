# Backend Round 22：Token 账本（2026-11-15）

## 新增

- tfv2/llm/usage.py：进程级 calls / prompt / completion / total / by_model；
- DeepSeek json 与 Qwen json 每次成功后记账；
- chapter_worker 开始时 reset，结束时把 usage 写入 worker_result；
- book_report 汇总 calls/total_tokens，cost_cny 仍为 null，不编价格。

## 真实单章账本

ch01（12 页，validated，253.35s）worker_result：

- calls **7**；
- prompt **10,948**；
- completion **30,860**；
- total **41,808**；
- deepseek-v4-pro：6 次 / 37,810 tokens；
- qwen-plus：1 次 / 3,998 tokens。

报告：docs/evidence/book_report_usage.json

- 1 validated + 2 pending；
- calls 7；
- total_tokens 41,808；
- cost_cny null（待定价表）。

## 测试

**504 项通过。**

## 成本 / 存储

- DeepSeek 余额：**¥116.91**；
- 磁盘可用：**8.1 GiB**，高于 5G；
- 未删用户资料。

## 判定

- 真实 token 账本：完成；
- 每章 calls/tokens 可审计：完成；
- CNY 成本：未完成（不编造，等定价表）；
- 第一梯队：未证明。

## 下一步

Round 23：接入可配置价格表（DeepSeek/Qwen 单价由 env/配置提供），把 token 换算成 CNY；没有配置就继续 null，绝不硬编码错价。
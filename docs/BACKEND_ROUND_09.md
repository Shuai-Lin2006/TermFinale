# Backend Round 9：阶段计时定位（2026-11-15）

## 5 页真实高数阶段耗时

| 阶段 | 时间 |
|---|---:|
| artifact_created | 0 |
| ledger_ready | **84s** |
| plan_ready | <1s |
| requirements_ready | **18s** |
| sections_ready | **69s** |
| render_start / done | **23s** |
| 合计 | **约 194s** |

5 页生成 gate 未过（页数少/审计缺失），但阶段计时可用。

## 3 章硬超时

设置：

- TERMFINALE_SKIP_DOCLING=1
- TERMFINALE_SKIP_TABLE_VISION=1
- TERMFINALE_SKIP_FIGURE_VISION=1
- 每章 120s 硬超时

结果：

- ch01/ch02/ch03 全部 **TimeoutError**；
- failed 状态/耗时落盘；
- 但 worker 线程仍在跑，进程没有立刻退出；
- 已 pkill + 清临时目录。

## 结论

1. 不是单一视觉问题；ledger 84s 是主要慢点，sections 69s 次之；
2. 120s 对当前章节太小；
3. 硬超时必须用**子进程隔离**，线程超时不能真正杀任务。

## 测试

**498 项通过。**

## 成本 / 存储

- DeepSeek 余额：**¥132.26**（本轮约 ¥1.06）；
- 磁盘可用：**9.8 GiB**，高于 5G；
- 临时目录已清理。

## 下一步

Round 10：章生成改为**子进程 worker**，超时直接 kill；同时 ledger 分层计时（解析/OCR/结构/公式），找出 84s 具体来源；先解决速度和可杀，再谈 validated。
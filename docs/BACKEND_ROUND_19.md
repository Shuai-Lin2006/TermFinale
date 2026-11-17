# Backend Round 19：失败章 Qwen 优先重试（2026-11-15）

## 改动

- 新增 TERMFINALE_FORCE_QWEN=1：
  - 章节正文第 1 次直接走 Qwen；
  - 不先烧 DeepSeek。
- 用于 failed 章单独重试，不加大全局预算。

## ch02 结果

- 单独重试，Qwen 优先；
- 耗时 **255.0s（4.25 分钟）**；
- gate/content/pdf 全 true；
- 状态 **validated**。

## 3 章汇总（跨轮）

| 章 | 状态 | 耗时 |
|---|---|---:|
| ch01 | validated | 254s |
| ch02 | **validated** | 255s |
| ch03 | validated | 200s |

- 3 章均 validated；
- 但不是同一次全跑；
- 同次 3/3 仍未证明。

## 测试

**502 项通过。**

## 成本 / 存储

- DeepSeek 余额：**¥118.46**（本轮约 ¥0.38）；
- 磁盘可用：**8.3 GiB**，仍高于 5G，但比上轮少 1G；
- 临时目录已清理；
- 数据目录增长待查，下一轮先看谁占空间。

## 判定

- failed 章 Qwen 优先重试：完成；
- 3 章跨轮 validated：完成；
- 同次 3/3：未完成；
- 第一梯队：未证明。

## 下一步

Round 20：先查磁盘 1G 去哪了，清无用测试 artifact；然后把“失败章自动 Qwen 重试”接入 run_subprocess，再跑同次 3 章。
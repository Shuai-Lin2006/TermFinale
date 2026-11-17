# Backend Round 13：ch02 Qwen 备用生成（2026-11-15）

## 改动

- 章节正文第 1 次用 DeepSeek；
- 第 2 次空返回时改用 QwenTextClient；
- 不再对同一个空返回模型重复两次。

## ch02 结果

- 耗时 **215.5s（3.6 分钟）**；
- gate_passed=true；
- content_passed=true；
- pdf_passed=true；
- 状态 **validated**。

## 3 章汇总（跨轮验证）

| 章 | 状态 | 耗时 |
|---|---|---:|
| ch01 | validated | 126s |
| ch02 | **validated** | 215.5s |
| ch03 | validated | 约 160s |

- 本轮只补 ch02，未重跑 ch01/ch03；
- 3 章均 validated，但还不是同一次全跑。

## 测试

**501 项通过。**

## 成本 / 存储

- DeepSeek 余额：**¥125.42**（本轮约 ¥0.45）；
- 磁盘可用：**9.6 GiB**，高于 5G；
- 临时目录已清理。

## 判定

- ch02 validated：完成；
- 双模型章节备用：完成；
- 5 分钟内：完成（215.5s）；
- 3 章同次全跑：未验证；
- 第一梯队：未证明。

## 下一步

Round 14：一次跑 3 章（含公式预算、Qwen 备用），目标 3/3 validated、总时长 ≤15 分钟、成本记录；如果同次全跑失败，按章续跑，不重做已 validated。
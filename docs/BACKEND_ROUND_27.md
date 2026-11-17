# Backend Round 27：2 资料 × lecture/questions（2026-11-15）

## lecture：2/2 通过

| 资料 | 状态 | pages | gate |
|---|---|---|---|
| gen_...a1a08a | done | 12 | true |
| gen_...fa0dcd | done | 12 | true |

- 2 份真实讲义均 gate_passed=true；
- 单份约 249s / 258s；
- 输出在 outputs/lecture/。

## questions：0/2 可用

| 资料 | 状态 | 原因 |
|---|---|---|
| gen_...a1a08a | failed | Qwen Request timed out |
| gen_...fa0dcd | rejected | 0 条原题 |

- 一份模型超时；
- 一份返回 0 条，因为这两个源是**讲义/课件，不含原题**；
- 这不是“2/2 done”，不标完成。

## 耗时

- questions：352.7s；
- lecture A：249.4s；
- lecture B：257.9s；
- 合计约 860s（14.3 分钟）。

## 测试 / 成本 / 存储

- **512 项通过**；
- DeepSeek 余额：**¥114.81**（本轮约 ¥0.71）；
- 磁盘可用：**8.0 GiB**，高于 5G；
- 未删用户资料。

## 判定

- 2 资料 × lecture 真实：完成；
- 2 资料 × questions 真实：未完成（源无题 + 超时）；
- 2×4 全真实：未完成；
- 第一梯队：未证明。

## 下一步

Round 28：questions 不使用“讲义 artifact”，改用**真题来源**（上传真题 PDF，抽原题）；如果真题源也抽不出，输出“资料无原题”而不是 failed。
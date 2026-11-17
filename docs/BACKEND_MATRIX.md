# Backend 2×4 矩阵（2026-11-15，最终审计版）

## 真实结果

| 模块 | 资料 | 外壳状态 | 真实状态 | 证据 |
|---|---|---|---|---|
| lecture | A | done | **validated/gate true** | 249s, 12页 |
| lecture | B | done | **validated/gate true** | 258s, 12页 |
| extract | A | done | **validated** | 21 条，覆盖 100% |
| extract | B | done | **validated** | 23 条，覆盖 100% |
| questions | A（讲义源） | failed | 超时 | Qwen timeout |
| questions | B（讲义源） | done | rejected | 0 条 |
| exam | A | done | **validated** | 20 题，213.5s |
| exam | B | done | **validated** | 20 题，214.1s |
| questions | 真题源1 | done | **partial** | 7 题 |
| questions | 真题源2 | done | **no_questions** | 0 题 |
| questions | 高数二期中 | failed | 模型超时/空返回 | 0 题 |
| questions | 人工题库 A | done | **partial** | 3 题 manual_bank |
| questions | 人工题库 B | done | **partial** | 2 题 manual_bank |

## 结论

- lecture：2/2 真实通过；
- extract：2/2 **validated**，覆盖 100%（21/23 条）；
- exam：2/2 **validated**，各 20 题（10 选择+4 填空+4 计算+2 简答）；
- questions：讲义源不可用；真题源 1 份 7 题、1 份无题、1 份模型失败；人工题库 2/2 partial（3+2）；
- 2 资料 × 4 模块“全真实通过”：**没有做到**（questions 未满）。

## 原因（不猜）

- 讲义源没有原题，questions 抽 0 是资料问题；
- extract 已修复为 100% 覆盖，空页显式记录；
- 这些都必须继续修，不能靠表格变绿。

## 成本 / 存储

- DeepSeek 余额：**¥114.43**；
- 磁盘可用：**8.0 GiB**；
- 未删用户资料。

## 判定

- 2×4 路由：完成；
- 2×4 真实通过：**未完成**（lecture/exam 通过，extract partial，questions 不足）；
- 第一梯队：**未证明**；
- 30 轮内不能宣称同类型第一梯队。

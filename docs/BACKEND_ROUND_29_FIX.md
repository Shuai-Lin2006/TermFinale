# Backend Round 29：exam 0 题修复（2026-11-15）

## 根因

exam_handler 读顶层 sections（不存在），实际题目在 content.sections。  
不是模型 0 题，是读取层级错误。

## 修复

- 从 content.sections 汇总；
- 输出每个题型题数；
- rejected 但有题 -> partial；
- questions=0 -> no_questions；
- module_runner 允许 validated 状态。

## 修复后真实结果

| 资料 | 状态 | 题数 | 耗时 |
|---|---|---:|---:|
| gen_...a1a08a | **validated** | 20 | 213.5s |
| gen_...fa0dcd | **validated** | 20 | 214.1s |

题型：10 选择 + 4 填空 + 4 计算 + 2 简答。

## 2×4 矩阵更新

- lecture：2/2 validated；
- exam：2/2 validated；
- extract：2/2 partial（覆盖 58–67%）；
- questions：讲义源 0；真题源 1 份 7 题、1 份 no_questions；
- 2×4 全真实通过：仍未完成（extract/questions）。

## 测试 / 成本 / 存储

- **512 项通过**；
- DeepSeek 余额：**¥113.54**；
- 磁盘可用：**8.0 GiB**；
- 未删用户资料。

## 判定

- exam 读取/状态：修复；
- exam 2/2 validated：完成；
- 2×4：仍未完成；
- 第一梯队：未证明。

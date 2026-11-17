# Backend Round 34：人工题库 2/2 partial（2026-11-15）

## 改动

- question_bank 增加 material_id；
- 按资料隔离，A 的题不会兜底到 B；
- questions_handler 只在对应 material 的人工题里兜底。

## 真实演示

工作区 data/workspaces/exam_questions3：

- 2 份真题 artifact；
- 人工题库 5 条（3+2）；
- 强制模型失败，验证兜底。

结果：

| 资料 | 状态 | 条数 | 来源 |
|---|---|---:|---|
| A | partial | 3 | manual_bank |
| B | partial | 2 | manual_bank |

- 2/2 都有产物；
- 没有跨资料串题；
- reason=model_error，来源不冒充模型。

## 2×4 更新

- lecture：2/2 validated；
- extract：2/2 validated；
- exam：2/2 validated；
- questions：2/2 partial（人工题库）。

**全真实通过仍不算**：questions 是人工兜底，不是模型从真题抽全。

## 测试 / 成本 / 存储

- **516 项通过**；
- DeepSeek 余额：**¥112.86**；
- 磁盘可用：**8.0 GiB**；
- 未删用户资料。

## 判定

- 人工题库按资料隔离：完成；
- questions 2/2 有产物：完成（partial）；
- 全模型 2×4：未完成；
- 第一梯队：未证明。

## 下一步

Round 35：做最终“可发布/不可发布”二选一，不再把 partial 当 validated；把 2×4 结果写进发布门禁。
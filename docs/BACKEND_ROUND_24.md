# Backend Round 24：多资料工作区 + 四模块独立（2026-11-15）

## 新增

tfv2/product/workspace.py：

- create/load/save 工作区；
- materials 带 id/title/pages/path；
- 四模块：lecture / extract / questions / exam；
- 每个模块独立选料；
- 讲义只允许 1 份、出卷只允许 1 份主资料；
- 不允许选不属于工作区的资料；
- 同模块不允许重复选同一资料；
- independence_report 输出各模块选择。

## 真实演示

工作区：data/workspaces/demo_3ch

- lecture -> artifact A；
- extract -> artifact B；
- questions -> A + B；
- exam -> B；
- lecture_extract false，extract_exam true（这是选择结果，不是串料）。

## 测试

- 四模块独立；
- 改 lecture 不影响 extract；
- 未知资料拒绝；
- 讲义多选拒绝；
- 全量 **510 项通过**。

## 成本 / 存储

- DeepSeek 余额：**¥116.28**；
- 磁盘可用：**8.1 GiB**，高于 5G；
- 未删用户资料。

## 判定

- 多资料工作区：完成；
- 四模块独立选择：完成；
- 价格 CNY 实际：未完成（仍 null，等用户价格表）；
- 第一梯队：未证明。

## 下一步

Round 25：把 workspace 选择接入任务入口，跑 2 份资料 × 四模块的最小端到端，证明产物不串；仍不做 UI。
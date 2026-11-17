# Backend Round 25：2 资料 × 四模块端到端（2026-11-15）

## 新增

tfv2/product/module_runner.py：

- 从 workspace.resolve(module) 取当前模块选中的资料；
- 每份资料单独执行 handler；
- 每份资料写 outputs/<module>/<material_id>.json；
- 输出带 module/material_id/status/seconds/result；
- 未选资料或未知模块直接报错；
- 单份失败不覆盖其他资料。

## 真实验证

工作区 data/workspaces/demo_3ch：

| 模块 | 选中资料 | 结果 |
|---|---|---|
| lecture | A | all_done |
| extract | B | all_done |
| questions | A+B | all_done |
| exam | B | all_done |

输出分别落在：

- data/workspaces/demo_3ch/outputs/lecture/
- .../extract/
- .../questions/
- .../exam/

没有跨模块覆盖。

## 测试

**512 项通过。**

## 成本 / 存储

- DeepSeek 余额：**¥116.14**；
- 磁盘可用：**8.1 GiB**，高于 5G；
- 未删用户资料。

## 判定

- 四模块执行入口：完成；
- 2 资料 × 四模块不串：完成；
- 真实 LLM 产物：本轮用 handler 汇总，未跑四份真实生成；
- 第一梯队：未证明。

## 下一步

Round 26：把 module_runner 接到真实 extract/exam handler，先跑 2 份资料 × 2 模块（extract/exam）真实产物，证明不是只路由。
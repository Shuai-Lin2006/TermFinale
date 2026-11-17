# Backend Round 26：2 资料 × extract/exam 真实产物（2026-11-15）

## 新增

tfv2/product/module_handlers.py：

- extract_handler：调用 tasks.run_task(extract_points)，返回 items/coverage；
- exam_handler：调用 exam.run_exam(mock)，返回题目数/状态。

## 真实运行

工作区 data/workspaces/demo_3ch：

### extract

- 2 份资料都选；
- 使用 Qwen；
- 2/2 done；
- 输出：
  - outputs/extract/gen_...a1a08a.json
  - outputs/extract/gen_...fa0dcd.json

### exam

- 2 份资料分别跑 mock；
- A：189.2s，done；
- B：192.1s，done；
- 输出：
  - outputs/exam/gen_...a1a08a.json
  - outputs/exam/gen_...fa0dcd.json

每份产物带 module/material_id/status/result，没有跨资料覆盖。

## 测试

**512 项通过。**

## 成本 / 存储

- DeepSeek 余额：**¥115.52**（本轮约 ¥0.62）；
- 磁盘可用：**8.1 GiB**，高于 5G；
- 未删用户资料。

## 判定

- 2 资料 × extract 真实：完成；
- 2 资料 × exam 真实：完成；
- 4 模块真实全跑：未完成（lecture/questions 仍是汇总 handler）；
- 第一梯队：未证明。

## 下一步

Round 27：跑 2 资料 × lecture/questions 真实产物，补满 2×4；如果时间超，先做 questions，lecture 放最后。
# Backend Round 6：章级 artifact + checkpoint（2026-11-15）

## 已完成

新增 tfv2/product/chapter_artifact.py：

- build_index：按 longdoc 分章，每章生成独立 source.pdf + manifest + status；
- build_manual_index：无目录时按人工页码范围切章；
- run：逐章执行，每章写 running/done/failed，崩溃后从 pending/failed 续跑；
- index.json 记录页码、标题、artifact_id、错误；
- 测试：
  - 3 章，跑 1 章后停，续跑完成；
  - 第 2 章失败，重跑只补失败章；
  - 全量 **497 项通过**。

## 真实 3 章生成：失败

用真实 35 页高数手工切 3 章：

- ch01 1–12；
- ch02 13–24；
- ch03 25–35。

实际跑 ch01 时：

- 页面表格视觉识别 120 秒超时；
- 图注识别继续等待；
- 15 分钟仍未产出第一章；
- 已停止，清理临时目录。

**没有把 3 章标成 validated。**

## 问题定性

不是 checkpoint 逻辑问题，是**生成链路的视觉调用没有总预算**：

- 表格 OCR 120s 超时；
- 图注逐个等待；
- 章节小，但视觉成本不受控。

## 成本 / 存储

- DeepSeek 余额：**¥134.77**（本轮消耗约 ¥0.78）；
- 磁盘可用：**9.9 GiB**；
- 临时章节目录已删除。

## 判定

- 章级 artifact/checkpoint：逻辑完成，测试通过；
- 3 章真实 validated：**未完成**；
- 本轮不标完全通过。

## 下一步

Round 7：给视觉调用加**总时间预算 + 快速跳过**（无图/纯文本页不调视觉），再重跑 3 章；时间可控优先于多识别一张图。
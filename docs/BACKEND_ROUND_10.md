# Backend Round 10：子进程 worker + 3 章完成（2026-11-15）

## 子进程隔离

新增：

- tfv2/product/chapter_worker.py：一章一个独立进程；
- chapter_artifact.run_subprocess：Popen + start_new_session；
- 超时 killpg(SIGKILL)，不再留线程后台跑；
- 测试：
  - 超时进程 0.3s 内被 kill；
  - worker 正常返回 artifact_id；
  - failed 后续跑。

全量 **500 项测试通过**。

## 3 章真实生成

设置：

- SKIP_DOCLING=1；
- SKIP_TABLE_VISION=1；
- SKIP_FIGURE_VISION=1；
- SKIP_LAYOUT=1；
- SKIP_FORMULA_OCR=1。

结果：

| 章 | 页 | 状态 | artifact |
|---|---|---|---|
| ch01 | 1–12 | done | gen_20261115_014345_9ca7cf |
| ch02 | 13–24 | done | gen_20261115_014559_339d57 |
| ch03 | 25–35 | done | gen_20261115_014945_6b7a62 |

- 总耗时 **597s（约 10 分钟）**；
- 停 1 章后续跑完成；
- 但 **done 只代表 artifact 生成，不代表 gate validated**；
- 上述跳过公式/版面/图注，质量不可当正式交付。

## 阶段耗时（5 页）

- ledger 基础：1s；
- layout：13s；
- formula OCR：**60s**；
- requirements：19s；
- sections：72s；
- render：31s。

## 成本 / 存储

- DeepSeek 余额：**¥130.24**（本轮约 ¥2.02）；
- 磁盘可用：**9.8 GiB**，高于 5G；
- 临时目录已清理。

## 判定

- 子进程可杀：完成；
- 3 章独立 artifact：完成（非 validated）；
- validated：未完成；
- 第一梯队：未证明。

## 下一步

Round 11：章节状态读取 gate；只跳过非关键视觉，保留公式/表格；目标 3 章至少 2 章 validated，时间 ≤15 分钟。
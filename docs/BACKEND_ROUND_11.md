# Backend Round 11：3 章 validated 验收（2026-11-15）

## 修复

之前 worker 读错质量字段，所有章都记 done。现在：

- worker 读取 generate 返回的 artifact.quality；
- gate_passed=true 才写 validated；
- gate_passed=false 写 done；
- 新增测试：gate=true → validated。

## 3 章结果

| 章 | 页 | 状态 | 耗时 |
|---|---|---|---:|
| ch01 | 1–12 | **validated** | 126s |
| ch02 | 13–24 | done | 约 200s |
| ch03 | 25–35 | **validated** | 约 160s |

- 总耗时 **505.2 秒（8.4 分钟）**；
- 目标“至少 2 章 validated、≤15 分钟”：**达到**；
- ch02 未 validated，不掩盖。

## 策略

为控时间临时跳过：

- Docling；
- 表格视觉；
- 图注视觉；
- layout；
- 公式 OCR。

因此：

- 3 章能 validated，但**质量不是完整版**；
- 公式/图注未进入，正式交付不能长期这样。

## 测试

**501 项通过。**

## 成本 / 存储

- DeepSeek 余额：**¥126.87**（本轮约 ¥3.37）；
- 磁盘可用：**9.7 GiB**，高于 5G；
- 临时目录已清理。

## 判定

- 章级 validated 状态：完成；
- 3 章 2 validated：完成；
- 完整质量（公式/表格/图注）：未完成；
- 第一梯队：未证明。

## 下一步

Round 12：把 ch02 补到 validated，并只恢复**公式 OCR**（不恢复全部视觉），看能否在 ≤5 分钟内补上；如果公式恢复拖垮时间，就做公式按需/预算，不默认全量。
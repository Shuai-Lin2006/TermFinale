# Backend Round 12：ch02 + 公式预算（2026-11-15）

## 目标

ch02 补到 validated，只恢复公式 OCR，≤5 分钟。

## 结果

- 恢复公式 OCR 后，原 300s 超时；
- 加公式 OCR 预算 60s，超时保留原图；
- ch02 总耗时 **252.4s（4.2 分钟）**；
- 但生成阶段报 **“正文（第 1–8 页）生成失败：模型返回为空”**；
- ch02 仍 **failed**，未 validated。

## 已完成

- _add_formula_ocr 增加 TERMFINALE_FORMULA_OCR_TIMEOUT，默认 60s；
- 超时不再挂死，公式保留为图片；
- 3 章已有 ch01/ch03 validated，ch02 未补上。

## 测试

**501 项通过。**

## 成本 / 存储

- DeepSeek 余额：**¥125.87**（本轮约 ¥1.00）；
- 磁盘可用：**9.6 GiB**，高于 5G；
- 临时目录已清理。

## 判定

- 公式 OCR 时间可控：完成；
- ch02 validated：未完成；
- 瓶颈已从公式 OCR 转到 **LLM 空返回**。

## 下一步

Round 13：ch02 空返回段做 Qwen 备用生成/单段重试；如果两次仍空，就把 ch02 降级为 done 并记录，不再为 1 章无限烧钱。
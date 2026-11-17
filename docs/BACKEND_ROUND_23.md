# Backend Round 23：可配置价格表（2026-11-15）

## 新增

- tfv2/llm/pricing.py：
  - 从 TERMFINALE_PRICE_JSON 读取，支持 JSON 字符串或文件路径；
  - 结构：{"模型":{"input":元/百万,"output":元/百万}}；
  - 没有配置或未知模型 -> 返回 None；
  - 绝不内置价格。
- usage.by_model 增加 prompt_tokens/completion_tokens；
- book_report 每章 cost_cny，汇总仅在全部章可定价时给 CNY。

## 测试

- 无配置 -> None；
- 配置 2/8 元每百万 -> 1M prompt + 0.5M completion = ¥6；
- 未知模型 -> None；
- 全量 **507 项通过**。

## 实际

当前未配置价格表，book_report_usage.json 的 cost_cny 仍为 null。  
这是正确行为，不是漏算。

## 成本 / 存储

- DeepSeek 余额：**¥116.47**；
- 磁盘可用：**8.1 GiB**，高于 5G；
- 未删用户资料。

## 判定

- 价格表可配置：完成；
- token -> CNY：完成（有配置时）；
- 无配置不伪造：完成；
- 第一梯队：未证明。

## 下一步

Round 24：把价格表接入实际 book_report 示例，并用一次真实章节验证 CNY；价格值由用户配置，不硬编。然后转到多资料/四模块独立。
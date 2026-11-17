# Backend Round 33：人工题库兜底（2026-11-15）

## 新增

tfv2/product/question_bank.py：

- CSV / JSON 导入；
- 必须有 stem/题干；
- 保留 answer/analysis/page/type/tags；
- 同题干去重；
- 保存到 workspace/question_bank.json。

## questions 兜底

questions_handler 新增 bank_root：

- 模型抽 0 条 -> 用人工题，status=partial，source=manual_bank，reason=model_returned_zero；
- 模型异常 -> 用人工题，status=partial，reason=model_error；
- 没人工题 -> failed 或 no_questions，带 reason，不静默。

## 测试

- CSV 去重；
- JSON 缺 stem 报错；
- 模型失败时用人工题 partial；
- 全量 **515 项通过**。

## 成本 / 存储

- DeepSeek 余额：**¥112.91**；
- 磁盘可用：**8.0 GiB**，高于 5G；
- 未删用户资料。

## 判定

- 人工题库导入：完成；
- 模型失败兜底：完成；
- 2×4 questions 真正 2/2：仍未完成（需要真实人工题/更多真题源）；
- 第一梯队：未证明。

## 下一步

Round 34：用真实人工题导入一份 workspace，跑 questions 2/2 partial，把 2×4 矩阵收口；不再靠模型抽题。
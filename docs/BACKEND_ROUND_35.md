# Backend Round 35：发布门禁（2026-11-15）

## 规则

四模块必须都 validated，且每模块 ≥2 份资料；partial/failed 一律不可发布。

## 实际门禁

工作区 data/workspaces/demo_3ch：

| 模块 | 状态 | validated |
|---|---|---|
| lecture | validated, validated | true |
| extract | validated, validated | true |
| exam | validated, validated | true |
| questions | failed, rejected | **false** |

blockers：

1. questions: 存在非 validated 状态 [failed, rejected]
2. UI: 未完成
3. 基准: 未通过开源基准

**release = false。**

## 修复

release_gate 之前读外壳 done，现改为：

- 优先读 result.status；
- result.status=done 且 result.gate_passed=true -> validated；
- 不再把外壳 done 当 validated。

## 测试 / 成本 / 存储

- **518 项通过**；
- DeepSeek 余额：**¥112.71**；
- 磁盘可用：**8.0 GiB**；
- 未删用户资料。

## 判定

- 发布门禁：完成；
- 可发布：**否**；
- 3/4 模块 validated；
- 第一梯队：未证明。

## 下一步

Round 36：不再加功能，做“如果用户现在就要用”的最小可用路径：只开放 lecture/extract/exam，questions 明确标注需要人工题库；不隐藏失败状态。
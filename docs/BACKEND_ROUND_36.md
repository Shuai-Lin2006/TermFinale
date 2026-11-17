# Backend Round 36：最小可用 beta 路径（2026-11-15）

## 结论

- 只开放已验证三模块：lecture / extract / exam；
- questions 明确 manual_bank_required；
- UI 仍 false；
- release 仍 false；
- 这是 beta，不是发布。

## 实际 launch profile

data/workspaces/demo_3ch：

- mode: beta
- enabled: lecture, extract, exam
- disabled: []
- questions.enabled: false
- questions.mode: manual_bank_required
- release: false
- ui: false
- blockers: questions 非 validated、UI 未完成、基准未通过

## 测试 / 成本 / 存储

- **520 项通过**；
- DeepSeek 余额：**¥112.60**；
- 磁盘可用：**8.0 GiB**，高于 5G；
- 未删用户资料，未关机。

## 判定

- 最小可用后端路径：完成（beta）；
- 可发布：否；
- 第一梯队：未证明；
- UI：未动。

## 下一步

不再加新功能。若用户要用，只能按 beta：
- lecture/extract/exam 可用；
- questions 必须人工题库；
- 不得对外宣称 release 或第一梯队。
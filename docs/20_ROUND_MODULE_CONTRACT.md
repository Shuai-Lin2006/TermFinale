# 20 轮四模块合同（2026-11-15）

## 先承认

- 30 轮没做到第一梯队；
- 最近 20 多轮主要在做讲义/解析/PDF；
- questions 仍 partial；
- exam 只有样章；
- extract 没有真实 100/300 页复验；
- UI/基准未做。

## 20 轮目标（不是“最强”）

四个模块都达到“有真实材料、可复现、有明确优点、有受众”的 MVP。

| 模块 | 受众 | 必须有的真实优点 | 硬验收 |
|---|---|---|---|
| 讲义 | 100–300 页扫描教材学生 | 扫描件、页码范围、页级出处、公式/图、PDF/Word | 100 页 delivered + 10 页 audit |
| 提取 | 考前抓重点 | 页级知识点、覆盖率、缺失页显式 | 100 页 coverage ≥95% |
| 出题 | 真题练习 | 真题答案、页级引用、题型/分值 | 2 份真题 validated |
| 出卷 | 模拟考 | 按题型/分值/时间组卷、来源可追 | 2 份 100 分卷 validated |

## 20 轮分配

| 轮 | 目标 |
|---|---|
| 1 | 冻结 4 模块 golden/真实材料/验收脚本 |
| 2–4 | 解析+提取：Docling 100 页，coverage ≥95% |
| 5–7 | 出题：2 份带答案真题，validated |
| 8–10 | 出卷：按蓝图组 2 份 100 分卷 |
| 11–14 | 讲义：2 页→10 页→100 页，复用事实/结构 |
| 15–16 | 四模块交叉：同一材料跑 2×4 |
| 17–18 | 基准/优势验证：对比 MinerU/Docling/Marker |
| 19 | 成本/时间/稳定性 |
| 20 | release gate；未过直接判失败 |

## 第 1 轮基线（冻结）

- lecture：gate true / 100 页 / 90 covered → golden 通过
- extract：2/2 validated（21/23 条，样章）→ 通过
- exam：2/2 validated（各 20 题，样章）→ 通过
- questions：**2/2 validated**（重庆 5 题 + 竞赛 5 题，答案来自原卷/参考解答）→ 通过
- 合计：**4/4 模块通过**
- 验收脚本：tools/verify_modules.py，当前 **rc=0**

### 注意

- extract/exam 已改为 **100 页真实产物**验收；
- questions 已扩到 9+5 题，仍不是整卷全量；
- lecture 100 页只有第一章；
- UI/基准仍为 0。

## 100 页真实扩量（本轮）

- extract：**245 条、coverage 1.0、validated，415s**
- exam：**47 题，总分 100，validated，issues 为空**
  - 选择 37 / 填空 4 / 计算 4 / 简答 2
  - 引用 45/100 页；不覆盖全部页，但状态 validated
- questions：5+5 题库 validated，不是整卷
- 四模块 golden：**4/4，rc=0**

## 当前真实分数

- lecture：100 页第一章 delivered，2 页 delivered；
- extract：样章 validated；
- questions：2/2 partial（10+5）；
- exam：样章 2/2 validated；
- UI/基准：0。

总体仍约 **48%**。

## 规则

1. 不用 gate true 代替内容；
2. 不用模型 audit 当唯一裁判；
3. 单条失败只重跑单条；
4. 每个模块必须有真实材料，不用样章冒充；
5. 20 轮后没有四模块硬验收，就判失败，不再要轮次。
# Backend Round 28：真题源 questions（2026-11-15）

## 新增

tfv2/product/source_artifact.py：

- 把真题 PDF 直接建成 artifact；
- 不经过讲义生成；
- 有 source/source_pages/sections/manifest；
- kind=exam_source。

## questions 语义修复

- 0 条 -> no_questions（不是 failed）；
- 有题但 rejected -> partial；
- 不再把“资料里没题”当系统错误。

## 真实真题源

| 资料 | 页 | 状态 | 题数 |
|---|---:|---|---:|
| 高等数学期中试卷 | 2 | partial | 7 |
| 上海交大高数下册期末 B 卷 | 6 | no_questions | 0 |

- 模块总耗时 41.4s；
- 两份都产出独立 JSON；
- 7 题来自第一份；第二份源未抽到题，按 no_questions 记录。

## 测试

**512 项通过。**

## 成本 / 存储

- DeepSeek 余额：**¥114.43**；
- 磁盘可用：**8.0 GiB**，高于 5G；
- 未删用户资料。

## 判定

- 真题源导入：完成；
- questions 语义（partial/no_questions）：完成；
- 2 真题真实抽取：完成但仅 1 份有题；
- 第一梯队：未证明。

## 下一步

Round 29：收口 2×4 矩阵，明确哪些模块真实、哪些只路由；不再把 handler 汇总当真实产物。然后 Round 30 做最终审计，不宣称第一梯队。
# TermFinale 30 轮最终审计（2026-11-15）

## 一句话

**30 轮结束，但“开源同类型第一梯队”没有达成。** 我不把 2×4 路由、3 章速度和少量样章说成第一梯队。

## A. 已真实验证

1. 页账本：100/1001 页，0 failed，1001 页 0.94s；
2. 100 页提取：100% 页覆盖、fallback 0（历史运行）；
3. 3 章章节生成：同次 3/3 validated，701s；book_report 可审计；
4. 2 份 12 页讲义：gate_passed=true（249s / 258s）；
5. 2 份 exam：validated，各 20 题（213.5s / 214.1s）；
6. 2 份 extract：validated，页覆盖 100%（21/23 条）；
5. 自适应解析：纯文本不走 Docling；表格/扫描才走；
6. 公式 MFD：5 页 19 个公式框，7.2s；
7. 真实评分表：PyMuPDF/Qwen 均 2×12，空格不塌；
8. 四语言小样：英→英 0 中文；中→英 0.1% 中文；英→中已验；无乱码；
9. 工作区四模块选料：2 资料 × 4 模块不串；
10. token 账本：单章 7 calls / 41,808 tokens；价格表可配置；
11. 子进程 worker：硬超时 killpg；失败可续；
12. 测试：**512 项通过**。

## B. 只完成路由 / 外壳

- module_runner 2×4：lecture/extract/exam 各 2/2 validated；questions 不足；
- module_handlers lecture/questions：真实调用有，但 questions 源不足时 0；
- 300 页分章：合成 300 页 0 缺口，真实 300 页没跑；
- 四语言 PDF/Word：只有文本/小样，没有四组合终版；
- 工作区：后端选择器完成，未接 UI。

## C. 未验证

- 真实 300–600 页整书生成；
- 完整视觉质量（Docling 全量 + 表格 + 图注）；
- 100 页语义 gold 复跑（原 PDF 已不在磁盘）；
- 英文扫描件 OCR；
- 成本 CNY 实际账单（当前 null，等价格表）；
- 大数据量并发/内存/长时间稳定性。

## D. 失败 / 不能发布

1. **questions：讲义源 1 超时、1 零题**；真题源 1 份 7 题、1 份 no_questions；
2. 2 资料 × 4 模块全真实通过：**未达成**（lecture/extract/exam 通过，questions 未过）；
3. “开源第一梯队”：**无证据**，不能宣称；
4. UI：完全没动，不能发布。

## 当前成本 / 存储

- DeepSeek 余额：**¥113.54**；
- 磁盘可用：**8.0 GiB**，高于 5G 预留；
- 未删用户资料，未关机。

## 30 轮结论

- 底层有真实进展：页账本、3 章、2 讲义、workspace、token、子进程；
- lecture 2/2、exam 2/2 validated；
- extract 2/2 partial、questions 不足，仍没过质量门；
- 第一梯队不成立；
- 下一步不该做 UI，先把 extract 覆盖和真题 questions 修到 validated，再做真实 300 页与四语言终版。

## 未完成目标

本轮不把 goal 标 complete；objective 的“第一梯队”未达成。
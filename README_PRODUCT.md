# TermFinale 产品说明（真实状态）

## 它是什么

面向扫描教材/真题的学习台：

- 讲义：按页码范围生成可读 PDF；
- 提取：页级知识点与覆盖率；
- 出卷：按题型/分值生成 100 分试卷；
- 出题：从真题答案页抽题，带页码和答案；
- UI：本地学习台 + 模块验收页。

## 启动

```bash
./scripts/start_ui.sh
# http://127.0.0.1:8877/
# http://127.0.0.1:8877/modules
```

依赖已在 `.venv`；Docling 在独立 venv；XeLaTeX/typst 可选。

## 已验证的真实结果

| 模块 | 证据 |
|---|---|
| lecture | 100 页，gate true |
| extract | 100 页，245 条，coverage 1.0，validated |
| exam | 100 页，47 题，100 分，validated |
| questions | 15 题，重庆 10 + 竞赛 5，validated |
| 四模块 | golden 4/4，rc=0 |
| UI | / 与 /modules 200，截图通过 |
| 测试 | 543 通过 |

验收：

```bash
python tools/verify_modules.py
```

## 真实优势

- 扫描教材能读：Docling 10 页拿到 416 blocks / 7,857 字 / 13 图；PyMuPDF 0 字；
- 100 页 extract/exam 不是样章；
- 真题答案有页码，不靠编；
- UI 可打开、可看结果、可下 PDF。

## 明确限制

- exam 只引用 45/100 页；
- questions 只有 15 题，不是整卷；
- 整书 273 页未完成；
- 三语言只有 10 页样稿；
- MinerU/Marker 未接入；
- 全模块基准未完成；
- UI 是结果展示，不是完整生成工作流。

## 结论

这是一个 **56% 候选版**，不是第一梯队。  
不能把 gate/4/4/56% 说成完成。

## 证据

- docs/RC_56.md
- docs/PARSE_BENCH.md
- docs/20_ROUND_MODULE_CONTRACT.md
- data/ui/modules.png
- data/workspaces/modules_100p/
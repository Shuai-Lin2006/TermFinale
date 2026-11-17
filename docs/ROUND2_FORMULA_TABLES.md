# 第 2 轮（三轮冲刺）：公式区域检测 + 表格（2026-11-12）

## 装了什么

- **MinerU 的 MFD 公式检测模型**（opendatalab/PDF-Extract-Kit 的 models/MFD/weights.pt，YOLO 权重，
  约 102MB）→ 用 ultralytics（8.4.211，已装进 Docling venv）在 CPU 上跑。
  - classes: isolated（独立公式）、embedding（行内公式）
  - 实测 150dpi 页图 2.1s/页
- 新增 tools/formula_detect.py：批量页图 → 公式框 JSON。
- 表格局：Docling 适配层新增 tables 提取（pipe table markdown 按页号回填），
  _apply_docling_text 把 [表格] markdown 追加进页文本。

## 管线行为（tfv2/product/generate.py）

1. PDF 每页渲染 → MFD 检测公式框（isolated conf≥0.40 / embedding conf≥0.70）。
2. 裁框 → pix2tex 转 LaTeX。
3. _latex_ok 质检通过 → 追加 [公式OCR] $...$ 进页文本（写作模型看到真公式）；
   质检不过 → 把原公式框当**图片**挂进讲义（视觉永远不乱码），绝不灌错误 LaTeX。
4. 图文相关性：layout_/formula_ 图也走 _figure_supports VLM 相关性检查（超时放行，失败不报错）。

## 实测

- 高数 35 页：MFD 稳定给出公式框；pix2tex 对“整块多行公式”会幻觉，_latex_ok
  正确拦截（如 alrccoS、\mathrm 链全部拒绝），该页 3 个公式块全部以原图保真进入讲义，
  0 条错误 LaTeX 进入 prompt。
- 干净单条公式（渲染测试图）：OCR 通过质检，写回 LaTeX，KaTeX 可渲染。
- 404 项测试全部通过（新增 test_formula_and_tables 3 项）。

## 还差

1. 表格在 PDF/Word 里仍是“文本回填+原图”，不是渲染成真表格；Docling 的表格块
   已在结构里，下一步要把 [表格] 渲染成 HTML <table>/Word table。
2. 行内公式（embedding）OCR 置信不够时只保图，没有逐个转 LaTeX。

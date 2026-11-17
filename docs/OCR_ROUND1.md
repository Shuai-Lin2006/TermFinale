# 第 1 轮（三轮冲刺）：公式 OCR 落地（2026-11-12）

## 装了什么

- **pix2tex 0.1.4（LaTeX-OCR，开源）**：装在 Docling venv（/private/tmp 与持久路径两处），
  权重 weights.pth（97.4MB）已缓存并复制到持久 venv。
- 新增 tools/formula_ocr.py：批量图片 → LaTeX JSON（resize=False，跳过 3.14 上损坏的 torch-jit
  resize 模型，实测单条 0.4s）。

## 实测

- 渲染公式图 int(0..1) x^2/sqrt(1-x^2) dx = pi/4：
  OCR 返回带 \textstyle\int \frac \sqrt 结构的 LaTeX（dx 被识别成 Q X），KaTeX 可渲染。
- 接进 tfv2/product/generate.py：
  - DocLayout 检测到 isolate_formula 的框 → 裁图 → pix2tex → 把 [公式OCR] $...$ 追加进该页文本，
    讲义写作时模型看到的是 LaTeX 而不是乱码碎片。
  - 新增 _latex_ok() 质检：拒掉 Big/stackrel/bigotimes/begin{array 等幻觉输出；长度 <=220。
- 高数 35 页实机测试发现：这些 PDF 的文本层把公式拆成碎片，DocLayout 又几乎不报 isolate_formula，
  按行裁图给 pix2tex 会输出幻觉。因此行级回退（TFV2_FORMULA_OCR_LINES）**默认关闭**，
  只保留 isolate_formula 路径；宁可不 OCR，也不往讲义 prompt 里灌垃圾公式。

## 回归

- 全部 401 项测试通过。

## 还差（第 1 轮未完成部分）

1. 公式区域检测本身不够准：需要 MinerU 的 layout 模型，或对数学 PDF 用更可靠的公式块定位。
   这是公式无乱码的最后一块；目前仍在“原图裁图保真 + 干净公式可 OCR”两层。
2. 表格转 Markdown 未做（第 1 轮原计划的一部分，顺延）。

# 第 3 轮：接入 DocLayout-YOLO，讲义第一次有资料原图（2026-11-12）

## 装了什么

- **DocLayout-YOLO 0.0.4**：装在 docling venv（torch/transformers 已在该环境）。
- 权重：juliozhao/DocLayout-YOLO-DocStructBench（约 100MB，缓存到 ~/.cache/huggingface）。
- 依赖：matplotlib/seaborn/thop/py-cpuinfo/albumentations/albucore 等，已修到可 import。
- 新增 tools/doclayout_detect.py：输入页图，输出 title/plain text/figure/table/formula 的框和置信度。
- 主流程新增 _add_doclayout_figures：PDF 每页 150dpi 渲染 → DocLayout 检测 → 裁图 → 页标题图注 → 挂到对应节。

## 实测效果

### 2 页解剖样本（第 5–6 页）

- 检测到 2 张真实图：
  - 681×1215（副交感/交感概况）
  - 1438×769（脊髓横断面、脊神经、交感通路）
- 讲义：**2 张资料原图**、4 页 PDF、Gate 通过。
- 图注示例：用 Qwen 对裁图复核，返回“脊髓横断面及脊神经、交感神经通路示意图，示前后根、脊神经节、交通支与效应器”，说明裁出来的确实是图，不是文字块。
- 旧问题：Paged.js 在有图时会产生空白页；已在有 source figure 时改用 Chromium 原生分页，2 页样本从 7 页（含 2 张空白页）变为 4 页、0 空白页。
- 当前测试课程“解剖图文”保留在库里，可直接打开看 2 页样本。

### 10 页离线检测

- 10 页共检测出 11 个 figure/table 区域；说明版面检测可用，不是只对单页碰巧有效。

### 32 页生物 PPTX

- 先把 PPTX 用 LibreOffice 转 PDF，再走 DocLayout；32 页检测出 **23 个 figure 框**。
- 图注取页首标题句；长图注需要下一步截短/交给 VLM。
- 这条路径证明 PPTX 也可以接，不是只能 PDF。

## 还没做到

1. 图注默认还是页标题（如“（一）交感神经”）；VLM 图注只在复核时验证，没有批量写进图注。下一步把 VLM 图注作为默认，并做图文相关性检查。
2. 表格/公式区域目前只裁图，没有转成 Markdown/LaTeX。
3. PPTX 还没走 DocLayout（PDF 先跑通）；需要先把 PPTX 转 PDF 或渲染 slide。
4. Word 导出图片/公式仍弱。
5. 2 页样本内容只有 643 字，是短样本；不代表 24 页全章质量。

## 结论

这轮终于不是“装了包但没效果”：
- 讲义里出现了**资料原图**；
- PDF 能打印、Gate 通过、无空白页；
- 裁图内容经 VLM 复核是真实解剖图，不是文字截图。

## 插图尺寸（本轮补充）

- PDF：figure 最大 60mm 高 / 120mm 宽；实测 2 页样本图片高度 162.8pt ≈ 页面 19.3%，整图完整显示。
- Word：宽度上限 9.5cm、高度上限 6.5cm；实测 9.5×5.08cm 与 3.64×6.5cm，不再整页铺图。
- 公式/表格区域（isolate_formula/table）同样按版面裁剪保留原图，不会出现乱码文本。

## 用户“不考”提示词（本轮补充）

- 计划级过滤：label 或原页文本命中 must_not 的整节不生成；tests.test_plan_exclusions 4/4。
- 提取 prompt 增加“标题/页眉页脚/页码/目录项不算考点或名词”。

## 回归

- 全部 401 项测试通过（含 padding 4、plan_exclusions 4、trust、math_verify、product、build）。

## 仍然没做到（如实）

1. 公式没有转 LaTeX：目前以裁图保真，不是可编辑公式；Pix2Text/MinerU 未装。
2. 表格没有转 Markdown，仍是图。
3. 真题“第 X 题 → 变式第 Y 题”的题级映射未做。
4. AI 生图仍只是“概念示意图”（明确标注非精确图）；精确结构一律用原图/程序图，不放文生图。
5. 出卷成功率/速度没有进一步放宽；现有审计/三审换题已是最强路径，但不能保证每卷一次通过。

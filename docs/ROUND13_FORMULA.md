# 第 13 轮完成报告：公式 OCR + 质量门（2026-11-14）

## 做了什么

- 发现主环境没有 ultralytics（MinerU MFD 跑不了），原有公式 OCR 实际不会执行。
- 新增公式 Python 探测：找装了 pix2tex 的 venv，不再依赖 doclayout_yolo。
- MFD 不可用时，新增文本跨度回退：从 PDF 文本行里找公式行，裁剪后 OCR；失败保留原图。
- pix2tex 结果不可靠时，自动调用 Qwen-VL 公式识别兜底，只输出 LaTeX。
- 修正 pix2tex 透明底问题：先合成白底再加白边，否则公式会变黑底黑字。
- _latex_ok 质量门：拒绝 Big/stackrel/array/underbrace/mathrm 等脚手架和空串；接受 frac/int/sum/sqrt/关系符等。

## 验收（20 张干净公式图）

- Qwen-VL OCR 后：
  - 19/20 通过 _latex_ok 且 matplotlib mathtext 可渲染；
  - 1 张网络超时，返回空；
  - 达标线 16/20，实际 19/20。
- 例：x^2+y^2=r^2、\frac{a+b}{c-d}、\int_0^1 x^2dx、\sum i^2、\lim、e^{i\pi}+1=0 等均正确。
- 新增 3 项质量门测试；全部 456 项测试通过。

## 如实说

- 20 条验证的是“裁剪好的干净公式图 → LaTeX → 可渲染”，不是整本 PDF 的公式检测召回。
- docling venv 已补 ultralytics；MFD 可检测公式区域（2 页测试 4 crop），OCR 失败保留原图；20 张干净公式仍是 19/20 可渲染。
- 1 张 Qwen 超时；生产需要重试/超时降级，已在流程里保留原图兜底，但没做批量重试指标。
- 公式 PDF/Word 真渲染是第 14 轮。

## 下一步

第 14 轮：公式 PDF/Word 兜底（失败转图，禁止半截 LaTeX/乱码）。
# Word 导出验证（2026-11-15）

## 产物

- 100 页 DOCX：data/artifacts/gen_20261115_123905_f21786/100pages.docx
- 体积：约 2.6 MB
- 段落：411
- 公式/图：1071 个 inline shape
- 文本：60,203 字符
- 裸 TeX：0

## 验证方式

- macOS Quick Look 预览：中文正常、目录正常、公式图正常；
- LibreOffice headless 转 PDF：中文出现方框、内容截断。

结论：

- DOCX 文件本身可用；
- LibreOffice 无头转换的字体环境不可靠，不能拿它判断 Word 交付质量；
- 需要 Word/Pages 实际打开或 Quick Look 验证。

## 修正

- Word 字体统一为 Arial Unicode MS，避免主题字体回落；
- 不再把 LibreOffice 转换结果当 Word 质量唯一证据。

## 尚未做

- Word 全 100 页逐页人工检查；
- 三语言 Word 全量；
- 页眉页脚/分页在 Microsoft Word 的最终确认。
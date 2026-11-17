# TermFinale 发布前验收记录

日期：2026-11-10
入口：`/Users/lan/Desktop/TermFinale.app`

## 自动化

- 341 项单元测试通过。
- `tools/release_gate.py` 全部硬项通过。
- `tools/product_acceptance.py` 通过；0 页面错误。
- `tools/ui_sweep.py` 通过；0 JS 错误；中/繁/英、深浅色、移动端。
- `tools/reader_acceptance.py` 对生成讲义通过：搜索、编辑、Word/HTML 导出、AI 面板、图片与图注。
- `tools/figure_benchmark.py` 25/25；`tools/figure_semantic_benchmark.py` 9/9。
- `tools/golden_eval.py` 23 文档 bad=0；`tools/deliverable_gate.py` 6/6 PDF。

## 真实资料生成

使用桌面材料实际生成并检查：

- 医学图解 24 页，老师人设：3 节、9 图、PDF 15 页；无 U+FFFD/□。
- 同一材料学术AI人设：3 节、9 图；输出语气/结构不同。
- 第10讲操作符 24 页，English：英文正文、4 图；PDF 无乱码。
- 第10讲操作符 24 页，繁體：OpenCC 后正文/标题/页眉统一繁體；无乱码。
- 多资料合并（医学权重5 + C语言权重1）：48 页、9 节、18 图；权重体现在切分与篇幅；空白末页自动保留来源页说明。
- 生成内容处于 `review`（待逐页复核），语义审计缺失时不冒充 delivered。

## 任务/试卷/交互

- 五类内容工具任务全部 done：考点、名词、原题、思维导图、逻辑分析。
- 生成 14 题医学模拟卷，选择题 10 道自动判分；交卷写入 Attempt/错题。
- 试卷 PDF、DOCX 导出通过；Word 导出 9 图、MathML/公式检查通过。
- 题库导入 2 题、题库练习、删除接口通过。
- 笔记新增/列表/删除通过；阅读器选段存笔记通过。
- AI 本地检索回答、SSE 流式、反馈、联网检索通过。
- 主题/语言/个人资料/头像/备份接口通过。
- onboarding 三页、完成、首页必读提示、说明页通过。

## 本轮修复

- 多资料生成接口 `illustrations` 未定义导致 500；payload 误用单文件。
- 多资料末页空白导致整份失败；改为保留来源页并显式说明。
- 联网问题把“联网”当搜索词；清理指令前缀，搜索“DeepSeek 最新模型”返回相关来源。
- 生成 PDF 页眉标签不随 en/hant 本地化；HTML/PDF 标签映射。
- 繁體正文遗漏简体字符；OpenCC 统一转换。
- 英文生成重复小节标题；生成后去重并本地化小节标签。
- 阅读器验收脚本硬编码旧目录/旧搜索词；改为动态选择。
- 产品验收脚本仍检查旧首页卡片/迁移状态；改为当前总控台/备份。
- 打包版数据原先写进 App 内部；改为 `~/Library/Application Support/TermFinale/v3-data`，API key 从用户目录 `.env` 读取。
- 桌面 App 加入 `web_v2`、OpenCC 资源、新 Logo 图标。

## 已知边界

- 中文资料生成 English 时，正文已大部分英文，但文件名/部分术语/个别标题会保留中文；这是“保留源术语”策略的边界，仍建议人工复核。
- 生成讲义默认 `review`，需要逐页复核后才 `delivered`；不会假装机器审计完成。
- 非选择题不自动判分，需人工核对。
- 联网结果取决于外部搜索源，引用会标“资料外”。
- 自定义试卷蓝图低于 12 题会被 100 分规则拒绝。

## 交付状态

- 桌面 App：`/Users/lan/Desktop/TermFinale.app`
- 源码数据：已清空。
- 桌面 App 用户数据：已清空（保留本机 `.env` 用于 AI）。
- 下次启动：首次 onboarding，无课程/讲义/笔记/题库/试卷。

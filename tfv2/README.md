# tfv2

TermFinale v2 core, built in parallel with the old app.

## 已建

- `domain/`: `lecture.py`（讲义契约：标头/目录/摘要/分节/出处/图/结语/页脚/scope）、`page.py`（页账本）。
- `ingest/pptx.py`: PPTX → PageLedger，抽图到本地 assets。
- `ingest/pdf.py`: PDF → PageLedger，抽图到本地 assets。
- `ingest/text.py`: 控制字符/私用区符号清洗（如 2Ω）。
- `curriculum/outline.py`: 真实章节/小节大纲 + 覆盖校验；支持人工确认大纲。
- `llm/client.py`: DeepSeek JSON 客户端。
- `authoring/lecture.py`: 证据包 → 结构化小节；过滤“资料未给例题”，无例题示例标【延伸】。
- `authoring/assemble.py`: 大纲/小节 → LectureSpec。
- `quality/lecture_gate.py`: 讲义硬门禁（目录/摘要/空节/出处/图/正文 P.x/页脚/覆盖）。
- `quality/answer_audit.py`: 例题/答案审计（LLM 辅助，需人工复核）。
- `quality/figure_report.py`: 图注/来源页/尺寸/来源类型清单。
- `quality/coverage_audit.py`: 逐页知识点覆盖审计（文本页/提纲页/图片页）。
- `quality/content_gate.py`: 乱码/未渲染 TeX/复杂公式/空段/重复段体检（讲义、源页、PDF 三层）。
- `render/lecture_html.py`: 教材式 HTML（课程在上、成稿从 1 开始、无大卡片、分节出处、页脚；人设只影响生成，不写入标头）。
- `render/reader_tools.py`: 阅读器工具条（搜索/编辑/导出 PDF/Word/HTML/打印/带上下文的 AI 助手）。
- `render/pdf.py`: Playwright 打 A4 PDF，按实际分页回填目录页码并写 PDF 书签。
- `api/reader_app.py`: v2 讲义库 + 阅读器 + `/api/ask` + `/api/practice`（练习/错题/复习）+ `/api/chat`（聊天持久化）。
- `library.py`: 扫描 `docs/evidence/*/manifest.json` 的讲义库。
- `retrieval.py`: 讲义段落本地检索（给 AI 提供可引用来源）。
- `store.py`: SQLite 聊天持久化（跨刷新/跨会话）。
- `build.py`: `project.json` → Gate → HTML → PDF → 图源/体检/清单的通用构建 CLI。
- `figures/`: 自制环烷烃内角、椅式/船式、苯系命名示意图。

## 其他资料试跑

- `docs/evidence/other_materials/report.md`：24 页医学 PDF、85 页电路 PPTX 的页账本/乱码清洗均通过；`2Ω/4Ω` 这类私用区符号已映射保留。
- `docs/evidence/v2_english/`：英文 PPT → 中文讲解样章，英文术语保留 + 语言检查报告。

## 真实样章

- `docs/evidence/v2_ring_41/`：老师版 4.1，6 小节、2 图，Gate 17/17。
- `docs/evidence/v2_ring_41_gentle/`：温柔小姐姐版 4.1，更详细、更多类比，Gate 17/17。
- `docs/evidence/v2_ring_full/`：全章 50 页，13 小节、3 图，Gate 1–50 全通过。

限制：Word 导出未单独分页；图为教学示意；例题【延伸】需复核；4.2 事实需学科 reviewer 核对。

## 尚未做

- 真实分页/目录页码已用于 PDF（16/24/13 页）；HTML 目录会同步 PDF 页码。
- 图片重绘/图源报告、答案审计、提取/试卷/分析 v2。
- AI 问答目前是 context-only v0；检索、页码引用、权限/撤销未做。
- 接旧 App（v2 独立端口/测试数据目录）。
- 断点续跑/数据库/API。

## 测试

```bash
.venv/bin/python -m unittest tests.test_tfv2_lecture tests.test_tfv2_page \
  tests.test_tfv2_ingest_pptx tests.test_tfv2_ingest_pdf tests.test_tfv2_ingest_text tests.test_tfv2_outline tests.test_tfv2_render \
  tests.test_tfv2_authoring \
  tests.test_tfv2_assemble tests.test_tfv2_pdf \
  tests.test_tfv2_answer_audit tests.test_tfv2_figure_report \
  tests.test_tfv2_coverage_audit tests.test_tfv2_content_gate \
  tests.test_tfv2_library tests.test_tfv2_build tests.test_tfv2_retrieval \
  tests.test_tfv2_store tests.test_tfv2_language_gate
```

当前 64 项通过。

## 运行讲义库 + AI

```bash
PYTHONPATH=. .venv/bin/python -m tfv2.api.reader_app
# 打开 http://127.0.0.1:8905/（讲义库）
```

## 通用构建

```bash
PYTHONPATH=. .venv/bin/python -m tfv2.build path/to/project.json
# project.json: header/summary/closing/footer/sections_files/page_count/scope_pages/out_dir
# 可加 --no-pdf 跳过 PDF
```

## 标准

见 `docs/ULTIMATE_FORM_LOCKED.md`；路线见 `docs/REBUILD_PLAN_V2_2026-11-09.md`。

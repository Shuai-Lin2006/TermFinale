# TermFinale

> 把一堆课件，压成一份能在剩余天数内读完的期末讲义。

面向大学生的桌面复习工具：导入 PPT / PDF / Word → 本地解析（文本 + 图形）→ 按你的考试信息规划大纲 → 逐章生成讲义 / 试卷 → 输出可打印的单文件 HTML。

## 能做什么

| 模块 | 产出 |
|---|---|
| 讲义 | 按大纲分章，每章「必背 + 公式卡 + 例题 + 原位配图 + 自测」；支持全量/精简、5 种人设、中英双语 |
| 逻辑分析 | 一次生成：知识图谱（Mermaid）+ 因果链卡片 + 概念-公式-题型对照表 |
| 资料提取 | 按页打包提取名词/考点/原题，自动去重并报告覆盖率 |
| 训练试卷 | 按目标分生成「题型×数量×分值」蓝图，自动验卷（缺题/分值/重复/考点标注） |
| 复习管理 | 课程紧迫度模型（压力模型）、倒计时、今日建议 |

## 快速开始

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

配置 API Key（二选一）：

1. 项目根目录 `.env`（开发期）
2. 用户数据目录 `.env`（打包版推荐），路径见 [`docs/API_KEYS.md`](docs/API_KEYS.md)

```bash
.env 内容：
DEEPSEEK_API_KEY=sk-xxxx
DASHSCOPE_API_KEY=sk-xxxx     # 可选，用于图片说明
```

启动：

```bash
python main.py
```

## 打包

```bash
pip install pyinstaller
python tools/build.py
```

- macOS：`dist/TermFinale.app`
- Windows：`dist/TermFinale/TermFinale.exe`
- **建议 Python 3.12**：PyInstaller 对新版本解释器支持滞后
- 首次启动若缺 Key 会提示，不会闪退；崩溃日志写到用户数据目录 `logs/crash.log`

## 数据存放

| 系统 | 位置 |
|---|---|
| macOS | `~/Library/Application Support/TermFinale/` |
| Windows | `%APPDATA%\TermFinale\` |
| Linux | `~/.local/share/TermFinale/` |

内含 `term_finale_pro.db`、`assets/`（解析出的图）、`logs/`、`debug/`（AI 原始输出与指标）、`.env`。
首次运行会从源码目录**复制**旧数据（不移动、不删除）。可用 `TERMFINALE_HOME` 覆盖。

## 项目结构

```
main.py              UI 主程序（CustomTkinter）
launcher.py          打包入口（崩溃日志兜底）
app/desktop/         主题 token + 组件库
services/            用例层：guide / review（不依赖 UI，可被 Web 复用）
core/
  paths.py           跨平台数据目录
  config.py          密钥与 .env
  logger.py          日志与异常钩子
  parser.py          文档解析
  parsing/figures.py 图形区域检测与渲染（矢量图也能出）
  generate/          大纲、组卷蓝图
  quality/qa.py      生成结果自动校验
  exporter.py        Markdown → 单文件 HTML
models/user_profile.py  紧迫度/压力模型
tests/               权重与维护单测
legacy/              已归档的旧实现（不删除）
```

## 测试

```bash
python -m tests.test_weights
python -m tests.test_maintenance
```

## 文档

- [`docs/CHANGES_v2.md`](docs/CHANGES_v2.md)：v2 重构改了什么、证据在哪
- [`docs/HANDOVER.md`](docs/HANDOVER.md)：交接清单（怎么跑、怎么验、别做什么）
- [`PRODUCT_SPEC.md`](PRODUCT_SPEC.md)：功能规格与质量验收标准
- [`ROADMAP.md`](ROADMAP.md)：分阶段施工计划与验收记录
- [`PROJECT_NOTES.md`](PROJECT_NOTES.md)：架构、隐形协议、已知问题清单

## 说明

- 生成内容由大模型产出，请以原始资料为准；讲义中每个知识点尽量标注源页码。
- 图片来自原始课件渲染，仅用于个人复习，请勿二次分发。

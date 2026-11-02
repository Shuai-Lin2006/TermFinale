# v2 重构变更摘要（10 轮，2026-11-02）

> 一句话：从「单文件 1395 行 + 页面 80% 空白 + 讲义没图 + 内容每次重写」，
> 变成「分层架构 + 可校验的生成流水线 + 能双击运行的安装包」。
> 全部改动在分支 `v2`，共 17 个提交；`main` 分支保留重构前原样。

## 按阶段看

| 阶段 | 之前 | 之后 | 证据 |
|---|---|---|---|
| **P1 地基** | 数据写在源码目录；打包后写进临时解压目录，重启即丢 | `core/paths.py` 统一用户数据目录；首次运行只复制不移动旧数据；WAL + timeout=15 | 迁移实测：DB 1 个 + 290 张图；`journal_mode=wal` |
| **P1 可观测** | 无日志、无原始输出，出问题无从查 | 文件日志 + 轮转 + sys/threading/Tk 三处异常钩子；每次生成的原始 Markdown 与指标落 `debug/` | `logs/app_*.log`、`debug/*.md` 实测生成 |
| **P1 架构** | UI、线程、数据库、生成逻辑全在 `main.py` | `services/` 用例层（零 tkinter）+ `core/` 纯逻辑；`main.py` 1395 → 1413 行但只剩 UI | 服务层可被 Web 端复用（为未来 Web 版留路） |
| **P2 图文** | 只认位图块，矢量图 0 张 | `core/parsing/figures.py` 把图形区域整块渲染成 PNG，按 y 坐标锚定回原位 | 32 页 PDF → **20 页 36 张图**，0.6s；第 12 页圆柱图从"没有"到"有" |
| **P3 内容** | 2 页一块，32 页出 16 个碎片章节；两次生成重合仅 10.4% | 先 AI 出大纲（章/必考点/篇幅），再逐章生成，prompt 注入"必须覆盖/前后章/篇幅" | 大纲 JSON 解析 + 坏输出回退 + 10 项质量校验全部离线通过 |
| **P3 压缩** | "精简"比"全量"还长 3% | 保命流改为结构性压缩（必背+公式卡+三步套路），不是砍知识点 | 单测锁定区间 600–2200 字/章 |
| **P4 复习** | 导图/文本逻辑两次生成，图文常对不上 | 一次生成「宏观架构 + 图谱 + 因果链 + 对照表」 | mock 产物同时含 mermaid / table / 因果链 |
| **P4 提取** | 2000 字硬切，图标签会被拦腰截断，漏页无法发现 | 按页打包 + 指纹去重 + 覆盖统计（页/块/有产出块） | 6 页 2 块零断裂，covereage=1.0 |
| **P4 组卷** | 让 AI 自由出题 | 蓝图（题型×数量×分值）+ 验卷（缺题/分值/重复/考点/公式/答案分区） | 正例 100 分通过；删一大题后正确报错 |
| **P5 权重** | `硬度×0.4 + 紧迫度×0.6`，临考课程全顶格（100/100/91） | 压力模型 `S=L/(1+L)`，并输出可执行建议 | 8 项单调性/边界/防饱和单测；旧 100/100/91 → 新 98.5/98.5/90.2 |
| **P6 UI** | 39 处裸颜色、下拉框整条蓝块、卡片文字被裁、仪表盘 80% 空白 | theme token + 9 个组件 + 仪表盘重做（指标/课程双列卡/今日建议） | 8 页截图逐页验证；U1/U3/U4/U5/U6/U8 已修 |
| **P7 打包** | 无依赖清单、无 spec、`.env` 不在包内 → 双击必崩 | `requirements.txt` + `TermFinale.spec` + `launcher.py` 崩溃日志 + 密钥外置 | `dist/TermFinale.app` 125MB，**实跑**：frozen=True、DB 加载、界面正常 |

**补记**：P0 遗留的「删课会删用户原件」在第 11 轮修复——删除逻辑改为只清理由本软件生成的产物，
`materials.file_path`（用户原始课件）不再触碰；已用模拟删除验证三件事同时成立：原件仍在 / 生成物已删 / DB 记录已清。

## 文件级变化

**新增（核心）**
```
app/desktop/theme.py          设计 token（亮/暗、间距、字体栈）
app/desktop/components.py     9 个复用组件
services/{task,guide_service,review_service}.py
core/paths.py  config.py  logger.py  maintenance.py  platform_utils.py  personas.py
core/parsing/figures.py
core/generate/outline.py  exam_builder.py
core/quality/qa.py
launcher.py  TermFinale.spec  requirements.txt  tools/{build,smoke}.py  tests/*
```

**归档（未删除）**：`legacy/ui_main_v0.py`、`legacy/text_exporter_v1.py`、`legacy/test_api_zhipu.py`

## 回滚

```bash
git checkout main     # 回到重构前
git checkout v2       # 回到重构后
```
另有 `_backup/termfinale_pre-v2_*.tar.gz` 快照。

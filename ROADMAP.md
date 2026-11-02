# TermFinale 重构路线图 v2.0

> 目标：从"能跑的 demo"变成"敢发给 100 个粉丝、能写进简历"的产品。
> 三端：macOS + Windows（首发），Web（预留）。
> 原则：**后端先行、每阶段可验收、任何时刻都能回滚**。

---

## 0. 工作纪律（高于一切）

| 纪律 | 具体做法 |
|---|---|
| 不删代码 | 废弃文件 `git mv` 到 `legacy/`，不物理删除 |
| 可回滚 | 每阶段一个 commit；重构前打 zip 快照到 `_backup/` |
| 可验证 | 每次改完 `py_compile` + 冒烟脚本；关键阶段跑 11 页截图 |
| 单点推进 | 一次只动一个层次，不同时改解析和 UI |
| 上下文节制 | 每轮只读当前要改的文件；决策写进本文件，不靠记忆 |
| 保护密钥 | 不 add `.env`，不改 git 历史，不读密钥明文 |

---

## 阶段总览

| 阶段 | 主题 | 主要产出 | 验收 | 预估 |
|---|---|---|---|---|
| **P0** | 安全基线 | git 分支 + zip 快照 + 回归脚本 | 一键还原可用 | 10 min |
| **P1** | 地基 | `core/paths.py`、`core/logger.py`、`services/`、`main.py` 变薄 | 数据落用户目录；11 页行为不变；日志有栈 | 1 天 |
| **P2** | 图文完整性 | `core/parsing/figures.py`、结构化 parser、`[[[FIG:]]]` 链路 | 图检出 ≥90%、位置准 ≥95%、带图题 100% 有图 | 1.5 天 |
| **P3** | 内容质量 | `generate/outline.py`、`quality/qa.py`、prompt 重构 | 两次重合 ≥60%、精简 ≤50%、10 项校验全绿 | 1.5 天 |
| **P4** | 复习模式 | 逻辑分析合并、提取两阶段、组卷矩阵、三套模板 | 覆盖报告、超纲 0、卷头答题卡齐 | 2 天 |
| **P5** | 权重与产品化 | `user_profile` 重构、速览页、倒计时、错题本 | 单调性单测通过；速览页可生成 | 1 天 |
| **P6** | UI 重建 | `theme.py`、`components.py`、页面栈、逐页重写 | 新截图对比；Windows 不崩排版 | 2 天 |
| **P7** | 打包分发 | requirements、PyInstaller spec、干净机测试 | 双击可运行、崩溃有日志 | 1 天 |
| **P8** | Web 预留 | 服务层异步化、FastAPI 骨架（后置） | 接口不依赖 tkinter | 后置 |

---

## P1 拆解（本轮开工）

### P1a 路径与日志 ✅ 已完成（2026-11-02，commit 541c8e2）

1. `core/paths.py`：统一数据目录
   - macOS `~/Library/Application Support/TermFinale`
   - Windows `%APPDATA%\TermFinale`
   - Linux `~/.local/share/TermFinale`
   - 可用 `TERMFINALE_HOME` 覆盖（测试/绿色版）
   - 首次运行从源码目录**复制**旧 DB 与 `assets_images`（不移动、不删除）
   - 子目录：`assets/`、`logs/`、`debug/`、`outputs/`；DB 在根目录
   - 用户目录不可写时自动回退到项目内 `.termfinale_home`（不崩溃）
2. `core/logger.py`：UTF-8 文件日志 + 5MB 轮转 + sys/threading/Tk 回调异常钩子
3. 接线：`database.py`（WAL + timeout=15）、`parser.py`、`exporter.py`、`main.py`

**验收结果（实测）**
- [x] 迁移成功：DB 复制 1 个 + assets 复制 290 个文件，3 门课程完整
- [x] `logs/app_2026-11-02.log` 正常落盘（含启动日志与 init_db）
- [x] SQLite 实测 `journal_mode=wal`
- [x] 启动冒烟测试通过：UI 正常、课程列表 3 条
- [ ] 打包模拟（`sys.frozen=True` 单测）留待 P7
- [ ] 11 页截图回归留待 P1b 一起做

### P1b 服务层抽离 + 已知 bug ✅ 已完成（2026-11-02，commit 871f300）

1. `services/task.py`：`ProgressEvent` / `RunResult` / `dump_debug`
2. `services/guide_service.py`：`run_guide(course, mode, persona, core_ratio, lang, on_progress, stop_event)`
3. `services/review_service.py`：`run_review(course, task_type, text, **params)`
4. `main.py` 只做：收集参数 → 调服务 → `after()` 桥接进度；抽 `_show_progress_page` / `_on_service_progress`
5. 修 B1 人设 key / B2 视觉模型名 / B3 打开文件 / B4 重复材料 / B5 标题双前缀 / B6 补图位置
6. UI 五个刺点（U1/U4/U5/U6/U8）→ **改到 P6 随 UI 重建一起做**（避免在即将废弃的代码上花两遍功夫）

**验收结果（实测）**
- [x] `main.py` 1401 → **1253 行**（剩余基本是纯 UI，P6 会继续降）
- [x] 服务层零 tkinter 依赖；`services/` 可被 Web 端复用
- [x] 原始 Markdown + 指标落盘 `debug/`
- [x] B1：5 个人设全部映射到 `PERSONAS` 有效 key（"阳光小哥哥"可选）
- [x] B2：`qwen-vl-max`，可用 `QWEN_VL_MODEL` 覆盖
- [x] B3：跨平台 `open_path()`，不再依赖 Edge
- [x] B4：编辑资料不再累加重复材料
- [x] B5：实测 `第 1 章：刚体力学基础`（无双前缀）；英文 `Chapter 1: Rigid Body`
- [x] B6：丢图补在章末「📷 配图」区
- [x] 8 个页面截图回归通过（`/tmp/tf_probe/regress`）

---

## P2 图文完整性（用户最痛）

1. ✅ `core/parsing/figures.py`：`get_drawings` + `get_image_info` → 过滤整页/页眉页脚/图标/纯色条 → 聚类 → 渲染 PNG
   - 阈值：面积 0.4%~45%、边长 ≥24pt、长宽比 0.15~6.5、纯色剔除、dHash 去重（汉明 ≤3）
   - 图注优先取页面原文（"图3-1"），否则视觉模型；视觉判定"无内容"→ 丢图
2. ✅ `parser.py`：图按 `bbox.y0` 锚定插入该页文本流的正确位置（不再放页尾）
3. ⏳ `figures.json` 清单：当前直接复用 `[[[IMAGE: 文件名 | 图注]]]` 协议，清单留给 P4 题图绑定
4. ✅ `exporter.py`：原有 `[[[IMAGE:]]]` 链路直接可用（base64 内联），无需新协议
5. ⏳ 题图绑定：提取 prompt 已要求 AI 原样保留标记；**按题目精确绑定留到 P4**
6. ⏳ 页级结构化（标题层级/表格/公式/双栏）→ 移到 P3 与解析质量一起做

**验收结果（实测，离线模式）**
- [x] 你那份 32 页纯矢量 PDF：**17 页命中、31 张图**、耗时 0.4s
- [x] 装饰图过滤：章节图标（放大镜 139×139）、整页版式块（715×330）、纯灰条、页眉横幅全部被剔除
- [x] 公式块（矢量文字）**有意保留**——它们是文本层丢失的信息，转图反而是兜底
- [x] 位置锚定：第 5 页样例中图标签出现在 `s / O / i=1` 等标签之间，符合原文版式
- [x] 端到端：parser 产出 31 个标签 → exporter 内联 base64 成功（16.7KB 图，HTML 33KB）
- [x] 离线测试开关 `TERMFINALE_DISABLE_VISION=1`（不烧 API）
- [ ] 视觉模型在线判定装饰图（代码已接，需真跑一次验证）
- [ ] 图文重叠严重页的裁切精度调优

---

## P3 内容质量

1. `generate/outline.py`：一次生成大纲（章/考点/重要度/预估字数）
2. 按大纲逐章生成，prompt 注入前后章摘要
3. 三轴控制：覆盖度 100% / 展开度 30%~100% / 形式密度
4. `quality/qa.py`：10 项校验（见 PRODUCT_SPEC §5）
5. `finish_reason=="length"` → 续写或丢弃
6. 稳定性：同一输入两次生成重合 ≥60%

---

## P4 复习模式

1. 逻辑分析合并：一次产出「图 + 因果卡 + 对照表」，两视图切换
2. 提取：两阶段（扫描→展开）+ 指纹去重 + 逐页覆盖报告 + CSV/Anki
3. 组卷：考点×题型×分值矩阵 + 覆盖率/超纲/重复/分值自检
4. 模板：讲义 / 试卷 / 图谱 三套独立 HTML

---

## P5 权重与产品化

1. 可完成性模型（PRODUCT_SPEC §8.6）+ 单调性单测
2. 考前 1 页速览（A4）
3. 倒计时 + 复习进度 + 错题本
4. 缓存清理、死代码入 `legacy/`

---

## P6 UI 重建

1. `app/desktop/theme.py`（token 纯数据）、`components.py`（Card/StatTile/Toast/...）
2. 页面栈 + 局部刷新，去掉 6 处全量销毁
3. 先出 HTML 原型 → 你确认 → 再移植
4. 字体回退栈、SVG 图标、深色模式、高 DPI

---

## P7 打包分发

1. 锁 Python 3.12，`requirements.txt`
2. PyInstaller spec（customtkinter data、fitz hiddenimports、图标）
3. 干净机双击测试；崩溃日志可回传

---

## 风险登记

| 风险 | 缓解 |
|---|---|
| 迁移旧数据失败 | 只复制不移动；失败则继续用旧路径并告警 |
| 解析重构导致产物崩 | 保留旧 `parser.py` 为 `legacy/parser_old.py`，可回切 |
| AI 质量不可控 | 先建指标与样本集，改一次测一次 |
| 上下文丢失 | 本文件 + PROJECT_NOTES + PRODUCT_SPEC 三件套 |
| macOS/Linux 权限 | 测试用 `TERMFINALE_HOME` 指向工作区 |

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

### P1a 路径与日志
1. `core/paths.py`：统一数据目录
   - macOS `~/Library/Application Support/TermFinale`
   - Windows `%APPDATA%\TermFinale`
   - Linux `~/.local/share/TermFinale`
   - 可用 `TERMFINALE_HOME` 覆盖（测试/绿色版）
   - 首次运行从源码目录**复制**旧 DB 与 `assets_images`（不移动、不删除）
   - 子目录：`db/`、`assets/`、`logs/`、`debug/`、`outputs/`
2. `core/logger.py`：UTF-8 文件日志 + 5MB 轮转 + 全局/线程/Tk 回调异常钩子
3. 接线：`database.py`、`parser.py`、`exporter.py`、`main.py`

**验收**
- [ ] 启动后课程数据仍在（迁移成功）
- [ ] `logs/app_YYYY-MM-DD.log` 有内容
- [ ] 打包模拟（`sys.frozen=True` 单测）路径落用户目录
- [ ] 11 页截图无异常

### P1b 服务层抽离 + 已知 bug
1. `services/task.py`：`Task(id, kind, status, progress, artifacts, metrics)`
2. `services/guide_service.py`：搬 `run_backend_task`，签名 `run(course, params, on_progress)`
3. `services/review_service.py`：搬 `run_generation_task`
4. `main.py` 只做：收集参数 → 调服务 → `after()` 桥接进度
5. 修 B1 人设 key / B2 视觉模型名 / B3 打开文件 / B4 重复材料 / B5 标题双前缀 / B6 补图位置
6. 修 U1 蓝块下拉 / U4 文字裁切 / U5 双复选框 / U6 按钮对齐 / U8 按钮对比度

**验收**
- [ ] `main.py` < 900 行
- [ ] 同样输入产物结构与改前一致
- [ ] 六个 B 类问题逐条复测通过

---

## P2 图文完整性（用户最痛）

1. `core/parsing/figures.py`：`get_drawings` + `get_image_info` → 过滤整页/装饰 → 聚类 → 渲染 300dpi
2. `parser.py`：页级结构化（标题层级/表格/公式/双栏），图按 `y` 锚定进文本流
3. `figures.json`：`{id, page, bbox, file, caption, phash}`
4. `exporter.py`：`[[[FIG:id]]]` → 原位内联；缺图时整页兜底
5. 题图绑定：题目 `source_page` → 取该页图（距离优先，整页兜底）

**验收**：图检出 ≥90%；位置准确 ≥95%；抽 10 道带图题 100% 有图。

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

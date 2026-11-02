# 交接清单（给自己，也给下一个协作者）

## 1. 三条命令

```bash
# 开发运行
python main.py

# 改完必跑（30 秒，不联网、不花钱）
python tools/smoke.py

# 打包
python tools/build.py
```

## 2. 改代码前先读什么

按这个顺序，10 分钟能恢复全部上下文：

1. `ROADMAP.md` —— 现在做到哪、下一步是什么
2. `PROJECT_NOTES.md` —— 架构、**隐形协议**、已知问题（尤其第 7 节）
3. `docs/CHANGES_v2.md` —— 这一轮到底改了什么、为什么

## 3. 隐形协议（改错就白屏/丢图）

| 协议 | 生产者 | 消费者 |
|---|---|---|
| `[[[IMAGE: 文件名 \| 图注: xxx]]]` | `parser.py` / `figures.py` | `exporter.py` |
| `[[名词 \| 解释]]` | `ai_engine` prompt | `exporter.py` |
| `## 核心考点：标题` | prompt 结构 | `exporter.py`（改写为「第 N 章」） |
| `$$...$$` / `$...$` | prompt | `exporter.py`（占位保护） |
| `@@KEYWORD{n}@@` 等占位符 | `exporter.py` | `exporter.py`（先恢复后清理） |
| 人设 key = `PERSONAS` 的键 | `core/personas.py` | `ai_engine` / `OUTROS` |

## 4. 数据在哪

| 系统 | 目录 |
|---|---|
| macOS | `~/Library/Application Support/TermFinale/` |
| Windows | `%APPDATA%\TermFinale\` |
| Linux | `~/.local/share/TermFinale/` |

内含 `term_finale_pro.db`、`assets/`（解析图）、`logs/`、`debug/`（AI 原始输出+指标）、`.env`。
测试时可用 `TERMFINALE_HOME=./_backup/home_test` 指向临时目录，不污染真实数据。

## 5. 已知限制（不是 bug，是没条件做）

| 项 | 原因 | 怎么补 |
|---|---|---|
| Windows 构建未验证 | 需要 Windows 机器 | 同一 `TermFinale.spec`，`python tools/build.py` |
| 内容质量未真实跑 | 需授权 API（约 ¥0.3） | 跑两次生成，对比 `debug/` 里的指标 |
| 深色模式 | 需把上百处颜色改成运行时取值，风险高 | theme 已备好暗色板，可增量切 |
| SVG 图标 | 替换 68 个 emoji，影响面广 | 单独排期 |
| 页面栈 | 内部优化，用户不可见 | `clear_ui` 逐步替换为局部刷新 |

## 6. 常见问题

| 现象 | 原因 | 处理 |
|---|---|---|
| 双击没反应 | 启动即崩 | 看用户目录 `logs/crash.log` |
| 提示"未配置 API Key" | 缺 `.env` | 按 `docs/API_KEYS.md` 放到用户目录 |
| 图片全是"第 N 页配图" | 视觉模型未配置或报错 | 配 `DASHSCOPE_API_KEY`，或接受兜底文案 |
| `database is locked` | 并发写 | 已开 WAL + timeout=15；仍有则查是否多个实例 |
| 打包失败 `PermissionError` | PyInstaller 写 `~/Library` | `tools/build.py` 已把缓存指到项目内 |
| 生成的讲义很大（几 MB） | 图片 base64 内联 | 预期行为；后续可加外置+懒加载 |

## 7. 下一步建议顺序

1. **真实 API 验收**：用同一份 PDF 跑「全量 / 精简」各一次，看 `debug/*.json` 里的
   `qa_chapters`、`images_expected`、`elapsed_s`，再人工抽 5 个必考点确认没漏。
2. **Windows 打包**：在 Windows 上建 venv → `pip install -r requirements.txt` →
   `pip install pyinstaller` → `python tools/build.py`。
3. **考前 1 页速览**：复用 `exporter`，把「必背 + 公式 + 易错」压成 A4 单页。
4. **深色模式**：先把 `main.py` 的 `BG_COLOR` 等换成 `theme.palette().bg`，
   再在设置里加切换 → `theme.set_dark()` + 重绘当前页。
5. **Web 版**：`services/` 已是零 tkinter，接 FastAPI 时只需把 `on_progress` 桥到 SSE。

## 8. 不要做的事

- 不要删 `legacy/`（那是回查历史用的，删了也没收益）
- 不要把 `.env` 提交进 git（历史上已经泄露过，别再加重）
- 不要在没跑 `tools/smoke.py` 的情况下说"改好了"
- 不要直接大段重写 `main.py`（它仍承载全部 UI，一次只动一个页面）

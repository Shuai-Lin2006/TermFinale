# TermFinale 夜间交付报告

> 时间：2026-11-08 01:10（Asia/Shanghai）
> 目标：数据安全 → 内容可信 → 深色 premium UI；不重置用户数据、不删原资料、不推送 GitHub。
> 当前状态：**可本机演示的 beta**；不是“全部完成”。未完成项在最后，全部可验证。

---

## 1. 早上先做这一件事

Electron 窗口如果还开着旧页面，按 **Cmd+R 刷新一次**。后端已在 8903 换成新代码，页面刷新后会拿到新的 HttpOnly 会话 cookie。

- 真实数据：`/api/courses` 只返回 **1 门**正式课；46 门 BATCH/TEST/FINAL 测试课默认隐藏。
- 如果看到“本地服务未启动”：终端里执行
  ```bash
  cd /Users/lan/PycharmProjects/TermFinale
  TERMFINALE_WEB_PORT=8903 .venv/bin/python server/app.py
  ```
  或直接重开 TermFinale。

---

## 2. 今夜完成（按证据）

### 2.1 数据安全

- 数据库备份：`~/Library/Application Support/TermFinale/backups/night_20261107_234346.db`（47 课 / 368 生成物，可独立打开）。
- `courses.is_test` 迁移：46 门测试课 / 1 门正式课；列表、概览、资料、错题、练习默认过滤，`?include_test=true` 才返回全量。
- `/api/reset` 必须 `{"confirm":"DELETE-ALL"}`；先自动备份；只删上传副本与生成物，**不删桌面/Documents 原资料**。
- `/api/backup`、`/api/backups`；设置页“立即备份”可直接调用。
- 日志与异常钩子：`setup_logging()`、`install_exception_hooks()` 在 import 时执行。
- 本地 API 鉴权：
  - 页面首次加载下发 HttpOnly `SameSite=Strict` 的 `tf_token`；
  - `/api/*`（`/api/health` 除外）无 token → **403**；
  - CORS 只允许 `http://127.0.0.1:<port>` / `http://localhost:<port>`；
  - 跨站 `Origin` → **403**。
- 实测：无 cookie `/api/courses` → 403；页面后带 cookie → 200；`Origin: evil` → 403。

### 2.2 内容可信

| 项 | 结果 |
|---|---|
| 85 页 PPT | **85/85 页**，按页码排序；第 74 页明确标 `[本页 OCR 未识别出文字]` |
| 公式 | 4 个 KaTeX 节点，0 残余 `$`；`<`/`&` HTML 转义 |
| 页码校验 | `【《有机化学【蜂考系统课】.pdf》第 5 页】` 能识别（不再被文件名里的 `【】` 搞瞎） |
| 覆盖率 | 改为按页分母；10 页只引 6 页 → 0.6 + 缺页 `[7,8,9,10]` |
| 171 页真实提取 | 171 页 / **169 引用 / 98.8%** / 仅缺封面 2 页；140,259 字 / 210 考点 / 6.6 分钟 + 逐页补提取 |
| 长文档 | 删掉 10k 无条件截断；1001 页均衡 10 章；160 页概览 2 次调用 |
| 老师重点 | 只考/必考/不考/页码/基团；8 页高数 8/8 引用、0 超范围；化学 10 基团通过 |
| 1001 页真实概览 | 1001 页 / 7 章 / 抽样 33 页 / **35.9s** / 15,725 字 / `qa_ok=true`（不是逐页提取） |
| 真实试卷 | FINAL高数 4/2/2=100 分，8 题 8 答案，1 次通过，15.7s，`validation.ok=True` |
| 试卷清洗 | 修掉“单题型输出答案+第二套题”导致误判通过；多答案分区/答案后混题 → 硬失败 |
| 引用修复 | 3 条漏出处考点用原文 2-gram 匹配补回真实页码；匹配不到不编 |

171 页首轮 156/171（91.2%），缺页 `[1,2,26,34,36,49,121,136,139,144,155,158,159,164,167]`；逐页补提取把 26/34/36/49/121/136/139/144/155/158/159/164/167 全部补回，**169/171 = 98.8%**，只剩 1、2 封面/群号。补提取已写进正式流程（最多 16 页），补不出来仍报缺页；**没有包装成 100%**。

### 2.3 UI（深色 premium 方向）

- 新 token 层 `web/assets/premium.css`：近黑画布、薄荷强调、衬线标题、等宽标签、浅色象牙主题。
- 首页：今日主卡 + 3 指标 + 最近生成 + 我的课程；修掉 `recentGrid` 空指针和假 demo 数据。
- 复习计划：今日目标 / 预计用时 / 进度 + 按课程 + 下一步。
- 课程页 / 课程详情 / 资料统计 / 笔记 / 练习 / 设置：premium 卡片、空态、备份入口、真实删除。
- 生成工作台：老师重点 + 任务约束（页码范围、禁止词、违规即失败、试卷答案开关）；套数/校验顺序/SSE 错误态修复。
- 阅读页：正文优先、封面收窄、TOC 无 h2 用 h3 兜底、工具收进“⋯”、PDF 走后端、去掉假“编辑”。
- 响应式：1440 / 1024 / 900 三档；900 以下 rail 隐藏时补移动 tab。
- 浅色主题：首页、复习计划已截图验证。
- 版本统一 **0.3.0**（build/spec/Electron/server）。

### 2.4 测试与 CI

- `python -m unittest discover -s tests` → **97 项全绿**。
- 新增：`test_security.py`（4）、`test_exam_engine.py`（5）、答案覆盖/多答案分区/引用修复等。
- CI：`unittest discover` 全量；pyflakes 覆盖 `server/app.py`、`desktop.py`、`tools/build.py`；server import smoke。
- 本机验证过 `import server.app`；GitHub Actions 尚未在远端跑（没有 push）。

---

## 3. 证据文件

| 内容 | 路径 |
|---|---|
| 夜间详细日志 | `docs/NIGHT_SHIFT.md` |
| 审计问题清单 | `docs/AUDIT_2026-11-07.md` |
| 发布计划 | `docs/RELEASE_PLAN.md` |
| 总清单 | `docs/MASTER_CHECKLIST.md` |
| 真实试卷 md | `docs/evidence/exam_real2.md` |
| 真实试卷日志 | `docs/evidence/exam_real2.log` |
| 171 页修复后（91.2%） | `docs/evidence/extract171_repaired.md` |
| 171 页逐页补提取（98.8%） | `docs/evidence/extract171_filled.md` |
| 171 页补提取日志 | `docs/evidence/fill171.log` |
| 1001 页真实概览 | `docs/evidence/guide1001.md` / `guide1001.log` |
| 171 页日志 | `docs/evidence/extract171.log` |
| UI 截图 | `docs/screenshots/`（见下） |
| README 预览图 | `docs/screenshots/dashboard.png` / `review.png` / `training.png` |

关键截图：

- `final_dashboard.png`：今日工作台（深色）
- `dash_light2.png`：浅色首页
- `dash_1024b.png`：1024 窄窗
- `dash_900b.png`：900 移动导航
- `plan2.png` / `plan_light.png`：复习计划深/浅
- `course_detail_v2.png`：课程详情
- `practice2.png`：练习
- `settings2.png`：设置
- `notes_v2.png`：笔记
- `materials_stats_v2.png`：资料统计
- `auth_generate.png`：生成工作台 + 老师重点
- `reader4.png`：阅读器
- `welcome2.png`：首次启动

---

## 4. 未完成 / 阻塞（不粉饰）

1. **171 页覆盖 98.8%**，只剩封面/群号 2 页；逐页补提取已进流程。若要 100%，需把封面也建索引（不建议为此调模型）。
2. **1001 页已真实跑概览**（7 章 / 抽样 33 页 / 35.9s / qa_ok），但没有跑 1001 页**逐页提取**（约 250 块，成本高）；概览模式的覆盖率已单独标记，不再伪装成逐页覆盖。
3. **Windows 构建/签名**未做：需要 Windows 机器 + 账号；`docs/BUILD_WINDOWS.md` 仍是待执行。
4. **macOS 签名/公证**未做：需要 Developer ID 证书与 App Store Connect 配置。
5. **PDF 导出**依赖本机 Edge/Chrome headless；没有内置渲染器。Word 导出是实验性。
6. **UI 不是终版**：`upload.html`、`welcome.html` 基本沿用旧结构（已套主题）；阅读页正文排版还可继续打磨；AI 抽屉/关键词弹窗只做了公式修复。
7. **测试数据还在库里**：46 门测试课只是隐藏，没有删；用户若要彻底清掉，需单独确认。
8. **GitHub 未推送**：本地 14+ 个提交；推不推、仓库名、release 文案由你决定。
9. **CI 未在 GitHub 跑过**；本机 97 项通过不等于三平台通过。
10. **API token 鉴权**后，外部 curl / 旧脚本要带 cookie 或 `X-TF-Token`；没有对外 API 文档。

---

## 5. 早上验收命令

```bash
cd /Users/lan/PycharmProjects/TermFinale
.venv/bin/python -m unittest discover -s tests          # 97 项
.venv/bin/python -m pyflakes server/app.py core services models tools/build.py

# 鉴权 + 数据
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8903/api/courses      # 403
curl -s -c /tmp/tf_c.txt -o /dev/null http://127.0.0.1:8903/dashboard.html
curl -s -b /tmp/tf_c.txt http://127.0.0.1:8903/api/courses | head -c 300        # 1 门课
```

GitHub 提交建议（你自己操作）：

```bash
cd /Users/lan/PycharmProjects/TermFinale
git log --oneline -15
git status
# 确认 .env 没有被跟踪
git remote -v
git push origin main
```

---

## 6. 一句话总结

今夜把“会骗人的覆盖率、丢页、公式转义、老师重点、试卷结构、答案自洽、本地 API 裸奔、UI 玩具感”这几件事都往下推了一大截，并且留下了可复现的证据；**171 页已到 98.8%，但 1001 页真跑、Windows/签名仍未完成**，所以它现在是一个“能演示、能继续打磨的 beta”，不是最终发布版。下一轮优先：1001 页真跑、上传/欢迎页终版、macOS 签名、Windows 构建。

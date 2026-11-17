# 最终测试清单（2026-11-10）

## 启动

```bash
cd /Users/lan/PycharmProjects/TermFinale
TERMFINALE_EMBEDDING=api PYTHONPATH=. .venv/bin/python -m tfv2.api.product_app
```

打开：http://127.0.0.1:8907/

健康检查：`/api/health` 返回 `{"ok":true}`。

## 先看 6 份 PDF

- deliverables/01_电路讲义.pdf
- deliverables/02_高等数学讲义.pdf
- deliverables/03_C语言讲义.pdf
- deliverables/04_医学解剖讲义.pdf
- deliverables/05_电路12题.pdf
- deliverables/06_跨学科小样讲义.pdf

重点看：目录、图是否完整、公式/中文、页码、题目重复。

## 功能路径

1. 首页 → 课程 → 资料 → 讲义阅读器；刷新后仍正常。
2. “AI 讲义”新建一份；确认进度、完成、PDF/Word。
3. “多资料”上传 2 份；确认权重和目录。
4. 提取：考点/名词/原题/思维导图/逻辑分析/试卷；确认状态 validated/rejected 合理。
5. 出卷：mock 能生成；original 不逐字会 rejected，这是正确行为。
6. 做题/错题/笔记/复习；确认保存后刷新不丢。
7. Agent：规划、执行、失败重规划、工作流保存/加载、目标。
8. 设置：中/英/繁体、主题、移动端宽度。
9. 导出：PDF 用浏览器打印；坏 PDF 会被 500 门禁拦住。
10. 备份：`/api/backup` 下载 ZIP，可解开看到 sqlite。

## 已知边界（不是测试失败）

- 30 张 VLM 审计未跑满，外部视觉 API 会超时；
- Job 是“重启重跑/失败重试”，不是断点续传；
- 医学/地图只走原图，不生成；
- 3D 是 MuJoCo 单/多刚体，不是通用 CAD；
- 打包/签名/人工 truth 未做。

## 怎么反馈

```text
文件/页面：
问题：
期望：
严重度：blocker / major / minor
```

不要只说“这块不好”，给到页/题/图，我才能直接改。

# 第 21 轮完成报告：路由去重 + 旧路由重定向（2026-11-14）

## 做了什么

- 新增 canonicalHash：
  - #/home、#/index -> #/
  - #/courses -> #/library
  - #/drill -> #/practice
  - #/exams -> #/exam
  - #/reader/* -> #/read/*
  - #/course/:key/tools -> #/workbench?course=:key
- onboarding 阶段也做 canonical 化：用户点旧链接，不会先停在旧地址。
- 删除课程页重复的“本课内容工具”Tab；内容工具只保留侧栏一个入口。
- app.js 版本号 20261112-r2 -> 20261114-r4，避免旧缓存继续用旧路由。

## 验收（Playwright + Edge）

7 条旧路由全部重定向成功：

| 旧路由 | 结果 |
|---|---|
| #/home | #/ |
| #/index | #/ |
| #/courses | #/library |
| #/drill | #/practice |
| #/exams | #/exam |
| #/course/demo/tools | #/workbench?course=demo |
| #/reader/abc | #/read/abc |

- 课程页重复的“本课内容工具”入口已删；
- 本轮不改视觉样式。

## 如实说

- 路由清单是从当前 app.js 盘点，不是穷举所有历史外部链接；
- #/course/:key/tools 带 query 时会保留 query；其他未知旧路径仍回 404；
- 验证用本机 Edge，不是所有浏览器。

## 下一步

第 22 轮：学科侧栏 + 首页学科卡片。
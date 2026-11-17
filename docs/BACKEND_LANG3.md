# 三语言实测（2026-11-15）

## 纠正

系统实际支持：

- 简体中文（zh）
- 繁體中文（hant）
- English（en）

不是四语言；旧计划里的“四语言”已纠正。

## 实测

10 页模电（30–39）分别生成 hant / en：

| 语言 | 结果 |
|---|---|
| 繁體中文 | gate/content/pdf/language 全 true；review（audit 未跑） |
| English | gate/content/pdf/language 全 true；review（audit 未跑） |

- 繁體 PDF：data/artifacts/gen_20261115_144411_810ad7/lecture.pdf
- English PDF：data/artifacts/gen_20261115_142848_e3b857/lecture.pdf
- Word 已导出：
  - gen_20261115_144411_810ad7.docx
  - gen_20261115_142848_e3b857.docx

## 修掉的问题

1. scoped 生成引用范围外页码（23）直接崩溃：
   - 新增 _clamp_page_refs，把引用钳制到当前 scoped 页数；
2. 繁體混简体：
   - 课程名、节标题、目标/术语/自测、页脚文件名全部转换；
3. 繁體目录硬编码“第…节”：
   - 改为“第…節”。

## 还未做

- 10 页语言稿没有 coverage audit，仍是 review；
- 100 页只做了简体，未做三语言全量；
- Word 只验证能导出，未逐页检查公式/图。

## 测试 / 余额

- **537 项测试通过**；
- 余额：**¥99.94**；
- Mac 可用：**92G**；
- T9 可用：**869G**。
# 2 页结构化闭环：通过（2026-11-15）

## 结果

- 范围：150–151，2 页
- 1 节
- 13 个结构化 block + 4 个缺失点补充
- 事实：20
- 初始映射：15/20
- 补 4 条后：**20/20**
- PDF：LaTeX，3 页
- gate/content/PDF/language：全 true
- audit：**2 covered / 0 partial / 0 missing**
- status：**delivered（可读）**

## 过程

1. Docling 2 页文本；
2. DeepSeek 返回空；
3. 换 qwen-max；
4. 发现 Qwen max_tokens 上限 8192，客户端截断；
5. 生成 9 个结构化 block，映射 15/20；
6. 对缺 4 条逐条补解释；
7. 映射 20/20；
8. 组装 LaTeX PDF；
9. audit 2/2 通过。

## 意义

- 第一次完整闭环：解析→事实→成节→PDF→audit；
- 失败单元缩到“单条事实”；
- 不是靠 100 页堆出来。

## 尚未做

- 10 页全量；
- 50/100 页；
- 三语言/UI。

## 10 页扩展结果

- gen_struct10_20261115
- 5 节、LaTeX、10 页、gate 全过
- 每节事实映射宣称 100%
- audit：第一次 1 covered / 6 partial / 3 overview；补 31 点后 4 covered / 3 partial；再补后 **3 covered / 4 partial**
- status review，不合格，非收敛

结论：2 页通过不能自动扩到 10 页；审计口径/成节组织仍有问题。

## 测试 / 存储

- 543 项测试通过
- token 无上限
- Mac 86G
- T9 858G
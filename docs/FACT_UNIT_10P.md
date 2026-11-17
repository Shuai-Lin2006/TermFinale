# 10 页事实单元（2026-11-15）

## 结果

- Docling 10 页文本；
- 清洗后 45 条事实；
- 每条单独生成 2–3 句解释；
- 本地映射：**45/45**
- coverage：**1.0**
- 耗时：19.5s
- 文件：data/golden/fact_unit_10p.json

## 样本

- 参考电流、晶体管状态判断解释可读；
- 但公式 OCR 仍有错误：I5 应为 Is，Is=Is 重复；
- 事实层通过，不代表讲义成品通过。

## 意义

- 这是第一次在 10 页上做到事实 100% 映射；
- 失败单元从“整节”缩到“单条事实”；
- 还没有组装成 5 节/PDF，也没有 audit。

## 当前总体

- 第一梯队 48%，差 52%；
- 10 页事实层通过，不等于 10 页交付；
- 下一步组装 PDF，再 audit。

## 组装结果

- artifact：gen_fact10_20261115
- 5 节、45 个事实 block
- LaTeX PDF：7 页
- gate/content/PDF/language：全 true
- audit：**1 covered / 5 partial / 1 missing / 3 overview**
- status：review，不合格

## 结论

- 事实映射 45/45 只证明“每条事实都有 block”；
- 不证明讲义讲清了；
- 当前事实 block 是“事实+解释”，缺少成节组织和上下文；
- 10 页仍未通过，不能扩 50/100。

## 未接

- Marker 安装失败；
- MinerU 未接；
- UI 未接。
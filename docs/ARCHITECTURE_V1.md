# 架构升级 V1（2026-11-15）

## 已完成

- 统一 `CanonicalDocument`：page_count / facts / plans / status / issues；
- `Fact`：fact_id、page、kind、text、source_span、confidence；
- `SectionPlan`：plan_id、页码范围、fact_ids；
- 覆盖规划：贪心按页邻接，每条事实只进一个计划；
- 槽位生成：每个 fact_id 必须被一个 block 消费，缺一条 partial；
- 单条重试：只重跑缺失 fact_id；
- 10 页 Docling：106 条事实、7 个计划、coverage 1.0、validated；
- 2 页槽位：23 条事实，先 22/23 partial，补 `p1-2` 后 23/23 validated；
- 测试：548 通过。

## 文件

- tfv2/canonical/model.py
- tfv2/canonical/pipeline.py
- tfv2/canonical/generate.py
- tools/canonical_demo.py
- tools/slots_2p.py
- tests/test_canonical_pipeline.py
- tests/test_slot_generation.py

## 下一步（未做）

- 解析器接口：Docling/MinerU/Marker 统一 parse；
- 事实去重/合并/类型校正；
- 槽位生成接 PDF/UI；
- 四模块读同一文档；
- 缓存/编排器。

## 边界

这是地基，不是第一梯队；还没有接生成渲染、UI、整书、基准。
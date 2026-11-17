# 架构升级 V2（2026-11-15）

## 新增

- `DocumentParser` 协议：Docling/MinerU/Marker 统一 `parse(source) -> PageLedger`；
- `DoclingStructureParser` 适配器；
- `CanonicalOrchestrator`：解析→事实→计划，磁盘缓存；
- `ModuleResult` 合同：validated/partial/rejected、items、coverage、evidence、issues；
- `gate()` 本地验收，不依赖模型 audit；
- 10 页实测：106 facts、7 plans、coverage 1.0、validated；
- 缓存第二次命中，facts 相同；
- 测试：551 通过。

## 文件

- tfv2/canonical/parsers.py
- tfv2/canonical/contracts.py
- tfv2/canonical/orchestrator.py
- tests/test_canonical_architecture.py
- tools/orchestrator_demo.py

## 下一步（未做）

- 事实去重/类型校正；
- 槽位生成接 PDF/UI；
- 四模块读同一文档；
- 编排器接全量任务；
- 解析器接 MinerU/Marker。

## 边界

地基完成，不是第一梯队；剩余 44% 仍是整书、基准、UI 完整流程、题量。
# 架构升级 V3（2026-11-15）

## 已完成

- 统一 CanonicalDocument；
- 106 条 10 页事实；
- 7 个覆盖计划；
- 槽位生成：106/106 blocks；
- 首批 102/106，缺 4 条；
- 逐条重试 4 条后 coverage 1.0；
- 解析器/合同/编排器/缓存；
- 测试：551 通过。

## 关键结果

`data/golden/slots_10p_fixed.json`

```json
{"facts":106,"blocks":106,"missing":[],"coverage":1.0,"status":"validated"}
```

## 下一步（未做）

- 槽位 block 渲染成 PDF/UI；
- 四模块读同一 CanonicalDocument；
- 事实去重/类型校正；
- MinerU/Marker 接入；
- 整书/基准。

## 边界

10 页槽位 validated，不等于 10 页成品通过；还没渲染和人工验收。
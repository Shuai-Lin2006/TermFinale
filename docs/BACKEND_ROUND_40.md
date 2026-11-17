# Backend Round 40：页码范围接入生成入口（2026-11-15）

## 新增

tfv2/product/page_generate.py：

- generate_scoped：先校验页码，再切 scoped PDF，再调用 generate_lecture；
- 生成结果带 scope：选中页、原页数、page_count、mode、policy；
- plan_scoped：只算范围/策略，不生成。

页面策略强制：

- ≤100 页：approx 直接拒绝，只能 precise；
- 101–500：precise/approx；
- ≥501：两选 + 警告。

## 测试

- 120 页选 1-10：mock 生成器实际只收到 10 页；
- 110 页 approx 可用；
- 50 页 approx 被拒绝；
- 全量 **529 项通过**。

## 微信资料

仍未在磁盘找到 200+ 页模电和两份带答案数学试卷。  
没有用旧资料冒充。

## 成本 / 存储

- DeepSeek 余额：**¥111.92**；
- 磁盘可用：**7.1 GiB**，高于 5G；
- 未删用户资料。

## 判定

- 页码范围生成入口：完成；
- 100/500/1000 页策略：完成；
- 200 页模电实测：未开始（文件不在磁盘）；
- UI：未动；
- 第一梯队：未证明。

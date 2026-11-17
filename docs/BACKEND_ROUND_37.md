# Backend Round 37：人工题库 validated 门槛（2026-11-15）

## 改动

question_bank.validated：

- 每条必须有题干；
- 必须有答案；
- 必须有来源页；
- 缺一不可。

questions_handler 兜底：

- 全部满足 -> validated（source=manual_bank）；
- 否则 -> partial；
- 不再“有题就算 validated”。

## 测试

- 完整人工题（stem+answer+page）-> validated；
- 缺答案 -> partial；
- 全量 **521 项通过**。

## 实际

现有 demo 人工题库没有答案，所以仍是 partial。  
launch profile 仍 beta，release false。

## 成本 / 存储

- DeepSeek 余额：**¥112.51**；
- 磁盘可用：**8.0 GiB**，高于 5G；
- 未删用户资料。

## 判定

- 人工题库 validated 门槛：完成；
- questions 真 2/2 validated：仍未完成（缺带答案题库）；
- 第一梯队：未证明。

## 下一步

不再放宽：没有答案的人工题只能 partial。若用户提供带答案题库，questions 才能 validated；否则保持 beta 标注。
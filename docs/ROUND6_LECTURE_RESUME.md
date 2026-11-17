# 第 6 轮完成报告：讲义断点续跑（2026-11-13）

## 做了什么

- 讲义生成每完成一节，写 lecture_checkpoint.json：
  - 原资料路径、生成参数、plan、已完成 sections（按 plan 序号）。
  - 同时写 UPLOAD_ROOT/lecture_checkpoints/{job_id}.json，任务失败也能找到。
- generate_lecture 新增 resume_dir / checkpoint_path：
  - 从检查点恢复 plan 和已完成 sections；
  - 只为缺失的 plan 序号提交 author_section；
  - 已完成的节不重新生成；
  - 复用原 artifact 的图片/资源。
- 失败时若已有检查点，_fail 不再删除 artifact 目录，保证可续跑。
- 新增 POST /api/lectures/jobs/{job_id}/resume：
  - 读检查点，按原参数续跑；
  - 不是 retry 从头跑，是从最后一个完成节继续。
- 续跑完成仍走原来的图片、评审、Gate、PDF/Word 流程。

## 验收

- 手工集成测试：用真实 2 页 artifact + 检查点（1 个已完成节）调用 resume：
  - author_section 没有被调用（断言会抛错）；
  - 结果 sections=1，已完成节原样保留；
  - 图片/资源复用成功。
- 全量 433 项测试通过（无回退）。
- 新增接口编译通过。

## 和之前比

之前：讲义中断只能 retry 从头跑，已生成节全丢。
现在：检查点落盘，续跑只补缺失节；已完成节不重写。

## 这轮没做（如实）

- 检查点按“节”粒度，不是按段落/图；同一节内失败会重做这一节，不会只补半节。
- 续跑接口没有 UI 按钮；按路线 UI 在第 21–26 轮。
- 已补永久测试 tests/test_lecture_resume.py：resume 时 author_section 被禁止调用，仍成功。

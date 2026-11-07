"""生成后硬校验的执行器：生成 → 校验 → 带反馈重试 → 仍违规则失败。

重试不是"再掷一次骰子"：每次重试都把上一版的硬违规写回提示词，
让模型针对问题修正。超过重试次数仍违规时，``strict`` 约束下直接抛
``ConstraintViolation``，任务判失败，不交付有问题的结果。
"""
from __future__ import annotations

from typing import Callable

from loguru import logger

from core.quality.constraints import TaskConstraints, ValidationReport, validate_output


class ConstraintViolation(RuntimeError):
    """生成结果违反硬约束，且重试后仍未修复。"""

    def __init__(self, report: ValidationReport):
        self.report = report
        detail = "；".join(report.issues[:5]) or "未知违规"
        super().__init__(f"生成结果未通过硬校验：{detail}")

    def to_dict(self) -> dict:
        return self.report.to_dict()


GenerateFn = Callable[[str], str]


def generate_until_valid(
    generate: GenerateFn,
    constraints: TaskConstraints,
    *,
    source_text: str = "",
    allowed_pages: set[int] | list[int] | None = None,
    stage: str = "final",
    raise_on_fail: bool | None = None,
    on_retry: Callable[[int, ValidationReport], None] | None = None,
) -> tuple[str, ValidationReport]:
    """最多生成 ``1 + max_retries`` 次；返回 (最终文本, 最终校验报告)。

    raise_on_fail 为 None 时跟随 ``constraints.strict``；分块生成可以先收集
    违规统一处理，传 False 即可。
    """
    should_raise = constraints.strict if raise_on_fail is None else raise_on_fail
    attempts = 0
    feedback = ""
    markdown = ""
    report = ValidationReport(task=constraints.task)

    while True:
        markdown = generate(feedback) or ""
        attempts += 1
        report = validate_output(
            markdown, constraints,
            source_text=source_text,
            allowed_pages=allowed_pages,
            stage=stage,
        )
        report.metrics["attempts"] = attempts
        if report.ok or attempts > constraints.max_retries:
            break
        feedback = report.feedback()
        logger.warning("{} 第 {} 次生成未通过校验：{}", constraints.task, attempts,
                       "；".join(report.issues[:3]))
        if on_retry:
            on_retry(attempts, report)

    if not report.ok:
        logger.warning("{} 校验失败（尝试 {} 次）：{}", constraints.task, attempts,
                       "；".join(report.issues[:5]))
        if should_raise:
            raise ConstraintViolation(report)
    return markdown, report


def aggregate_reports(task: str, reports: dict) -> ValidationReport:
    """把分块报告合并成一份（key 为 (章, 块) 时自动加可读前缀）。"""
    out = ValidationReport(task=task)
    attempts = 0
    for key, report in (reports or {}).items():
        if isinstance(key, tuple) and len(key) == 2:
            label = f"第 {key[0] + 1} 章第 {key[1] + 1} 块"
        else:
            label = str(key)
        out.merge(report, prefix=f"{label}：")
        attempts += int((report.metrics or {}).get("attempts", 1))
    out.metrics["attempts"] = attempts
    return out

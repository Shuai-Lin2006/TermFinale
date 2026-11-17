"""Job state machine: estimate -> preview -> confirm -> run."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field

from .job_plan import JobPlan


class JobStage(str, Enum):
    AWAITING_CONFIRM = "awaiting_confirm"
    READY = "ready"
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    DONE = "done"
    FAILED = "failed"


class JobEvent(BaseModel):
    at: str
    stage: str
    message: str = ""
    current: int = 0
    total: int = 0


class JobRecord(BaseModel):
    job_id: str
    created_at: str
    stage: JobStage = JobStage.AWAITING_CONFIRM
    plan: JobPlan
    preview_generated: bool = False
    preview_file: str = ""
    confirmed: bool = False
    note: str = ""
    events: list[JobEvent] = Field(default_factory=list)


class JobStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, job_id: str) -> Path:
        return self.root / f"{job_id}.json"

    def create(self, plan: JobPlan) -> JobRecord:
        rec = JobRecord(job_id=uuid.uuid4().hex[:12],
                        created_at=datetime.now(timezone.utc).isoformat(), plan=plan)
        self.save(rec)
        rec.events.append(JobEvent(at=rec.created_at, stage="created", message="任务已创建"))
        self.save(rec)
        return rec

    def event(self, job_id: str, stage: str, message: str = "", current: int = 0, total: int = 0) -> JobRecord:
        rec = self.get(job_id)
        rec.events.append(JobEvent(at=datetime.now(timezone.utc).isoformat(),
                                   stage=stage, message=message, current=current, total=total))
        self.save(rec)
        return rec

    def save(self, rec: JobRecord) -> None:
        self._path(rec.job_id).write_text(rec.model_dump_json(indent=2), encoding="utf-8")

    def get(self, job_id: str) -> JobRecord:
        return JobRecord.model_validate_json(self._path(job_id).read_text(encoding="utf-8"))

    def preview(self, job_id: str, generated: bool = True, preview_file: str = "") -> JobRecord:
        rec = self.get(job_id)
        rec.preview_generated = generated
        rec.preview_file = preview_file or rec.preview_file
        rec.stage = JobStage.AWAITING_CONFIRM if not generated else JobStage.READY
        rec.events.append(JobEvent(at=datetime.now(timezone.utc).isoformat(), stage=rec.stage.value, message="预览就绪" if generated else "等待预览"))
        self.save(rec)
        return rec

    def confirm(self, job_id: str) -> JobRecord:
        rec = self.get(job_id)
        if not rec.preview_generated:
            raise ValueError("preview must be generated before confirm")
        rec.confirmed = True
        rec.stage = JobStage.QUEUED
        rec.events.append(JobEvent(at=datetime.now(timezone.utc).isoformat(), stage=rec.stage.value, message="用户已确认，等待 worker"))
        self.save(rec)
        return rec

    def start(self, job_id: str) -> JobRecord:
        rec = self.get(job_id)
        if rec.stage != JobStage.QUEUED:
            raise ValueError("job must be queued before start")
        rec.stage = JobStage.RUNNING
        rec.events.append(JobEvent(at=datetime.now(timezone.utc).isoformat(), stage=rec.stage.value, message="worker 已启动"))
        self.save(rec)
        return rec

    def cancel(self, job_id: str) -> JobRecord:
        rec = self.get(job_id)
        rec.stage = JobStage.PAUSED
        rec.events.append(JobEvent(at=datetime.now(timezone.utc).isoformat(), stage=rec.stage.value, message="用户已暂停"))
        self.save(rec)
        return rec

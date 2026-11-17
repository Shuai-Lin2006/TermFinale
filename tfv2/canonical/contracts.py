"""Module result contract shared by lecture/extract/questions/exam."""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ModuleStatus(str, Enum):
    VALIDATED = "validated"
    PARTIAL = "partial"
    REJECTED = "rejected"


class ModuleResult(BaseModel):
    module: str = Field(min_length=1)
    artifact_id: str = ""
    status: ModuleStatus
    items: int = Field(default=0, ge=0)
    coverage: float = Field(default=0, ge=0, le=1)
    evidence: dict[str, Any] = Field(default_factory=dict)
    issues: list[str] = Field(default_factory=list)


def gate(result: ModuleResult, *, min_items: int = 1, min_coverage: float = 0.0) -> ModuleResult:
    issues = list(result.issues)
    if result.items < min_items:
        issues.append(f"items {result.items} < {min_items}")
    if result.coverage < min_coverage:
        issues.append(f"coverage {result.coverage} < {min_coverage}")
    status = ModuleStatus.VALIDATED if not issues else ModuleStatus.PARTIAL
    return result.model_copy(update={"status": status, "issues": issues})

"""Real handlers for the workspace module runner."""
from __future__ import annotations

import json
from pathlib import Path

from . import exam, generate, local_extract, question_bank, questions_pagewise, service, tasks
from tfv2.llm.client import DeepSeekClient
from tfv2.llm.qwen_text import QwenTextClient


def extract_handler(*, gen_lang: str = "zh", client=None):
    client = client or DeepSeekClient(model="deepseek-flash")

    def handler(material: dict) -> dict:
        doc = tasks.run_task("extract_points", material["id"], "__all__",
                             gen_lang=gen_lang, client=client)
        return {"artifact_id": material["id"], "task": "extract_points",
                "status": doc.get("status"), "items": len((doc.get("content") or {}).get("items") or []),
                "coverage": (doc.get("coverage") or {}).get("coverage")}
    return handler


def lecture_handler(*, gen_lang: str = "zh"):
    def handler(material: dict) -> dict:
        path = service.artifact_path(material["id"])
        if path is None:
            raise RuntimeError("讲义不存在")
        source = next((p for p in (path / "source").glob("*") if p.is_file()), None)
        if source is None:
            raise RuntimeError("原资料不存在")
        res = generate.generate_lecture(source, title=material.get("title") or "章节讲义",
                                         course=material.get("title") or "课程", gen_lang=gen_lang,
                                         illustrations=False)
        quality = (res.get("artifact") or {}).get("quality") or {}
        return {"artifact_id": res.get("id"), "task": "lecture",
                "gate_passed": bool(quality.get("gate_passed")),
                "pages": res.get("pages")}
    return handler


def questions_handler(*, gen_lang: str = "zh", client=None, bank_root=None):
    client = client or QwenTextClient()

    def _manual(material_id: str):
        return question_bank.items(bank_root, material_id) if bank_root else []

    def _is_exam_source(material_id: str) -> bool:
        path = service.artifact_path(material_id)
        if path is None:
            return False
        try:
            data = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
            return str(data.get("kind") or "") == "exam_source"
        except Exception:
            return False

    def _pagewise(material_id: str) -> list[dict]:
        try:
            return questions_pagewise.extract_artifact(material_id, client).get("items") or []
        except Exception:
            return []

    def _local(material_id: str) -> list[dict]:
        path = service.artifact_path(material_id)
        if path is None:
            return []
        try:
            data = json.loads((path / "source_pages.json").read_text(encoding="utf-8"))
            pages = data.get("pages") if isinstance(data, dict) else data
            text = {i + 1: (p.get("text") or "") for i, p in enumerate(pages)}
            return local_extract.extract_questions(text, list(text))
        except Exception:
            return []

    def handler(material: dict) -> dict:
        if _is_exam_source(material["id"]):
            pagewise = _pagewise(material["id"])
            if pagewise:
                return {"artifact_id": material["id"], "task": "extract_questions",
                        "status": "validated" if question_bank.validated(pagewise) else "partial",
                        "items": len(pagewise), "source": "pagewise",
                        "reason": "exam_source"}
        try:
            doc = tasks.run_task("extract_questions", material["id"], "__all__",
                                 gen_lang=gen_lang, client=client)
            items = (doc.get("content") or {}).get("items") or []
            status = doc.get("status")
            if not items:
                manual = _manual(material["id"])
                if manual:
                    return {"artifact_id": material["id"], "task": "extract_questions",
                            "status": "validated" if question_bank.validated(manual) else "partial",
                            "items": len(manual), "source": "manual_bank",
                            "reason": "model_returned_zero"}
                pagewise = _pagewise(material["id"])
                if pagewise:
                    return {"artifact_id": material["id"], "task": "extract_questions",
                            "status": "validated" if question_bank.validated(pagewise) else "partial",
                            "items": len(pagewise), "source": "pagewise",
                            "reason": "model_returned_zero"}
                local = [x for x in _local(material["id"])
                         if x.get("answer_text") and x["answer_text"] != "原卷未给答案"]
                if local:
                    return {"artifact_id": material["id"], "task": "extract_questions",
                            "status": "partial", "items": len(local), "source": "local_ocr",
                            "reason": "model_returned_zero"}
                status = "no_questions"
            elif status == "rejected":
                status = "partial"
            return {"artifact_id": material["id"], "task": "extract_questions",
                    "status": status, "items": len(items), "source": "past_exam"}
        except Exception as exc:  # noqa: BLE001
            manual = _manual(material["id"])
            if manual:
                return {"artifact_id": material["id"], "task": "extract_questions",
                        "status": "validated" if question_bank.validated(manual) else "partial",
                        "items": len(manual), "source": "manual_bank",
                        "reason": "model_error", "error": f"{type(exc).__name__}: {exc}"}
            pagewise = _pagewise(material["id"])
            if pagewise:
                return {"artifact_id": material["id"], "task": "extract_questions",
                        "status": "validated" if question_bank.validated(pagewise) else "partial",
                        "items": len(pagewise), "source": "pagewise",
                        "reason": "model_error", "error": f"{type(exc).__name__}: {exc}"}
            local = [x for x in _local(material["id"])
                     if x.get("answer_text") and x["answer_text"] != "原卷未给答案"]
            if local:
                return {"artifact_id": material["id"], "task": "extract_questions",
                        "status": "partial", "items": len(local), "source": "local_ocr",
                        "reason": "model_error", "error": f"{type(exc).__name__}: {exc}"}
            return {"artifact_id": material["id"], "task": "extract_questions",
                    "status": "failed", "items": 0, "source": "model",
                    "reason": "model_error", "error": f"{type(exc).__name__}: {exc}"}
    return handler


def exam_handler(*, subject: str = "其他", gen_lang: str = "zh", client=None):
    client = client or DeepSeekClient(model="deepseek-v4-pro", effort="low")

    def handler(material: dict) -> dict:
        doc = exam.run_exam(material["id"], mode="mock", subject=subject,
                            gen_lang=gen_lang, client=client)
        sections = (doc.get("content") or {}).get("sections") or []
        questions = sum(len(s.get("questions") or []) for s in sections)
        status = doc.get("status")
        if questions and status == "rejected":
            status = "partial"
        content = doc.get("content") or {}
        return {"artifact_id": material["id"], "task": "exam",
                "status": status or ("done" if questions else "no_questions"),
                "questions": questions,
                "sections": [{"name": s.get("name"), "count": len(s.get("questions") or [])} for s in sections],
                "issues": doc.get("issues") or [],
                "coverage": doc.get("coverage") or {},
                "total_score": content.get("total_score"),
                "content": content}
    return handler

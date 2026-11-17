"""v3 产品服务：真实 artifact + 质量报告 + 练习/错题/复习。

原则：页面只显示能追溯的状态；没有 coverage_audit 就叫“待复核”，
没有通过 Gate 就叫“未通过”，不拿生成数/页数当完成。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from pathlib import Path
from typing import Any

from tfv2.llm.client import DeepSeekClient, LLMError
from tfv2.product import exclusions, source_pages, store

ROOT = Path(__file__).resolve().parents[2]
from tfv2.product.data_paths import ARTIFACT_ROOT, DATA_ROOT
# 用户库只放用户自己的产物；docs/evidence 是开发样本，默认不混进真实界面。
# 需要跑样本/评测时用 TERMFINALE_INCLUDE_EVIDENCE=1 显式打开。
ARTIFACT_ROOTS = [ARTIFACT_ROOT]
if os.environ.get("TERMFINALE_INCLUDE_EVIDENCE") == "1":
    ARTIFACT_ROOTS.insert(0, ROOT / "docs" / "evidence")
_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")

COURSE_META = {
    "电路": {"key": "circuit", "color": "teal", "icon": "bolt"},
    "有机化学": {"key": "organic", "color": "amber", "icon": "hex"},
    "医学": {"key": "medical", "color": "rose", "icon": "pulse"},
    "人体解剖学": {"key": "medical", "color": "rose", "icon": "pulse"},
    "化学动力学": {"key": "english", "color": "indigo", "icon": "flask"},
    "物理化学": {"key": "physical", "color": "indigo", "icon": "flask"},
    "其他": {"key": "other", "color": "slate", "icon": "book"},
}


def _course_name(aid: str, path: Path, manifest: dict) -> str:
    project = _read_json(path / "project.json", {}) if (path / "project.json").is_file() else {}
    header = project.get("header") if isinstance(project, dict) else {}
    course = str((header or {}).get("course") or manifest.get("course") or "").strip()
    if course:
        return course
    if aid.startswith("v2_circuit"):
        return "电路"
    if aid.startswith("v2_ring"):
        return "有机化学"
    if aid.startswith("v2_medical"):
        return "医学"
    if aid.startswith("v2_english"):
        return "化学动力学"
    return "其他"


class ProductError(RuntimeError):
    pass


class PracticeError(ProductError):
    pass



def refresh_artifact_gate(aid: str) -> dict:
    from tfv2.product import service
    path = service.artifact_path(aid)
    if path is None:
        raise FileNotFoundError("artifact not found")
    audit_path = path / "coverage_audit.json"
    if not audit_path.is_file():
        raise ValueError("还没有 coverage audit")
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    bad = [x for x in audit if x.get("status") in ("missing", "partial")]
    unverified = [x for x in audit if x.get("status") == "unverified"]
    manifest_path = path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    # 结构门禁归结构门禁，复核归复核：这里绝不能把 gate 改成“复核未通过”，
    # 否则页面会把结构完整的讲义显示成“结构未通过”。
    gate = manifest.get("gate") if isinstance(manifest.get("gate"), dict) else {}
    manifest["gate"] = {"passed": bool(gate.get("passed")),
                        "issues": list(gate.get("issues") or [])}
    manifest["coverage_audit"] = {
        "pages": len(audit),
        "covered": sum(1 for x in audit if x.get("status") == "covered"),
        "partial": sum(1 for x in audit if x.get("status") == "partial"),
        "missing": sum(1 for x in audit if x.get("status") == "missing"),
        "overview": sum(1 for x in audit if x.get("status") == "overview"),
        "unverified": len(unverified),
        "unverified_pages": [int(x.get("page_no") or 0) for x in unverified][:50],
        "note": ("复核没跑完的页会标为待复核，不代表内容缺失" if unverified else ""),
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return service.get_artifact(aid)


def _artifact_dir(aid: str) -> Path | None:
    if not _ID_RE.match(aid or ""):
        return None
    for root in ARTIFACT_ROOTS:
        path = root / aid
        if (path / "manifest.json").is_file() and (path / "lecture.html").is_file():
            return path
    return None


def artifact_path(aid: str) -> Path | None:
    return _artifact_dir(aid)


def _deletable_user_path(path: Path) -> bool:
    """Only artifacts under the writable user artifact root may be deleted."""
    try:
        from tfv2.product.data_paths import ARTIFACT_ROOT
        root = ARTIFACT_ROOT.resolve()
        rp = Path(path).resolve()
        return rp == root or root in rp.parents
    except Exception:
        return False


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _quality(aid: str, path: Path, manifest: dict) -> dict:
    gate = manifest.get("gate") if isinstance(manifest.get("gate"), dict) else {}
    content = manifest.get("content_gate") if isinstance(manifest.get("content_gate"), dict) else {}
    pdf = manifest.get("pdf_content_gate") if isinstance(manifest.get("pdf_content_gate"), dict) else {}
    language = manifest.get("language") if isinstance(manifest.get("language"), dict) else {}

    def hard(report: dict) -> bool:
        issues = report.get("issues") or []
        return any((x.get("severity") if isinstance(x, dict) else "hard") == "hard" for x in issues)

    audit_path = path / "coverage_audit.json"
    audit = _read_json(audit_path, None)
    audit_counts = {"covered": 0, "partial": 0, "missing": 0, "overview": 0, "visual": 0,
                    "empty": 0, "unverified": 0}
    missing_pages: list[int] = []
    unverified_pages: list[int] = []
    if isinstance(audit, list):
        for item in audit:
            status = item.get("status")
            if status in audit_counts:
                audit_counts[status] += 1
            if status in ("partial", "missing"):
                missing_pages.append(int(item.get("page_no") or 0))
            if status == "unverified":
                unverified_pages.append(int(item.get("page_no") or 0))
    audit_ok = (bool(audit) and audit_counts["partial"] == 0 and audit_counts["missing"] == 0
                and audit_counts["visual"] == 0 and audit_counts["empty"] == 0)
    audit_present = isinstance(audit, list) and len(audit) > 0

    figure_report = _read_json(path / "figure_report.json", [])
    figures_ok = 0
    figures_bad = 0
    if isinstance(figure_report, list):
        for f in figure_report:
            if f.get("status") in ("ok", "ok_schematic"):
                figures_ok += 1
            else:
                figures_bad += 1

    gate_ok = bool(gate.get("passed"))
    content_ok = not hard(content)
    pdf_ok = not hard(pdf)
    language_ok = not hard(language)

    sections_data = _read_json(path / "sections.json", [])
    has_readable = ((path / "lecture.pdf").is_file() or (path / "lecture.html").is_file()) and bool(sections_data)
    if not (gate_ok and content_ok and pdf_ok and language_ok):
        if manifest.get("draft") and has_readable:
            status = "partial"
            status_label = "部分交付"
        else:
            status = "rejected"
            status_label = "未通过"
    elif audit_ok:
        status = "delivered"
        status_label = "可读"
    else:
        status = "review"
        status_label = "待复核"

    return {
        "gate_passed": gate_ok,
        "content_passed": content_ok,
        "pdf_passed": pdf_ok,
        "language_passed": language_ok,
        "audit_present": audit_present,
        "audit_ok": audit_ok,
        "audit": audit_counts,
        "missing_pages": sorted(set(missing_pages)),
        "figures_ok": figures_ok,
        "figures_bad": figures_bad,
        "status": status,
        "status_label": status_label,
    }


def course_key_for(course: str) -> str:
    """课程名的稳定 key：同一门课在产物/偏好/前端之间必须一致。"""
    name = str(course or "")
    meta = COURSE_META.get(name)
    return meta["key"] if meta else "c-" + hashlib.md5(name.encode("utf-8")).hexdigest()[:8]


def _view(aid: str, path: Path, manifest: dict) -> dict:
    q = _quality(aid, path, manifest)
    sections = _sections(path)
    course = _course_name(aid, path, manifest)
    key = course_key_for(course)
    return {
        "id": aid,
        "course": course,
        "course_key": key,
        "title": str(manifest.get("chapter") or manifest.get("artifact") or aid),
        "page_count": manifest.get("page_count"),
        "pdf_pages": manifest.get("pdf_pages"),
        "coverage": manifest.get("scope_coverage") or manifest.get("material_coverage"),
        "sections": len(sections),
        "figures": manifest.get("figures") or q["figures_ok"],
        "quality": q,
        "delivery": {
            "status": q["status"],
            "label": q["status_label"],
            "exportable": (path / "lecture.pdf").is_file() or (path / "lecture.html").is_file(),
            "missing_pages": q.get("missing_pages") or [],
        },
        "reader_url": f"/artifact/{aid}/lecture.html",
        "pdf_url": f"/artifact/{aid}/lecture.pdf",
        "updated_at": manifest.get("generated_at") or "",
        "constraints": manifest.get("constraints") or {},
        "root": str(path),
        "source_only": bool(manifest.get("source_only")),
        "sources": manifest.get("sources") or [],
        "pending_regeneration": bool(manifest.get("pending_regeneration")),
        "word_available": (path / "project.json").is_file() and (path / "sections.json").is_file(),
    }


def list_artifacts() -> list[dict]:
    out: list[dict] = []
    for root in ARTIFACT_ROOTS:
        if not root.is_dir():
            continue
        for manifest_path in sorted(root.glob("*/manifest.json")):
            aid = manifest_path.parent.name
            if not _ID_RE.match(aid):
                continue
            if not (manifest_path.parent / "lecture.html").is_file():
                continue
            manifest = _read_json(manifest_path, {})
            if not isinstance(manifest, dict):
                continue
            if manifest.get("preview"):
                continue
            out.append(_view(aid, manifest_path.parent, manifest))
    out.sort(key=lambda x: (x["quality"]["status"] != "delivered", -(x["pdf_pages"] or 0), x["id"]))
    return out


def get_artifact(aid: str) -> dict | None:
    path = _artifact_dir(aid)
    if path is None:
        return None
    manifest = _read_json(path / "manifest.json", {})
    view = _view(aid, path, manifest if isinstance(manifest, dict) else {})
    view["section_list"] = _sections(path)
    view["figure_list"] = _read_json(path / "figure_report.json", [])
    try:
        raw = source_pages.load_source_pages(path)
        sections = _read_json(path / "sections.json", [])
        if raw and isinstance(sections, list):
            from tfv2.quality import trust
            view["trust"] = trust.audit_evidence(sections, source_pages.page_map(raw))
    except Exception:
        pass
    return view


def _sections(path: Path) -> list[dict]:
    data = _read_json(path / "sections.json", [])
    if not isinstance(data, list):
        return []
    out: list[dict] = []
    for sec in data:
        if not isinstance(sec, dict):
            continue
        pages: set[int] = set()
        for ref in sec.get("source_refs") or []:
            try:
                start = int(ref.get("page_start"))
                end = int(ref.get("page_end") or start)
                pages.update(range(start, end + 1))
            except Exception:
                pass
        blocks = sec.get("blocks") or []
        out.append({
            "id": str(sec.get("id") or sec.get("title") or ""),
            "title": str(sec.get("title") or ""),
            "pages": sorted(pages),
            "blocks": len(blocks),
            "paragraphs": sum(1 for b in blocks if b.get("kind") == "paragraph"),
            "figures": sum(1 for b in blocks if b.get("kind") == "figure"),
        })
    return out


def list_courses() -> list[dict]:
    courses: dict[str, dict] = {}
    for a in list_artifacts():
        key = a["course_key"]
        meta = COURSE_META.get(a["course"], COURSE_META["其他"])
        item = courses.setdefault(key, {
            "key": key, "name": a["course"], "color": meta["color"], "icon": meta["icon"],
            "artifact_ids": [], "delivered": 0, "review": 0, "rejected": 0, "source_only": 0,
            "pages": 0, "sections": 0, "figures": 0, "updated_at": "",
        })
        item["artifact_ids"].append(a["id"])
        if a.get("source_only"):
            item["source_only"] = item.get("source_only", 0) + 1
        else:
            item[a["quality"]["status"]] = item.get(a["quality"]["status"], 0) + 1
        item["pages"] += a.get("pdf_pages") or 0
        item["sections"] += a.get("sections") or 0
        item["figures"] += a.get("figures") or 0
        item["updated_at"] = max(item["updated_at"], a.get("updated_at") or "")
    for key, item in courses.items():
        pref = store.get_course_prefs(key)
        item["target_score"] = int(pref.get("target_score") or 0)
        item["exam_date"] = str(pref.get("exam_date") or "")
        item["credits"] = float(pref.get("credits") or 0)
        item["course_type"] = str(pref.get("course_type") or "")
        item["school_level"] = str(pref.get("school_level") or "")
        item["days_left"] = int(pref.get("days_left") or 7)
        item["foundation"] = str(pref.get("foundation") or "基础较弱")
        item["key_points"] = str(pref.get("key_points") or "")
        item["excluded"] = str(pref.get("excluded") or "")
        item["custom_prompt"] = str(pref.get("custom_prompt") or "")
        item["difficulty"] = int(pref.get("difficulty") or 3)
        if str(pref.get("display_name") or "").strip():
            item["name"] = str(pref.get("display_name")).strip()
    out = list(courses.values())
    out.sort(key=lambda x: (x["delivered"] == 0, -len(x["artifact_ids"]), x["name"]))
    return out


def get_course(key: str) -> dict | None:
    for c in list_courses():
        if c["key"] == key:
            arts = [a for a in list_artifacts() if a["course_key"] == key]
            c = dict(c)
            c["artifacts"] = arts
            return c
    return None


def archive_artifact(key: str, artifact_id: str) -> int:
    """Permanently delete one user-created artifact and its learner records."""
    import shutil
    course = get_course(key)
    if course is None:
        raise ValueError("课程不存在")
    if artifact_id not in (course.get("artifact_ids") or []):
        raise ValueError("讲义不属于这门课程")
    p = artifact_path(artifact_id)
    if p is None:
        raise ValueError("讲义不存在")
    if not _deletable_user_path(p):
        raise ValueError("内置/交付资料不能删除")
    store.delete_artifact_records(artifact_id)
    shutil.rmtree(p, ignore_errors=False)
    return 1


def archive_course(key: str) -> int:
    """Permanently delete every user-created artifact in a course."""
    import shutil
    course = get_course(key)
    if course is None:
        raise ValueError("课程不存在")
    movable = []
    for a in course.get("artifacts") or []:
        p = artifact_path(str(a.get("id") or ""))
        if p is not None and _deletable_user_path(p):
            movable.append(p)
    if not movable:
        raise ValueError("这门课只包含内置/交付资料，不能删除")
    # Delete records first: if the DB cleanup fails, the user still has the
    # source files and the course rather than a half-deleted artifact tree.
    store.delete_course_records(key, [str(a.get("id") or "") for a in course.get("artifacts") or []])
    for p in movable:
        shutil.rmtree(p, ignore_errors=False)
    return len(movable)


def home_data() -> dict:
    artifacts = list_artifacts()
    due = store.due_mistakes()
    return {
        "artifacts": artifacts,
        "courses": list_courses(),
        "due_count": len(due),
        "delivered_count": sum(1 for a in artifacts if a["quality"]["status"] == "delivered"),
        "review_count": sum(1 for a in artifacts if a["quality"]["status"] == "review"),
        "rejected_count": sum(1 for a in artifacts if a["quality"]["status"] == "rejected"),
    }


def _section_text(path: Path, section_id: str) -> tuple[dict, str, list[int]]:
    data = _read_json(path / "sections.json", [])
    if not isinstance(data, list):
        raise PracticeError("讲义没有 sections.json")
    for sec in data:
        if str(sec.get("id")) != section_id and str(sec.get("title")) != section_id:
            continue
        pages: set[int] = set()
        chunks: list[str] = []
        for block in sec.get("blocks") or []:
            if block.get("kind") == "figure":
                continue
            text = str(block.get("text") or "").strip()
            if text:
                chunks.append(text)
            for ref in block.get("source_refs") or []:
                try:
                    start = int(ref.get("page_start"))
                    end = int(ref.get("page_end") or start)
                    pages.update(range(start, end + 1))
                except Exception:
                    pass
        if not chunks:
            raise PracticeError("这一节没有可用于出题的正文")
        raw = source_pages.load_source_pages(path)
        raw_map = source_pages.page_map(raw) if raw else {}
        if raw and pages and all(p in raw_map for p in pages) and any(raw_map.get(p, "").strip() for p in pages):
            return sec, source_pages.source_context(raw, sorted(pages), 7000), sorted(pages)
        return sec, "\n".join(chunks)[:7000], sorted(pages)
    raise PracticeError("找不到这一节")


def _parse_questions(data: dict, aid: str, section: str, allowed_pages: set[int]) -> list[dict]:
    items = data.get("questions")
    if not isinstance(items, list):
        return []
    out: list[dict] = []
    for raw in items:
        if not isinstance(raw, dict):
            continue
        stem = str(raw.get("stem") or "").strip()
        options = raw.get("options")
        if not stem or not isinstance(options, list):
            continue
        options = [str(x).strip() for x in options]
        if len(options) != 4 or any(not x for x in options) or len(set(options)) != 4:
            continue
        try:
            answer = int(raw.get("answer"))
        except Exception:
            continue
        if answer not in range(4):
            continue
        try:
            page = int(raw.get("page"))
        except Exception:
            page = 0
        if page not in allowed_pages:
            continue
        explanation = str(raw.get("explanation") or "").strip()
        if not explanation:
            continue
        out.append({
            "id": uuid.uuid4().hex,
            "artifact_id": aid,
            "section": section,
            "stem": stem,
            "options": options,
            "answer": answer,
            "explanation": explanation,
            "page": page,
        })
    return out


def _artifact_exclusion_specs(path: Path) -> list[dict]:
    try:
        project = json.loads((path / "project.json").read_text(encoding="utf-8"))
        constraints = project.get("constraints") or {}
        existing = (constraints.get("exclusions") or {}).get("specs")
        if existing:
            return existing
        return exclusions.specs_from_requirements(
            constraints.get("requirements") or {},
            constraints.get("excluded") or "",
            constraints.get("custom_prompt") or "",
        )["specs"]
    except Exception:
        return []


def generate_questions(aid: str, section: str, count: int = 3) -> list[dict]:
    path = _artifact_dir(aid)
    if path is None:
        raise PracticeError("讲义不存在")
    sec, context, pages = _section_text(path, section)
    specs = _artifact_exclusion_specs(path)
    if specs and exclusions.text_hit(str(sec.get("title") or ""), [s for s in specs if s.get("scope") == "section"], "practice"):
        raise PracticeError("这一节被用户标记为不考")
    for spec in specs:
        if spec.get("scope") == "section_limit" and str(spec.get("value") or "").isdigit():
            if exclusions.section_exceeds_limit(str(sec.get("title") or ""), int(spec["value"])):
                raise PracticeError("这一节超出用户限定的考试范围")
    page_specs = {int(s["value"]) for s in specs if s.get("scope") == "page" and str(s.get("value") or "").isdigit()}
    pages = [p for p in pages if p not in page_specs]
    if not pages:
        raise PracticeError("这一节的内容被用户全部排除")
    exclusion_note = exclusions.exclusion_prompt([s for s in specs if s.get("scope") in ("topic", "section")], "practice")
    count = max(1, min(int(count), 5))
    system = (
        "你是命题助教。只依据给出的讲义段落出单选题。"
        "每题必须有 4 个不同选项、唯一正确答案、答案在选项内、解析说明为什么，并给出段落里的一个页码；公式用 $...$ 包裹。"
        "不要编资料外内容。只输出 JSON："
        '{"questions":[{"stem":"题干","options":["A","B","C","D"],"answer":0,'
        '"explanation":"解析","page":52}]}。不要 Markdown。'
    )
    if exclusion_note:
        system += "\n" + exclusion_note
    user = (
        f"学科/章节：{sec.get('title')}\n"
        f"可用页码：{pages}\n\n"
        f"讲义段落：\n{context}\n\n"
        f"请出 {count} 道题。"
    )
    client = DeepSeekClient(model="deepseek-flash")
    last = ""
    for _ in range(2):
        try:
            raw = client.json(system, user, max_tokens=4000, temperature=0.2)
        except LLMError as exc:
            last = str(exc)
            continue
        items = _parse_questions(raw, aid, section, set(pages))
        if items and specs:
            items, _ = exclusions.filter_questions(items, specs, "practice")
        if items:
            store.save_questions(items)
            return items
        last = "模型没有返回合法题目（选项/答案/页码不完整）"
    raise PracticeError(last or "出题失败，请重试")



def practice_from_units(aid: str, pages: list[int], count: int = 3, client=None) -> dict:
    """按 PageUnit 出题，并明确报告哪些页因为公式/图片被跳过。

    跳过必须说出来：不能静默当用户没选过，也不能把公式硬转成文字出题。
    """
    path = _artifact_dir(aid)
    if path is None:
        raise PracticeError("资料不存在")
    raw = json.loads((path / "source_pages.json").read_text(encoding="utf-8"))
    rows = raw.get("pages") or raw
    if not pages:
        raise PracticeError("先选择资料页")
    bad = [p for p in pages if int(p) < 1 or int(p) > len(rows)]
    if bad:
        raise PracticeError(f"页码超出资料范围：{sorted(set(bad))[:5]}")
    chosen = sorted({int(p) for p in pages})[:8]
    from tfv2.domain.page_unit import build_page_unit
    parts = []
    skipped: list[int] = []
    for p in chosen:
        unit = build_page_unit(p, str(rows[p - 1].get("text") or ""))
        if unit.kind in ("text", "table") and unit.text.strip():
            parts.append(f"[第{p}页]\n{unit.text[:5000]}")
        else:
            skipped.append(p)
    context = "\n\n".join(parts)
    if not context.strip():
        raise PracticeError("这些页以公式/图片为主，暂不能直接出题；请选文字页")
    count = max(1, min(int(count), 5))
    system = (
        "你是命题助教。只依据给出的资料原文出单选题。"
        "每题必须有 4 个不同选项、唯一正确答案、答案在选项内、解析说明为什么，并给出原文页码；公式用 $...$ 包裹。"
        "不要编资料外内容。只输出 JSON："
        '{"questions":[{"stem":"题干","options":["A","B","C","D"],"answer":0,'
        '"explanation":"解析","page":1}]}。不要 Markdown。'
    )
    user = f"资料页：{chosen}\n\n原始内容：\n{context}\n\n请出 {count} 道题。"
    client = client or DeepSeekClient(model="deepseek-flash")
    last = ""
    for _ in range(2):
        try:
            data = client.json(system, user, max_tokens=4000, temperature=0.2)
        except LLMError as exc:
            last = str(exc)
            continue
        items = _parse_questions(data, aid, "资料页 " + ",".join(map(str, chosen)), set(chosen))
        if items:
            store.save_questions(items)
            return {"questions": items, "skipped_pages": skipped,
                    "used_pages": [p for p in chosen if p not in skipped]}
        last = "模型没有返回合法题目（选项/答案/页码不完整）"
    raise PracticeError(last or "出题失败，请重试")


def generate_questions_from_pages(aid: str, pages: list[int], count: int = 3) -> list[dict]:
    """兼容旧调用：只要题目列表的入口。"""
    return practice_from_units(aid, pages, count)["questions"]

def grade_question(qid: str, chosen: int, context: str = "practice") -> dict:
    q = store.get_question(qid)
    if q is None:
        raise PracticeError("题目不存在")
    correct = int(chosen) == int(q["answer"])
    store.record_attempt(qid, int(chosen), correct, context=context)
    mistake_id = None
    if not correct:
        mistake_id = store.upsert_mistake(q)
    return {
        "correct": correct,
        "answer": q["answer"],
        "explanation": q["explanation"],
        "page": q.get("page"),
        "mistake_id": mistake_id,
    }


def review_data() -> dict:
    from datetime import date
    due = store.due_mistakes()
    all_items = store.all_mistakes()
    today = date.today().isoformat()
    scheduled = [x for x in all_items if str(x.get("next_review") or "") > today]
    mastery = store.mastery()
    return {
        "due": due,
        "scheduled": scheduled,
        "all_count": len(all_items),
        "mastery": mastery,
    }

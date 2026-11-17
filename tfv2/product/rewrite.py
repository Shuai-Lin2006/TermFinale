"""整份讲义 AI 改写：生成新草稿，不覆盖原稿；重新过 Gate/PDF。"""
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

from tfv2.authoring.lecture import AuthoringError
from tfv2.build import build_project
from tfv2.llm.client import DeepSeekClient, LLMError
from tfv2.product import generate, service

LANG_LABEL = {"zh": "简体中文", "hant": "繁體中文", "en": "English"}
from tfv2.product.data_paths import ARCHIVE_ROOT


class RewriteError(RuntimeError):
    pass


def _paragraphs(section: dict) -> list[dict]:
    return [b for b in section.get("blocks") or []
            if b.get("kind") == "paragraph" and str(b.get("text") or "").strip()]


def rewrite_artifact(aid: str, *, instruction: str, gen_lang: str = "zh", client=None) -> dict:
    src = service.artifact_path(aid)
    if src is None:
        raise RewriteError("讲义不存在")
    if not (src / "project.json").is_file() or not (src / "sections.json").is_file():
        raise RewriteError("这份产物没有 project.json/sections.json，不能整份改写")
    instruction = (instruction or "").strip()
    if not instruction:
        raise RewriteError("请填写改写要求")
    gen_lang = gen_lang if gen_lang in LANG_LABEL else "zh"
    client = client or DeepSeekClient()
    draft_id = f"{aid}_ai_{datetime.now().strftime('%m%d_%H%M%S')}"
    dst = generate.ARTIFACT_ROOT / draft_id
    if dst.exists():
        raise RewriteError("草稿目录已存在，请重试")
    shutil.copytree(src, dst)
    try:
        data = json.loads((dst / "sections.json").read_text(encoding="utf-8"))
        diffs = []
        for si, sec in enumerate(data, start=1):
            paras = _paragraphs(sec)
            if not paras:
                continue
            before = [str(b.get("text") or "") for b in paras]
            system = (
                "你是大学教材编辑。只改写给定的段落：保留全部事实、公式、术语、页码和因果关系；"
                "不要新增资料外内容；不要输出标题/解释/Markdown 围栏。"
                f"改写语言：{LANG_LABEL[gen_lang]}；资料原题/原文引用/术语保持原语言。"
                '只输出 JSON：{"paragraphs":["改写后的第1段","改写后的第2段",...]}，数量必须与输入一致。'
            )
            user = (
                f"改写要求：{instruction}\n\n"
                + "\n\n".join(f"[{i+1}] {text}" for i, text in enumerate(before))
                + "\n\n请逐段改写，输出 JSON。"
            )
            raw = client.json(system, user, max_tokens=5000, temperature=0.35)
            after = raw.get("paragraphs")
            if not isinstance(after, list) or len(after) != len(before):
                raise RewriteError(f"第 {si} 节改写段数不一致，已放弃草稿")
            for b, text in zip(paras, after):
                b["text"] = str(text).strip()
            diffs.append({"title": sec.get("title"), "before": before, "after": [str(x).strip() for x in after]})
        (dst / "sections.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        project = json.loads((dst / "project.json").read_text(encoding="utf-8"))
        project["id"] = draft_id
        project["chapter_title"] = str(project.get("chapter_title") or "") + "（AI 改写草稿）"
        project["header"]["title"] = str(project["header"].get("title") or "") + "（AI 改写草稿）"
        project.setdefault("constraints", {})
        project["constraints"].update({"draft_of": aid, "rewrite_instruction": instruction, "gen_lang": gen_lang})
        project["language_policy"] = {"ui_lang": "zh", "gen_lang": LANG_LABEL[gen_lang],
                                      "source_lang": None, "translation_mode": "none"}
        (dst / "project.json").write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8")
        build_project(dst / "project.json", pdf=True)
    except (RewriteError, AuthoringError, LLMError) as exc:
        shutil.rmtree(dst, ignore_errors=True)
        raise RewriteError(str(exc)) from exc
    except Exception as exc:
        shutil.rmtree(dst, ignore_errors=True)
        raise RewriteError(f"改写草稿未通过 Gate/PDF：{exc}") from exc
    return {"draft_id": draft_id, "artifact": service.get_artifact(draft_id), "diffs": diffs}




def _backup_original(aid: str, src: Path) -> Path:
    ARCHIVE_ROOT.mkdir(parents=True, exist_ok=True)
    backup = ARCHIVE_ROOT / f"{aid}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    if backup.exists():
        raise RewriteError("备份目录已存在，请重试")
    shutil.copytree(src, backup)
    return backup


def accept_draft(draft_id: str) -> dict:
    """一键替换原稿：先备份，再替换并重建；失败自动还原。"""
    draft = service.artifact_path(draft_id)
    if draft is None:
        raise RewriteError("草稿不存在")
    try:
        project = json.loads((draft / "project.json").read_text(encoding="utf-8"))
    except Exception as exc:
        raise RewriteError("草稿缺少 project.json") from exc
    original_id = str((project.get("constraints") or {}).get("draft_of") or "").strip()
    if not original_id:
        raise RewriteError("这不是 AI 改写草稿，不能替换原稿")
    original = service.artifact_path(original_id)
    if original is None:
        raise RewriteError("原稿不存在")
    if original.resolve() == draft.resolve():
        raise RewriteError("草稿和原稿是同一目录")
    backup = _backup_original(original_id, original)
    try:
        shutil.rmtree(original)
        shutil.copytree(draft, original)
        project["id"] = original_id
        title = str(project.get("chapter_title") or "")
        title = title.replace("（AI 改写草稿）", "").strip()
        project["chapter_title"] = title
        header = project.get("header") or {}
        header["title"] = str(header.get("title") or "").replace("（AI 改写草稿）", "").strip()
        project["header"] = header
        constraints = project.setdefault("constraints", {})
        constraints.pop("draft_of", None)
        constraints["replaced_draft"] = draft_id
        constraints["backup"] = str(backup)
        (original / "project.json").write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8")
        build_project(original / "project.json", pdf=True)
    except Exception as exc:
        shutil.rmtree(original, ignore_errors=True)
        shutil.copytree(backup, original)
        raise RewriteError(f"替换失败，已自动还原原稿：{exc}") from exc
    shutil.rmtree(draft, ignore_errors=True)
    return {"artifact": service.get_artifact(original_id), "backup": backup.name}


def list_backups(aid: str) -> list[dict]:
    ARCHIVE_ROOT.mkdir(parents=True, exist_ok=True)
    out = []
    for p in sorted(ARCHIVE_ROOT.glob(f"{aid}_*"), reverse=True):
        if p.is_dir():
            out.append({"name": p.name, "created_at": datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")})
    return out


def restore_backup(aid: str, name: str) -> dict:
    if not str(name).startswith(aid + "_") or "/" in name or ".." in name:
        raise RewriteError("备份名不合法")
    backup = ARCHIVE_ROOT / name
    if not backup.is_dir():
        raise RewriteError("备份不存在")
    original = service.artifact_path(aid)
    if original is None:
        raise RewriteError("原稿不存在")
    _backup_original(aid, original)
    try:
        shutil.rmtree(original)
        shutil.copytree(backup, original)
        build_project(original / "project.json", pdf=True)
    except Exception as exc:
        raise RewriteError(f"恢复失败：{exc}") from exc
    return {"artifact": service.get_artifact(aid), "backup": name}

def discard_draft(draft_id: str) -> None:
    path = service.artifact_path(draft_id)
    if path is None:
        raise RewriteError("草稿不存在")
    try:
        project = json.loads((path / "project.json").read_text(encoding="utf-8"))
    except Exception as exc:
        raise RewriteError("不是可丢弃的改写草稿") from exc
    if not (project.get("constraints") or {}).get("draft_of"):
        raise RewriteError("只能丢弃 AI 改写草稿，不能丢弃原始讲义")
    shutil.rmtree(path, ignore_errors=True)

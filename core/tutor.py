"""课程级 AI 助教：先检索资料页，再回答；无依据不装懂。

这是“AI 贯穿始终”的后端入口：阅读器、全局抽屉、错题解释都可以调用它。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

from loguru import logger
from openai import OpenAI

from core import paths
from core.config import get_key, load_env, max_tokens, model_extra, text_model
from core.database import Course, Material, get_db_session
from core.parser import PARSER_VERSION, extract_text_from_file
from core.retrieval import build_index, search

_SYSTEM = """你是这门课的期末复习助教。你必须遵守：
1. 只依据用户提供的【资料页】回答；每个结论后面标（P.页码）。
2. 资料页没有的内容，直接说“资料里没有检索到”，不要编；可以用基础常识补充，但必须标【延伸】。
3. 先给结论，再拆步骤；学生基础差就降维解释，不要堆术语。
4. 公式用 $...$；不要编造页码、定理编号、题目数据。
5. 回答控制在 700 字内，但要把话说完整。"""


def _cache_key(path: str) -> str:
    st = os.stat(path)
    return hashlib.md5(f"{PARSER_VERSION}|{path}|{st.st_mtime}|{st.st_size}".encode()).hexdigest()


def _pages_for_material(m: Material) -> list[str]:
    try:
        key = _cache_key(m.file_path)
        cache_dir = paths.data_dir() / "parse_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache = cache_dir / f"{key}.json"
        if cache.is_file():
            try:
                return json.loads(cache.read_text(encoding="utf-8"))
            except Exception:
                pass
        pages = extract_text_from_file(m.file_path)
        try:
            cache.write_text(json.dumps(pages, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass
        return pages
    except Exception as exc:  # noqa: BLE001
        logger.warning("AI 索引解析失败 {}: {}", getattr(m, "filename", ""), str(exc)[:120])
        return []


def _course_index(course_id: int, file_id: int | None = None) -> list[dict]:
    db = get_db_session()
    try:
        q = db.query(Material).filter(Material.course_id == course_id)
        if file_id:
            q = q.filter(Material.id == file_id)
        mats = list(q.all())
    finally:
        db.close()
    docs = []
    for m in mats:
        for doc in build_index(_pages_for_material(m), m.filename):
            docs.append(doc)
    return docs


def _source_block(hits: list[dict]) -> str:
    parts = []
    for h in hits:
        parts.append(f"【资料页：{h['source']} 第 {h['page']} 页】\n{h['text']}")
    return "\n\n".join(parts)


def ask_course(payload: dict) -> dict:
    question = (payload.get("question") or "").strip()[:800]
    selection = (payload.get("context") or payload.get("selection") or "").strip()[:12000]
    course_id = int(payload.get("course_id") or 0)
    file_id = int(payload.get("file_id") or 0) or None
    course_name = (payload.get("course") or "").strip()[:80]
    if not question:
        return {"answer": "没有收到问题。", "sources": []}
    if not course_id:
        return {"answer": "缺少课程上下文，无法检索资料。", "sources": []}

    index = _course_index(course_id, file_id)
    hits = search(index, (selection + " " + question), top_k=4) if index else []
    # 选中片段没有页码时，也把它当作高优先级上下文
    sources = [{"page": h["page"], "source": h["source"], "score": h["score"]} for h in hits]
    if not hits and not selection:
        return {"answer": "资料里没有检索到与这个问题相关的内容。可以换个说法，或先上传对应资料。",
                "sources": []}

    load_env()
    prompt = (f"课程：{course_name or '未知'}\n"
              f"【资料页】\n{_source_block(hits) or '（没有检索到页）'}\n\n"
              f"【用户选中/当前页面】\n{selection or '（无）'}\n\n"
              f"【问题】{question}")
    try:
        client = OpenAI(api_key=get_key("DEEPSEEK_API_KEY", "sk-not-configured"),
                        base_url="https://api.deepseek.com")
        resp = client.chat.completions.create(
            model=text_model(), max_tokens=min(2200, max_tokens()), temperature=0.2,
            messages=[{"role": "system", "content": _SYSTEM},
                      {"role": "user", "content": prompt}],
            **model_extra())
        answer = (resp.choices[0].message.content or "").strip()
    except Exception as exc:  # noqa: BLE001
        logger.error("课程问答失败: {}", exc)
        return {"answer": f"问答失败：{type(exc).__name__}。请检查 API Key 或网络。", "sources": sources}
    if not answer:
        return {"answer": "模型没有返回内容，请重试。", "sources": sources}
    return {"answer": answer, "sources": sources}

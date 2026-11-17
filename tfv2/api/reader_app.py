"""v2 阅读器本地服务：讲义库 + 静态讲义 + /api/ask。

启动：
  PYTHONPATH=. .venv/bin/python -m tfv2.api.reader_app
打开：
  http://127.0.0.1:8905/
"""
from __future__ import annotations

import html
import os
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from tfv2.library import Artifact, discover
from tfv2.llm.client import DeepSeekClient, LLMError
from tfv2.retrieval import RetrievalIndex, context as retrieval_context, expand_neighbors, search, sources as retrieval_sources
from tfv2.store import append_chat, clear_chat, list_chat

ROOT = Path(os.getenv("TERMFINALE_ROOT", str(Path(__file__).resolve().parents[2])))

app = FastAPI(title="TermFinale v2 reader", version="0.2")
app.mount("/web", StaticFiles(directory=str(ROOT / "web")), name="web")
if (ROOT / "docs").is_dir():
    app.mount("/docs", StaticFiles(directory=str(ROOT / "docs")), name="docs")


@app.middleware("http")
async def local_origin_guard(request: Request, call_next):
    origin = (request.headers.get("origin") or "").strip()
    if origin:
        from urllib.parse import urlparse
        parsed = urlparse(origin)
        if parsed.scheme not in ("http", "https") or parsed.hostname not in ("127.0.0.1", "localhost", "::1"):
            return JSONResponse({"detail": "拒绝跨站请求"}, status_code=403)
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    return response


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class PracticePayload(BaseModel):
    artifact_id: str
    section: str = ""
    count: int = 3


class AskPayload(BaseModel):
    question: str
    context: str = ""
    mode: str = "explain"
    artifact_id: str = ""
    selection: str = ""
    session_id: str = "default"
    lang: str = "zh"
    history: list[Message] = []


def _badge(value: bool | None) -> str:
    if value is True:
        return '<span class="ok">通过</span>'
    if value is False:
        return '<span class="bad">未通过</span>'
    return '<span class="muted">—</span>'


def _library_html(items: list[Artifact]) -> str:
    rows = []
    for a in items:
        pdf = f'<a href="{html.escape(a.pdf_url)}" target="_blank">PDF</a>' if a.pdf_url else '<span class="muted">—</span>'
        rows.append(
            "<tr>"
            f"<td><a class=\"title\" href=\"{html.escape(a.html_url)}\">{html.escape(a.title)}</a>"
            f"<div class=\"id\">{html.escape(a.id)}</div></td>"
            f"<td>{a.page_count or '—'}</td><td>{html.escape(a.coverage or '—')}</td>"
            f"<td>{_badge(a.gate_passed)}</td><td>{a.sections or '—'}</td><td>{a.figures or '—'}</td>"
            f"<td>{html.escape(a.updated_at or '—')}</td>"
            f"<td><a href=\"{html.escape(a.html_url)}\">阅读</a> · <a href=\"{html.escape(a.html_url)}?ai=1\">问 AI</a> · {pdf}</td>"
            "</tr>"
        )
    body = "".join(rows) or '<tr><td colspan="8" class="muted">还没有讲义。</td></tr>'
    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>TermFinale 讲义库</title>
<style>
body{{margin:0;background:#f3f4f6;color:#1f2328;font-family:-apple-system,"PingFang SC","Noto Sans CJK SC",sans-serif}}
main{{max-width:1080px;margin:48px auto;padding:0 22px}}
h1{{font-size:30px;margin:0 0 6px}}
.sub{{color:#5b6470;margin:0 0 24px}}
table{{width:100%;border-collapse:collapse;background:#fff;border:1px solid #e1e5ea}}
th,td{{text-align:left;padding:12px 10px;border-bottom:1px solid #eceff3;font-size:13px;vertical-align:top}}
th{{font-size:12px;color:#5b6470;font-weight:600;background:#fafbfc}}
a{{color:#245c73;text-decoration:none}} a:hover{{text-decoration:underline}}
.title{{font-size:15px;font-weight:600;color:#1f2328}} .id{{color:#8a929c;font-size:11px;margin-top:2px}}
.ok{{color:#1f7a4d;font-weight:600}} .bad{{color:#a33;font-weight:600}} .muted{{color:#8a929c}}
.note{{margin-top:18px;color:#5b6470;font-size:12px;line-height:1.8}}
</style></head><body><main>
<h1>TermFinale 讲义库</h1>
<p class="sub">阅读、搜索、编辑、导出 PDF/Word/HTML，或让 AI 助教基于当前讲义回答。</p>
<table><thead><tr><th>讲义</th><th>页数</th><th>覆盖</th><th>Gate</th><th>小节</th><th>图</th><th>更新时间</th><th>操作</th></tr></thead>
<tbody>{body}</tbody></table>
<p class="note">PDF 为 A4 真实分页，带书签和目录跳转；HTML 阅读器右上角有搜索/编辑/导出/AI 助教。AI 只依据当前页面上下文回答。</p>
</main></body></html>"""


@app.get("/", response_class=HTMLResponse)
def index():
    return _library_html(discover(ROOT))


@app.get("/api/artifacts")
def artifacts():
    return [a.model_dump() for a in discover(ROOT)]


@app.get("/read/{artifact_id}")
def read(artifact_id: str):
    for a in discover(ROOT):
        if a.id == artifact_id:
            return RedirectResponse(url=a.html_url)
    raise HTTPException(404, "没有这份讲义")


@app.get("/api/health")
def health():
    return {"ok": True}


def _load_index(artifact_id: str) -> RetrievalIndex | None:
    if not artifact_id or "/" in artifact_id or ".." in artifact_id:
        return None
    path = ROOT / "docs" / "evidence" / artifact_id / "retrieval_index.json"
    if not path.is_file():
        return None
    try:
        return RetrievalIndex.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception:
        return None


@app.post("/api/practice")
def practice(payload: PracticePayload):
    index = _load_index(payload.artifact_id)
    if index is None:
        raise HTTPException(404, "这份讲义还没有检索索引")
    chunks = [c for c in index.chunks if not payload.section or c.section == payload.section]
    if not chunks:
        chunks = index.chunks
    count = max(1, min(int(payload.count or 3), 5))
    ctx = retrieval_context(chunks[:10])
    system = (
        "你是命题助教。只依据资料片段出题，题目要能独立回答，覆盖不同知识点。"
        "只输出 JSON：{\"questions\":[{\"question\":\"...\",\"answer\":\"...\","
        "\"explanation\":\"...\",\"page\":\"6\"}]}。不要 Markdown。"
    )
    user = f"资料片段：\n{ctx}\n\n请出 {count} 道题。"
    try:
        data = DeepSeekClient().json(system, user, max_tokens=1800, temperature=0.2)
    except LLMError as exc:
        raise HTTPException(503, str(exc)) from exc
    qs = data.get("questions") or []
    if not isinstance(qs, list) or not qs:
        raise HTTPException(502, "模型没有返回题目")
    return {"questions": qs[:count], "section": payload.section}


@app.get("/api/chat/{artifact_id}")
def get_chat(artifact_id: str, session_id: str = "default"):
    return {"messages": list_chat(artifact_id, session_id)}


@app.delete("/api/chat/{artifact_id}")
def delete_chat(artifact_id: str, session_id: str = "default"):
    clear_chat(artifact_id, session_id)
    return {"ok": True}


@app.post("/api/ask")
def ask(payload: AskPayload):
    q = (payload.question or "").strip()
    if not q:
        raise HTTPException(400, "问题不能为空")
    selection = (payload.selection or "").strip()[:1200]
    index = _load_index(payload.artifact_id)
    src = []
    if index is not None:
        chunks = expand_neighbors(index, search(index, q, top_k=6, selection=selection), max_chunks=10)
        ctx = retrieval_context(chunks)
        src = retrieval_sources(chunks)
    else:
        ctx = (payload.context or "").strip()[:8000]
    mode = (payload.mode or "explain").strip()
    prev = next((m.content for m in reversed(payload.history) if m.role == "assistant"), "")
    if mode == "rewrite":
        src = []
        system = ("你是教材编辑。只输出改写后的段落，不要解释、不要列来源、不要加标题；"
                  "保留原意和术语，句子更适合基础较弱的学生。")
        user = f"原文：{selection or q}\n要求：把这段改写得更通俗，但不要改变事实。"
    elif mode == "quiz":
        system = ("你是课程助教。基于资料片段出 1 道小题：先给题干，再给答案和一句解析；"
                  "不要编资料外的内容；公式用 $...$ 或 $$...$$。")
        user = f"资料片段：\n{ctx or '（无）'}\n\n选中的内容：{selection}\n\n请出题。"
    elif mode == "plan":
        system = ("你是学习规划助教。基于资料片段给 7 天复习计划；每天写重点和一个小练习；"
                  "不要编资料外的章节；中文。")
        user = f"资料片段：\n{ctx or '（无）'}\n\n请给计划。"
    else:
        qtype = "步骤" if any(k in q for k in ("怎么", "如何", "步骤", "计算", "求")) else (
            "对比" if any(k in q for k in ("为什么", "区别", "比较", "不同")) else "概念")
        system = (
            "你是 TermFinale 的课程助教。优先依据“检索到的资料片段”回答；"
            "片段没有覆盖的内容就明确说“这份讲义没有覆盖”，不要编页码/定理/答案。"
            f"本题类型：{qtype}。请按问题需要组织答案：概念题直接给定义+一个关键证据；"
            "对比题先给对比结论再列 2-3 个差异；步骤题按步骤写；不要每道题都套“结论→拆开说”的长模板，"
            "短问题就短答，避免重复上一轮的说法。引用片段里的小节名和页码；公式用 $...$ 或 $$...$$；中文、耐心。"
        )
        user = f"检索到的资料片段：\n{ctx or '（无）'}\n\n学生问题：{q}"
        if selection:
            user += f"\n\n学生选中的片段：{selection}"
        if prev:
            user += "\n\n如果上一轮回答已经覆盖这个问题，请补充新的角度，不要原样重复。"
    if (payload.lang or "zh").lower().startswith("en"):
        system += " Answer in English unless the user explicitly asks for Chinese; keep source terms in their original form."
    history = [m.model_dump() for m in payload.history]
    if not history and payload.artifact_id:
        history = [{"role": m["role"], "content": m["content"]}
                   for m in list_chat(payload.artifact_id, payload.session_id)]
    recent = history[-20:]
    older = history[:-20]
    summary = ""
    try:
        client = DeepSeekClient()
        if older:
            transcript = "\n".join(f"{m['role']}：{m['content'][:400]}" for m in older[-30:])
            summary = client.chat(
                "把以下课程对话压缩成不超过 300 字的摘要，保留学生已问过的概念、已解决的疑问和未完成的问题。",
                transcript, max_tokens=400, temperature=0.1)
    except LLMError as exc:
        raise HTTPException(503, str(exc)) from exc
    if summary:
        user = f"更早对话摘要：{summary}\n\n" + user
    try:
        answer = client.chat_messages(system, recent + [{"role": "user", "content": user}],
                                      max_tokens=2048, temperature=0.45)
    except LLMError as exc:
        raise HTTPException(503, str(exc)) from exc
    answer = answer.strip()
    # 模型偶尔用 \[...\]/\(...\)；统一成 KaTeX 能渲染的 $$...$$/$...$
    answer = answer.replace("\\[", "$$").replace("\\]", "$$")
    answer = answer.replace("\\(", "$").replace("\\)", "$")
    if not answer:
        raise HTTPException(502, "模型没有返回内容")
    if payload.artifact_id:
        append_chat(payload.artifact_id, payload.session_id, "user", q)
        append_chat(payload.artifact_id, payload.session_id, "assistant", answer)
    return {"answer": answer, "sources": src}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("TFV2_PORT", "8905")))

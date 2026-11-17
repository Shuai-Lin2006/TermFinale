"""Agent P0：安全工具注册表 + 意图规划 + 只读/学习工具。

写操作只返回 action/确认，不直接改库；所有结果带页码出处。
"""
from __future__ import annotations

import json
import re
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from tfv2.product import service, store

TOOLS = {
    "search_material": {"scope": "read", "desc": "在当前讲义中检索段落",
                        "args": {"artifact_id": "讲义 ID", "query": "检索词"}},
    "read_page": {"scope": "read", "desc": "读某页原文/图注",
                  "args": {"artifact_id": "讲义 ID", "page": "页码（整数）"}},
    "get_artifact": {"scope": "read", "desc": "讲义质量、覆盖、图、目录",
                     "args": {"artifact_id": "讲义 ID"}},
    "get_learning_state": {"scope": "read", "desc": "掌握度、错题、到期", "args": {}},
    "web_search": {"scope": "read", "desc": "联网搜索最新资料（返回 URL/摘要）", "args": {"query": "检索词"}},
    "make_review_plan": {"scope": "read", "desc": "按弱项生成复习计划", "args": {"days": "天数（默认 7）"}},
    "make_practice": {"scope": "action", "desc": "跳转练习并出题",
                      "args": {"artifact_id": "讲义 ID", "section": "小节 ID（可空）"}},
    "generate_lecture": {"scope": "action", "desc": "新建讲义（需确认）", "args": {}},
    "generate_exam": {"scope": "action", "desc": "出 100 分卷（需确认）",
                      "args": {"artifact_id": "讲义 ID"}},
}


def _sections(aid: str) -> list[dict]:
    path = service.artifact_path(aid)
    if path is None or not (path / "sections.json").is_file():
        return []
    data = json.loads((path / "sections.json").read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def _page_blocks(aid: str, page: int) -> list[dict]:
    out = []
    for sec in _sections(aid):
        for b in sec.get("blocks") or []:
            text = str(b.get("text") or "").strip()
            if not text:
                continue
            for ref in b.get("source_refs") or []:
                try:
                    if int(ref.get("page_start", 0)) <= page <= int(ref.get("page_end") or ref.get("page_start")):
                        out.append({"section": sec.get("title"), "page": page, "text": text})
                        break
                except Exception:
                    continue
    return out


def search_material(aid: str, query: str) -> dict:
    q = (query or "").strip()
    if not q:
        return {"ok": False, "error": "缺少检索词", "citations": []}
    terms = [x for x in re.split(r"\s+", q) if x][:5]
    hits = []
    for sec in _sections(aid):
        for b in sec.get("blocks") or []:
            text = str(b.get("text") or "")
            if any(t.lower() in text.lower() for t in terms):
                page = None
                for ref in b.get("source_refs") or []:
                    page = ref.get("page_start"); break
                hits.append({"section": sec.get("title"), "page": page, "text": text[:300]})
    return {"ok": True, "data": hits[:6], "citations": [h["page"] for h in hits[:6] if h["page"]]}


def read_page(aid: str, page: int) -> dict:
    rows = _page_blocks(aid, page)
    return {"ok": bool(rows), "data": rows[:8], "citations": [page] if rows else []}


def get_artifact(aid: str) -> dict:
    a = service.get_artifact(aid) or {}
    return {"ok": bool(a), "data": {k: a.get(k) for k in ("title", "quality", "coverage", "sections", "figures")},
            "citations": []}


def get_learning_state() -> dict:
    data = service.review_data()
    return {"ok": True, "data": data, "citations": []}


def make_review_plan(days: int = 7) -> dict:
    data = service.review_data()
    weak = [m for m in data.get("mastery") or [] if m.get("label") == "weak"][:6]
    due = data.get("due") or []
    plan = []
    for d in range(1, max(1, min(14, days)) + 1):
        items = []
        if due and d <= 3:
            items.append(f"清 {min(len(due), 5)} 道到期错题")
        if weak:
            w = weak[(d - 1) % len(weak)]
            items.append(f"补弱项：{w.get('section')}（掌握分 {w.get('score')}）")
        if not items:
            items.append("新题 5 道 + 回看错题")
        plan.append({"day": d, "tasks": items})
    return {"ok": True, "data": {"days": plan, "weak": weak, "due_count": len(due)}, "citations": []}


def plan(goal: str, artifact_id: str = "", page: int | None = None) -> list[dict]:
    g = (goal or "").lower()
    if any(k in g for k in ("复习", "计划", "review", "plan")):
        return [{"tool": "make_review_plan", "args": {"days": 7}}]
    if any(k in g for k in ("出题", "练习", "quiz", "practice")):
        return [{"tool": "make_practice", "args": {"artifact_id": artifact_id, "section": ""}}]
    if any(k in g for k in ("出卷", "试卷", "exam")):
        return [{"tool": "generate_exam", "args": {"artifact_id": artifact_id}}]
    if any(k in g for k in ("新建", "讲义", "lecture", "生成")):
        return [{"tool": "generate_lecture", "args": {}}]
    if page:
        return [{"tool": "read_page", "args": {"artifact_id": artifact_id, "page": page}}]
    return [{"tool": "search_material", "args": {"artifact_id": artifact_id, "query": goal}},
            {"tool": "get_artifact", "args": {"artifact_id": artifact_id}}]






PLANNER_SYSTEM = """你是 TermFinale 的任务规划器。只输出 JSON，不解释。
可用工具：
- search_material {artifact_id, query}
- read_page {artifact_id, page}
- get_artifact {artifact_id}
- get_learning_state {}
- make_review_plan {days}
- make_practice {artifact_id, section}
- generate_exam {artifact_id}
- generate_lecture {}
规则：
1. 步数不设固定上限；只规划可验证的步骤；只读工具可直接执行；generate_exam/generate_lecture/make_practice 标 requires_confirmation=true。
2. 不要编造工具；不要输出 shell/文件工具。需要最新外部信息时用 web_search（联网只读）。
3. 先检索/读页，再生成；生成讲义需要上传，使用 generate_lecture 只会得到 action。
4. 输出：{"goal":"...","steps":[{"tool":"search_material","args":{...},"why":"...","requires_confirmation":false}]}
"""


def _validate_steps(data: dict, artifact_id: str, page: int | None) -> list[dict]:
    steps = data.get("steps")
    if not isinstance(steps, list) or not steps:
        raise ValueError("planner 没有 steps")
    out = []
    for s in steps:
        if not isinstance(s, dict):
            continue
        tool = str(s.get("tool") or "")
        if tool not in TOOLS:
            continue
        args = s.get("args") if isinstance(s.get("args"), dict) else {}
        if tool in ("search_material", "read_page", "get_artifact") and not args.get("artifact_id"):
            args["artifact_id"] = artifact_id
        if tool == "read_page" and not args.get("page"):
            args["page"] = page or 1
        out.append({"tool": tool, "args": args, "why": str(s.get("why") or ""),
                    "requires_confirmation": tool in ("generate_exam", "generate_lecture", "make_practice")})
    if not out:
        raise ValueError("planner 没有合法工具")
    return out


def plan_with_llm(goal: str, *, artifact_id: str = "", page: int | None = None, client=None, memory: list[str] | None = None) -> dict:
    if client is None:
        try:
            from tfv2.llm.client import DeepSeekClient
            client = DeepSeekClient()
        except Exception:
            client = None
    if client is not None:
        a = service.get_artifact(artifact_id) or {}
        ctx = {"goal": goal, "artifact": {"id": artifact_id, "title": a.get("title"), "quality": (a.get("quality") or {}).get("status"),
                                          "sections": a.get("sections"), "figures": a.get("figures")}, "page": page,
               "memory": (memory or [])[:3]}
        try:
            data = client.json(PLANNER_SYSTEM, json.dumps(ctx, ensure_ascii=False), max_tokens=1800, temperature=0.2)
            steps = _validate_steps(data, artifact_id, page)
            return {"goal": goal, "steps": steps, "needs_confirmation": any(s["requires_confirmation"] for s in steps),
                    "planner": "llm", "note": "LLM 规划；生成/出卷需确认。" if any(s["requires_confirmation"] for s in steps) else "LLM 规划；只读/学习工具。"}
        except Exception:
            pass
    meta = plan_with_meta(goal, artifact_id, page)
    meta["planner"] = "fallback"
    return meta

def plan_with_meta(goal: str, artifact_id: str = "", page: int | None = None) -> dict:
    steps = plan(goal, artifact_id, page)
    need = [s for s in steps if s["tool"] in ("generate_exam", "generate_lecture", "make_practice")]
    for s in steps:
        s["requires_confirmation"] = s["tool"] in ("generate_exam", "generate_lecture")
    return {"goal": goal, "steps": steps, "needs_confirmation": bool(need),
            "note": "生成/出卷会消耗模型调用，需确认后执行。" if need else "只读/学习工具，可直接执行。"}


def _exam_count(goal: str) -> int:
    m = re.search(r"(\d+)\s*(?:道)?\s*题", goal or "")
    if not m:
        return 12
    return max(12, min(30, int(m.group(1))))


def _course_subject(aid: str) -> str:
    a = service.get_artifact(aid) or {}
    course = str(a.get("course") or a.get("course_name") or "")
    for s in ("电路", "物理", "高等数学", "化学", "计算机", "生物", "医学", "文科"):
        if s in course or s in str(a.get("title") or ""):
            return s
    return "其他"


def execute_action(tool: str, args: dict, *, goal: str = "", progress=None) -> dict:
    if tool == "generate_exam":
        from tfv2.product import exam
        aid = str(args.get("artifact_id") or "")
        if not aid:
            return {"ok": False, "error": "缺少讲义"}
        n = _exam_count(goal)
        subject = _course_subject(aid)
        if progress:
            progress(8, f"出卷：{subject} / {n} 题")
        doc = exam.run_exam(
            aid, mode="mock", subject=subject, difficulty=3, types="choice",
            blueprint_text=f"选择题 {n} 题 100 分", work=None,
            progress=(lambda pct, step: progress(8 + int(pct * 0.8), step)) if progress else None,
        )
        did = store.save_document(doc)
        doc["id"] = did
        return {"ok": True, "data": {"id": did, "title": doc.get("title"), "status": doc.get("status"),
                                     "total_score": doc.get("content", {}).get("total_score"),
                                     "questions": sum(len(s.get("questions") or []) for s in doc.get("content", {}).get("sections") or [])},
                "citations": []}
    if tool == "generate_lecture":
        return {"ok": False, "error": "新建讲义需要上传资料，请用“去新建讲义”", "requires_upload": True}
    if tool == "make_practice":
        return {"ok": True, "data": {"section": args.get("section") or ""}, "citations": []}
    return {"ok": False, "error": f"未知动作 {tool}"}




READ_TOOLS = {"search_material", "read_page", "get_artifact", "get_learning_state", "make_review_plan", "web_search"}


def _execute_tool(tool: str, args: dict, *, goal: str, artifact_id: str, page: int | None, progress=None) -> dict:
    aid = str(args.get("artifact_id") or artifact_id)
    if tool in ("generate_exam", "generate_lecture", "make_practice"):
        return execute_action(tool, args, goal=goal, progress=progress)
    if tool == "make_review_plan":
        return make_review_plan(int(args.get("days", 7)))
    if tool == "search_material":
        return search_material(aid, str(args.get("query") or goal))
    if tool == "read_page":
        return read_page(aid, int(args.get("page") or page or 1))
    if tool == "get_artifact":
        return get_artifact(aid)
    if tool == "get_learning_state":
        return get_learning_state()
    if tool == "web_search":
        from tfv2.product import websearch
        data = websearch.search_and_fetch(str(args.get("query") or goal), count=5, fetch_top=2)
        rows = data.get("results") or []
        return {"ok": bool(rows), "data": rows, "citations": [str(x.get("url") or "") for x in rows[:5]]}
    return {"ok": False, "error": f"未知工具 {tool}", "citations": []}



def _topo_order(steps: list[dict]) -> list[dict]:
    """按 depends_on 做拓扑排序；支持 step id 或 0-based 下标。有环则原序。"""
    if not any(isinstance(s.get("depends_on"), list) and s.get("depends_on") for s in steps):
        return steps
    ids = {str(s.get("id") or f"s{i}"): i for i, s in enumerate(steps)}
    for i, s in enumerate(steps):
        s.setdefault("id", f"s{i}")
    indeg = {i: 0 for i in range(len(steps))}
    edges = {i: [] for i in range(len(steps))}
    for i, s in enumerate(steps):
        for dep in s.get("depends_on") or []:
            j = ids.get(str(dep), dep if isinstance(dep, int) else None)
            if isinstance(j, int) and 0 <= j < len(steps) and j != i:
                edges[j].append(i); indeg[i] += 1
    q = [i for i in range(len(steps)) if indeg[i] == 0]
    out = []
    while q:
        i = q.pop(0); out.append(steps[i])
        for j in edges[i]:
            indeg[j] -= 1
            if indeg[j] == 0:
                q.append(j)
    return out if len(out) == len(steps) else steps



def _topo_levels(steps: list[dict]) -> list[list[dict]]:
    """按 depends_on 分层；返回同层可并行的步骤。有环则一层全跑。"""
    if not any(s.get("depends_on") for s in steps):
        return [steps]
    ids = {str(s.get("id") or f"s{i}"): i for i, s in enumerate(steps)}
    for i, s in enumerate(steps):
        s.setdefault("id", f"s{i}")
    indeg = {i: 0 for i in range(len(steps))}
    edges = {i: [] for i in range(len(steps))}
    for i, s in enumerate(steps):
        for dep in s.get("depends_on") or []:
            j = ids.get(str(dep), dep if isinstance(dep, int) else None)
            if isinstance(j, int) and 0 <= j < len(steps) and j != i:
                edges[j].append(i); indeg[i] += 1
    levels, done = [], set()
    while len(done) < len(steps):
        level = [i for i in range(len(steps)) if i not in done and indeg[i] == 0]
        if not level:
            return [steps]
        levels.append([steps[i] for i in level])
        for i in level:
            done.add(i)
            for j in edges[i]:
                indeg[j] -= 1
    return levels


def _run_batch(steps: list[dict], *, goal: str, artifact_id: str, page: int | None, progress=None,
               resume: bool = False) -> dict:
    trace, actions, citations = [], [], []
    pending = [s for s in steps if not (resume and s.get("result") and s.get("ok") is not False)]
    skipped = [s for s in steps if resume and s.get("result") and s.get("ok") is not False]
    for s in skipped:
        trace.append({"tool": s["tool"], "ok": True, "error": None, "attempts": 0, "skipped": True})
        citations.extend((s.get("result") or {}).get("citations") or [])
    if len(pending) > 1 and all(s["tool"] in READ_TOOLS for s in pending):
        with ThreadPoolExecutor(max_workers=min(4, len(pending))) as pool:
            futures = [(st, pool.submit(_execute_tool, st["tool"], st.get("args") or {}, goal=goal,
                                        artifact_id=artifact_id, page=page, progress=progress)) for st in pending]
            for st, fut in futures:
                try: res = fut.result()
                except Exception as exc: res = {"ok": False, "error": str(exc), "citations": []}
                st["result"] = res; st["ok"] = bool(res.get("ok"))
                trace.append({"tool": st["tool"], "ok": st["ok"], "error": res.get("error"), "attempts": 1, "parallel": True})
                citations.extend(res.get("citations") or [])
    else:
        for st in pending:
            tool, args = st["tool"], st.get("args") or {}
            attempts = 1 if tool in ("generate_exam", "generate_lecture", "make_practice") else 2
            res, used = {"ok": False, "error": "未执行", "citations": []}, 0
            for attempt in range(attempts):
                used = attempt + 1
                res = _execute_tool(tool, args, goal=goal, artifact_id=artifact_id, page=page, progress=progress)
                if res.get("ok"):
                    break
            if not res.get("ok") and tool == "read_page":
                alt = search_material(artifact_id, goal)
                if alt.get("ok"):
                    res = alt; trace.append({"tool": "search_material", "ok": True, "error": None, "attempts": 0, "repaired": True})
                    citations.extend(alt.get("citations") or [])
            st["result"] = res; st["ok"] = bool(res.get("ok"))
            trace.append({"tool": tool, "ok": st["ok"], "error": res.get("error"), "attempts": used})
            citations.extend(res.get("citations") or [])
            if tool == "generate_exam" and res.get("ok"):
                actions.append({"label": "打开试卷", "href": "#/exam"})
            if tool == "make_practice" and res.get("ok"):
                actions.append({"label": "去练习", "href": f"#/practice/{artifact_id}" if artifact_id else "#/practice"})
    return {"trace": trace, "actions": actions, "citations": citations}

def run_workflow(goal: str, *, artifact_id: str = "", page: int | None = None, confirm: bool = False,
                 progress=None, use_llm: bool = False, steps: list[dict] | None = None,
                 on_step=None, resume: bool = False, auto_repair: bool = False, max_repairs: int = 2) -> dict:
    if steps:
        cleaned = []
        for s in steps:
            if not isinstance(s, dict) or s.get("tool") not in TOOLS:
                continue
            cleaned.append({"tool": s["tool"], "args": s.get("args") if isinstance(s.get("args"), dict) else {},
                            "why": s.get("why") or "", "requires_confirmation": s.get("tool") in ("generate_exam", "generate_lecture", "make_practice"),
                            **({"id": s["id"]} if s.get("id") else {}),
                            **({"depends_on": s["depends_on"]} if s.get("depends_on") else {}),
                            **({"result": s["result"], "ok": s["ok"]} if s.get("result") and "ok" in s else {})})
        meta = {"goal": goal, "steps": cleaned, "needs_confirmation": any(x["requires_confirmation"] for x in cleaned), "planner": "confirmed"}
        if not cleaned:
            meta = plan_with_meta(goal, artifact_id, page)
    else:
        memory = store.recall_memory(goal, artifact_id)
        meta = plan_with_llm(goal, artifact_id=artifact_id, page=page, memory=memory) if use_llm else plan_with_meta(goal, artifact_id, page)
    if meta.get("needs_confirmation") and not confirm:
        return {"goal": goal, "needs_confirmation": True, "plan": meta["steps"],
                "answer": "这个任务会调用模型生成内容；确认后执行。"}
    meta["steps"] = _topo_order(meta["steps"])
    has_deps = any(isinstance(s.get("depends_on"), list) and s.get("depends_on") for s in meta["steps"])
    if has_deps:
        trace, actions, citations = [], [], []
        for level in _topo_levels(meta["steps"]):
            batch = _run_batch(level, goal=goal, artifact_id=artifact_id, page=page, progress=progress, resume=resume)
            trace.extend(batch["trace"]); actions.extend(batch["actions"]); citations.extend(batch["citations"])
            if on_step:
                try: on_step(meta["steps"])
                except Exception: pass
        return {"goal": goal, "needs_confirmation": False, "plan": meta["steps"], "trace": trace,
                "answer": "\n".join(f"{t['tool']}：{'完成' if t.get('ok') else '失败 ' + str(t.get('error') or '')}" for t in trace),
                "citations": sorted({c for c in citations if isinstance(c, int)}), "actions": actions,
                "ok": all(t.get("ok") for t in trace) if trace else False,
                "failed_step": next((i for i, t in enumerate(trace) if not t.get("ok")), None)}
    trace, actions, citations = [], [], []
    if not has_deps and len(meta["steps"]) > 1 and all(s["tool"] in READ_TOOLS for s in meta["steps"]):
        # 独立只读步骤并行；任一失败仍保留其他结果
        with ThreadPoolExecutor(max_workers=min(4, len(meta["steps"]))) as pool:
            futures = [(st, (None if resume and st.get("result") and st.get("ok") is not False else
                             pool.submit(_execute_tool, st["tool"], st.get("args") or {}, goal=goal,
                                         artifact_id=artifact_id, page=page, progress=progress)))
                       for st in meta["steps"]]
            for st, fut in futures:
                if fut is None:
                    trace.append({"tool": st["tool"], "ok": True, "error": None, "attempts": 0, "skipped": True, "parallel": True})
                    citations.extend((st.get("result") or {}).get("citations") or [])
                    continue
                try:
                    res = fut.result()
                except Exception as exc:
                    res = {"ok": False, "error": str(exc), "citations": []}
                st["result"] = res; st["ok"] = bool(res.get("ok"))
                trace.append({"tool": st["tool"], "ok": st["ok"], "error": res.get("error"), "attempts": 1, "parallel": True})
                citations.extend(res.get("citations") or [])
        if on_step:
            try:
                on_step(meta["steps"])
            except Exception:
                pass
    else:
      for st in meta["steps"]:
          tool = st["tool"]; args = st.get("args") or {}
          if resume and st.get("result") and st.get("ok") is not False:
              trace.append({"tool": tool, "ok": True, "error": None, "attempts": 0, "skipped": True})
              citations.extend((st.get("result") or {}).get("citations") or [])
              continue
          def _call() -> dict:
              return _execute_tool(tool, args, goal=goal, artifact_id=artifact_id, page=page, progress=progress)

          attempts = 1 if tool in ("generate_exam", "generate_lecture", "make_practice") else 2
          res = {"ok": False, "error": "未执行", "citations": []}
          used = 0
          for attempt in range(attempts):
              used = attempt + 1
              res = _call()
              if res.get("ok"):
                  break
          if not res.get("ok") and tool == "read_page":
              alt = search_material(artifact_id, goal)
              if alt.get("ok"):
                  res = alt; trace.append({"tool": "search_material", "ok": True, "error": None, "attempts": 0, "repaired": True})
                  citations.extend(alt.get("citations") or [])
          if tool == "generate_exam" and res.get("ok"):
              actions.append({"label": "打开试卷", "href": "#/exam"})
          if tool == "make_practice" and res.get("ok"):
              actions.append({"label": "去练习", "href": f"#/practice/{artifact_id}" if artifact_id else "#/practice"})
          st["result"] = res; st["ok"] = bool(res.get("ok"))
          trace.append({"tool": tool, "ok": st["ok"], "error": res.get("error"), "attempts": used})
          citations.extend(res.get("citations") or [])
          if on_step:
              try:
                  on_step(meta["steps"])
              except Exception:
                  pass
    repair_diff = ""
    repaired_ok = False
    if auto_repair and trace and any(not t.get("ok") for t in trace) and max_repairs > 0:
        failed = next((st for st in meta["steps"] if st.get("ok") is False), None)
        if failed:
            rep = replan_remaining(goal, artifact_id=artifact_id, steps=meta["steps"],
                                   failed_tool=str(failed.get("tool") or ""),
                                   error=str((failed.get("result") or {}).get("error") or ""))
            new_steps = [s for s in (rep.get("steps") or []) if s.get("tool") in READ_TOOLS][:2]
            if new_steps:
                batch = _run_batch(new_steps, goal=goal, artifact_id=artifact_id, page=page, progress=progress)
                trace.extend(batch["trace"]); actions.extend(batch["actions"]); citations.extend(batch["citations"])
                repair_diff = rep.get("diff") or ""
                repaired_ok = bool(batch["trace"]) and all(t.get("ok") for t in batch["trace"])
                if on_step:
                    try: on_step(meta["steps"] + new_steps)
                    except Exception: pass
    # 简化答案
    parts = []
    for st in meta["steps"]:
        r = st.get("result") or {}
        if st["tool"] == "make_review_plan":
            d = r.get("data") or {}
            parts.append("7 天复习计划：\n" + "\n".join(f"第 {x['day']} 天：" + "；".join(x["tasks"]) for x in d.get("days") or []))
        elif st["tool"] == "generate_exam":
            d = r.get("data") or {}
            parts.append(f"试卷：{d.get('title')}，{d.get('questions')} 题，{d.get('total_score')} 分，状态 {d.get('status')}")
        elif r.get("ok"):
            rows = r.get("data") or []
            parts.append(f"{st['tool']}：完成" + (f"，{len(rows)} 条" if isinstance(rows, list) else ""))
        else:
            parts.append(f"{st['tool']}：失败 {r.get('error') or ''}")
    return {"goal": goal, "needs_confirmation": False, "plan": meta["steps"], "trace": trace,
            "answer": "\n".join(parts), "citations": sorted({c for c in citations if isinstance(c, int)}), "actions": actions,
            "ok": (all(t.get("ok") for t in trace) if trace else False) or repaired_ok,
            "failed_step": next((i for i, t in enumerate(trace) if not t.get("ok")), None),
            "repair_diff": repair_diff, "auto_repair": bool(auto_repair), "repaired_ok": repaired_ok}



def replan_remaining(goal: str, *, artifact_id: str = "", steps: list[dict] | None = None,
                     failed_tool: str = "", error: str = "", client=None) -> dict:
    import difflib
    steps = steps or []
    done = [s for s in steps if s.get("ok")]
    remaining = [s for s in steps if not s.get("ok")]
    if client is None:
        try:
            from tfv2.llm.client import DeepSeekClient
            client = DeepSeekClient()
        except Exception:
            client = None
    if client is not None:
        system = PLANNER_SYSTEM + "\n这是失败后的重规划：只输出剩余步骤，不要重复已完成步骤；最多 3 步；必须换一个可行工具或参数。"
        user = json.dumps({"goal": goal, "artifact_id": artifact_id, "failed_tool": failed_tool,
                           "error": error, "done": [{"tool": s.get("tool"), "args": s.get("args")} for s in done],
                           "remaining_old": [{"tool": s.get("tool"), "args": s.get("args")} for s in remaining]}, ensure_ascii=False)
        try:
            data = client.json(system, user, max_tokens=1400, temperature=0.2)
            new = _validate_steps(data, artifact_id, None)
            new = [x for x in new if x["tool"] != failed_tool][:3] or new
            return {"ok": True, "steps": new, "diff": _diff_steps(remaining, new), "planner": "llm"}
        except Exception as exc:
            pass
    fallback = []
    if failed_tool != "search_material":
        fallback.append({"tool": "search_material", "args": {"artifact_id": artifact_id, "query": goal}, "why": "读取失败后改为检索"})
    fallback += [x for x in remaining if x.get("tool") != failed_tool][:2]
    return {"ok": bool(fallback), "steps": fallback,
            "diff": _diff_steps(remaining, fallback), "planner": "fallback", "error": error}


def _diff_steps(before: list[dict], after: list[dict]) -> str:
    import difflib
    a = json.dumps(before, ensure_ascii=False, indent=2).splitlines()
    b = json.dumps(after, ensure_ascii=False, indent=2).splitlines()
    return "\n".join(difflib.unified_diff(a, b, fromfile="old", tofile="replanned", lineterm=""))



def run_due_goals() -> list[dict]:
    """常驻调度：只自动执行不需要确认的步骤；生成/出卷保留计划等用户确认。"""
    out = []
    for g in store.due_auto_goals():
        goal = str(g.get("goal") or "")
        aid = str(g.get("artifact_id") or "")
        try:
            meta = plan_with_llm(goal, artifact_id=aid)
            if meta.get("needs_confirmation"):
                res = {"goal": goal, "needs_confirmation": True, "plan": meta.get("steps") or [],
                       "answer": "到期目标包含生成/出卷，已生成计划，等待确认。"}
            else:
                res = run_workflow(goal, artifact_id=aid, confirm=False)
            store.advance_goal(int(g["id"]), 1)
            out.append({"goal_id": g["id"], "goal": goal, "ok": True,
                        "needs_confirmation": bool(res.get("needs_confirmation")), "answer": res.get("answer", "")})
        except Exception as exc:
            out.append({"goal_id": g["id"], "goal": goal, "ok": False, "error": str(exc)})
    return out

def run_agent(goal: str, *, artifact_id: str = "", page: int | None = None) -> dict:
    steps = plan(goal, artifact_id, page)
    trace = []
    actions = []
    citations = []
    for step in steps:
        tool = step["tool"]
        args = step.get("args") or {}
        if tool == "make_review_plan":
            res = make_review_plan(int(args.get("days", 7)))
        elif tool == "search_material":
            res = search_material(artifact_id, str(args.get("query") or goal))
        elif tool == "read_page":
            res = read_page(artifact_id, int(args.get("page") or page or 1))
        elif tool == "get_artifact":
            res = get_artifact(artifact_id)
        elif tool == "get_learning_state":
            res = get_learning_state()
        elif tool == "make_practice":
            res = {"ok": True, "data": {"section": args.get("section") or ""}, "citations": []}
            actions.append({"label": "去练习", "href": f"#/practice/{artifact_id}" if artifact_id else "#/practice"})
        elif tool == "generate_exam":
            res = {"ok": True, "data": {}, "citations": []}
            actions.append({"label": "去出卷（需确认）", "href": "#/exam"})
        elif tool == "generate_lecture":
            res = {"ok": True, "data": {}, "citations": []}
            actions.append({"label": "去新建讲义（需确认）", "href": "#/new"})
        else:
            res = {"ok": False, "error": f"未知工具 {tool}", "citations": []}
        trace.append({"tool": tool, "args": args, "ok": res.get("ok"), "error": res.get("error")})
        citations.extend(res.get("citations") or [])
        step["result"] = res
        step["ok"] = bool(res.get("ok"))
    # 生成可读答案
    if steps and steps[0]["tool"] == "make_review_plan":
        d = steps[0]["result"].get("data") or {}
        lines = ["给你一份 7 天复习计划："]
        for day in d.get("days") or []:
            lines.append(f"第 {day['day']} 天：" + "；".join(day["tasks"]))
        answer = "\n".join(lines)
    elif steps and steps[0]["tool"] == "read_page":
        rows = steps[0]["result"].get("data") or []
        answer = f"第 {page or 1} 页找到 {len(rows)} 段：\n" + "\n".join(f"· {r['text'][:180]}" for r in rows)
    else:
        hits = []
        for st in steps:
            hits.extend((st.get("result") or {}).get("data") or []) if isinstance((st.get("result") or {}).get("data"), list) else None
        answer = f"我按“{goal}”查了讲义。" + (f"找到 {len(hits)} 条相关段落，见下方引用。" if hits else "没有找到直接匹配，请换关键词或指定页码。")
    return {"goal": goal, "plan": steps, "trace": trace, "answer": answer,
            "citations": sorted({c for c in citations if isinstance(c, int)}), "actions": actions}

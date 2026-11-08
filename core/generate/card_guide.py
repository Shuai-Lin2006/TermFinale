"""证据卡驱动讲义：程序掌控引文/页码，模型只解释每张证据卡。

每 5 张卡一次 JSON；引文由程序从资料原句填入，模型无法伪造页码。
坏卡/坏批量只回退为“原文要点”，不阻塞整章；没有证据卡才返回空。
"""
from __future__ import annotations

import json
import re

from core.exam_engine import call_ai_with_retry
from core.generate.evidence_pack import Evidence, build_pack

PAGE_SPLIT = re.compile(r"(?=【《.+?》第\s*\d+\s*页】)")
_MAT_PREFIX = re.compile(r"【[^】]*(?:重点资料|辅助资料|本章资料|权重)[^】]*】\s*")
BATCH = 6


def _clean_explain(text: str, bans: list[str]) -> str:
    t = re.sub(r"\s+", " ", str(text or "")).strip()
    t = re.sub(r"[（(]\s*P?\.?\s*\d+\s*[)）]", "", t)
    if len(t) < 8:
        return ""
    if any(b and b in t for b in bans):
        return ""
    return t[:500]


def _parse_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except Exception:
        return {}


def _explain_batch(batch: list[Evidence], title: str, weak: str, bans: list[str],
                   ai_call=None) -> dict[str, str]:
    lines = "\n".join(f"[{e.eid}｜P.{e.page}] {e.quote}" for e in batch)
    sys_p = f"""你是大学期末讲义编辑。下面每张卡是资料里的原句，你只能解释这些原句。
要求：
1. 每张卡写 60–180 字通俗讲解，面向基础一般的大学生；
2. 不得新增资料没有的事实、数字、定理编号、例题数据；
3. 不得出现老师禁用的内容；不要写“如图”除非原句有图；
4. 只输出 JSON：{{"cards":[{{"eid":"E1","explain":"..."}}]}}
{('5. 学生薄弱点必须多讲：' + weak) if weak else ''}
"""
    user = f"章节：{title}\n\n证据卡：\n{lines}"
    try:
        raw = (ai_call or call_ai_with_retry)(sys_p, user, temp=0.2, min_budget=1800)
    except Exception:
        raw = ""
    data = _parse_json(raw)
    out = {}
    for item in data.get("cards") or []:
        eid = str(item.get("eid") or "").strip()
        exp = _clean_explain(item.get("explain") or "", bans)
        if eid and exp:
            out[eid] = exp
    if not out:
        # 一次纠错，仍失败则整批回退为原文
        try:
            raw2 = (ai_call or call_ai_with_retry)(
                sys_p + "\n上一轮不是有效 JSON；请只输出 JSON。", user,
                temp=0.1, min_budget=1800)
            for item in (_parse_json(raw2).get("cards") or []):
                eid = str(item.get("eid") or "").strip()
                exp = _clean_explain(item.get("explain") or "", bans)
                if eid and exp:
                    out[eid] = exp
        except Exception:
            pass
    return out


def _fallback_cards(pages: list[str], page_hints: list[int] | None = None) -> list[Evidence]:
    """无可用证据句时，用该页最长正文/图注兜底；不编内容，只保留来源。"""
    out = []
    for i, page in enumerate(pages, 1):
        m = re.search(r"》\s*第\s*(\d+)\s*页】", page or "")
        n = int(m.group(1)) if m else (page_hints[i - 1] if page_hints and i - 1 < len(page_hints) else i)
        clean = _MAT_PREFIX.sub("", page or "")
        clean = re.sub(r"^【《[^》]+》[^】]*】", "", clean).strip()
        lines = [re.sub(r"\s+", " ", x).strip() for x in clean.splitlines() if x.strip()]
        lines = [re.sub(r"第\s*\d+\s*页", "", x).strip() for x in lines]
        lines = [x for x in lines if "[[[IMAGE:" not in x and len(x) >= 6]
        lines = [x for x in lines if not re.fullmatch(r"【[^】]{0,20}】", x)]
        if lines:
            quote = max(lines, key=len)[:140]
            out.append(Evidence(f"E{len(out) + 1}", n, quote))
            continue
        imgs = re.findall(r"\[\[\[IMAGE:\s*([^|\]]+)\|\s*图注:\s*(.*?)（第\s*\d+\s*页）\]\]\]", page or "", re.S)
        if imgs:
            quote = f"【图示】{imgs[0][1].strip() or '第' + str(n) + '页图示'}"
            out.append(Evidence(f"E{len(out) + 1}", n, quote))
    return out


def generate_card_chapter(raw_text: str, course=None, persona: str = "老师",
                          user_choice: str = "", weight_prompt: str = "", lang: str = "中文",
                          chapter: dict | None = None, user_note: str = "",
                          constraint_block: str = "", retry_note: str = "",
                          ai_call=None) -> str:
    raw_text = _MAT_PREFIX.sub("", raw_text or "")
    pages = [p for p in PAGE_SPLIT.split(raw_text) if p.strip()]
    _cpp = int((chapter or {}).get("cards_per_page") or 4)
    cards = build_pack(pages, max_per_page=max(1, min(4, _cpp)))
    bans = list((chapter or {}).get("ban_topics") or [])
    if bans:
        cards = [e for e in cards if not any(b in e.quote for b in bans)]
    for e in cards:
        # 卡片页码由程序渲染；引文里残留的“第N页”会被误判为引用
        e.quote = re.sub(r"第\s*\d+\s*页", "", e.quote).strip()
    if not cards:
        cards = _fallback_cards(pages, (chapter or {}).get("chapter_pages"))
    if not cards:
        return ""
    title = str((chapter or {}).get("title") or "本章")
    weak = "、".join((chapter or {}).get("weak_topics") or [])
    out = [f"## 核心考点：{title}"]
    # 章节内按顺序分批；每批 5 张卡
    for start in range(0, len(cards), BATCH):
        batch = cards[start:start + BATCH]
        explanations = _explain_batch(batch, title, weak, bans, ai_call=ai_call)
        out.append(f"### 原文要点 {start + 1}–{start + len(batch)}")
        for e in batch:
            out.append(f"> 原文：{e.quote}（P.{e.page}）")
            exp = explanations.get(e.eid) or "原文直接给出了这一要点，先把原句读懂，再回到资料上下文确认。"
            out.append(f"**讲解**：{exp}")
    return "\n\n".join(out).strip()

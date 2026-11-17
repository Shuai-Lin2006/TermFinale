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
    t = re.sub(r"第\s*\d+\s*页", "", t)
    if len(t) < 8:
        return ""
    if any(b and b in t for b in bans):
        return ""
    return t[:500]


def _math_ok(q: str) -> bool:
    r"""残缺公式不进卡：未闭合 $ / \begin...\end / \(...\) 会在 KaTeX 报错。"""
    q = q or ""
    if q.count("$") % 2 != 0:
        return False
    if q.count("\\(") != q.count("\\)"):
        return False
    if q.count("{") != q.count("}"):
        return False
    if q.count("\\left") != q.count("\\right"):
        return False
    # 截断的长公式极易缺环境/括号，宁可不进卡
    if "\\" in q and len(q) > 120:
        return False
    for env in re.findall(r"\\begin\{([^}]+)\}", q):
        if f"\\end{{{env}}}" not in q:
            return False
    for env in re.findall(r"\\end\{([^}]+)\}", q):
        if f"\\begin{{{env}}}" not in q:
            return False
    return True


def _parse_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except Exception:
        return {}


def _explain_batch(batch: list[Evidence], title: str, weak: str, bans: list[str],
                   ai_call=None) -> tuple[str, dict[str, str]]:
    lines = "\n".join(f"[{e.eid}｜P.{e.page}] {e.quote}" for e in batch)
    sys_p = f"""你是大学期末讲义编辑。下面每张卡是资料里的原句，你只能解释这些原句。
要求：
1. 直接写教材正文，60–180 字，客观、精炼，面向基础一般的大学生；
2. 不要出现“这一页/这里/这句/这段/这张卡/这条说明/你可以/我们/先知道/理解这一点/图示内容”等元话语；不要复述资料页；定义就直接给定义，分类就直接给分类；
3. 不得新增资料没有的事实、数字、定理编号、例题数据；不得出现老师禁用内容；
4. 给这组卡起一个具体的小节标题（如“脂环烃的命名”，不要写“原文要点/第几组”）；
5. 只输出 JSON：{{"section":"小节标题","cards":[{{"eid":"E1","explain":"..."}}]}}
{('6. 学生薄弱点必须多讲：' + weak) if weak else ''}
"""
    user = f"章节：{title}\n\n证据卡：\n{lines}"
    try:
        raw = (ai_call or call_ai_with_retry)(sys_p, user, temp=0.2, min_budget=1800)
    except Exception:
        raw = ""
    data = _parse_json(raw)
    section = str(data.get("section") or "").strip()[:40]
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
            data2 = _parse_json(raw2)
            if not section:
                section = str(data2.get("section") or "").strip()[:40]
            for item in (data2.get("cards") or []):
                eid = str(item.get("eid") or "").strip()
                exp = _clean_explain(item.get("explain") or "", bans)
                if eid and exp:
                    out[eid] = exp
        except Exception:
            pass
    return section, out


def _fallback_cards(pages: list[str], page_hints: list[int] | None = None, bans: list[str] | None = None) -> list[Evidence]:
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
        lines = [x for x in lines if not any(b and b in x for b in (bans or []))]
        lines = [x for x in lines if _math_ok(x)]
        if lines:
            quote = max(lines, key=len)[:140]
            out.append(Evidence(f"E{len(out) + 1}", n, quote))
            continue
        imgs = re.findall(r"\[\[\[IMAGE:\s*([^|\]]+)\|\s*图注:\s*(.*?)（第\s*\d+\s*页）\]\]\]", page or "", re.S)
        if imgs:
            quote = f"【图示】{imgs[0][1].strip() or '第' + str(n) + '页图示'}"
            out.append(Evidence(f"E{len(out) + 1}", n, quote))
        else:
            # 纯空白页也要保留来源，不能返回空块导致整份失败
            out.append(Evidence(f"E{len(out) + 1}", n, "【本页无可用文字，保留原页】"))
    return out


def _clean_quote(q: str) -> str:
    q = str(q or "")
    q = re.sub(r"\d{2}/\d{2}/\d{2}", "", q)
    q = re.sub(r"【图示】|原文[:：]?", "", q)
    q = re.sub(r"[（(]\s*[)）]", "", q)
    q = re.sub(r"第\s*\d+\s*页", "", q)
    q = re.sub(r"[（(]\s*P?\.?\s*\d+\s*[)）]", "", q)
    q = re.sub(r"\s+", " ", q).strip(" ，,。.;；")
    return q


_IMG_TAG = re.compile(r"\[\[\[IMAGE:[^\n]*?\]\]\]")


def _page_images(pages: list[str]) -> dict[int, list[str]]:
    out: dict[int, list[str]] = {}
    for i, page in enumerate(pages, 1):
        text = page or ""
        m = re.search(r"》\s*第\s*(\d+)\s*页】", text)
        n = int(m.group(1)) if m else i
        tags = _IMG_TAG.findall(text)
        if not tags:
            continue
        dm = re.search(r"【图示内容】\s*([^\n【]+)", text)
        desc = re.sub(r"\s+", " ", dm.group(1)).strip()[:90] if dm else ""
        fixed = []
        for tag in tags:
            if desc:
                tag = re.sub(r"\|\s*图注:\s*.*?（第\s*\d+\s*页）", f"| 图注: {desc}（第 {n} 页）", tag)
            fixed.append(tag)
        out[n] = fixed
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
    cards = [e for e in cards if _math_ok(e.quote)]
    if not cards:
        cards = _fallback_cards(pages, (chapter or {}).get("chapter_pages"), bans)
    if not cards:
        return ""
    title = str((chapter or {}).get("title") or "本章")
    weak = "、".join((chapter or {}).get("weak_topics") or [])
    out = [f"## {title}"]
    page_imgs = _page_images(pages)
    used_pages: set[int] = set()
    _batch = int((chapter or {}).get("card_batch") or BATCH)
    for start in range(0, len(cards), _batch):
        batch = cards[start:start + _batch]
        section, explanations = _explain_batch(batch, title, weak, bans, ai_call=ai_call)
        out.append(f"### {section or title}")
        for e in batch:
            quote = _clean_quote(e.quote)
            if not quote:
                continue
            # 教材式段落：原句自然并入讲解，段尾只留很小的来源标记
            exp = explanations.get(e.eid) or "这句是资料里的直接结论，先记住原句，再结合上下文理解。"
            joined = quote + ("" if quote.endswith(("。", "！", "？", ".", "；", ";")) else "。") + " " + exp
            out.append(joined + f'<sup class="src">P.{e.page}</sup>')
            if e.page not in used_pages and page_imgs.get(e.page):
                out.extend(page_imgs[e.page])
                used_pages.add(e.page)
    return "\n\n".join(out).strip()

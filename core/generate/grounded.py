"""证据优先讲义：先给模型资料原句，只允许写“原文引用 + 讲解”。

产物形态：
> 原文：<逐字原文>（P.N）
**讲解**：<通俗解释，不新增事实>

引文必须能在原句库里逐字找到；找不到就重试/拒收。
"""
from __future__ import annotations

import re

from core.exam_engine import call_ai_with_retry
from core.generate.evidence_pack import build_pack, render_pack

PAGE_SPLIT = re.compile(r"(?=【《.+?》第\s*\d+\s*页】)")
QUOTE_LINE = re.compile(r"(?m)^>\s*原文[:：]\s*(.+?)\s*[（(]\s*P?\.?\s*(\d+)\s*[)）]\s*$")


def _norm(text: str) -> str:
    return re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", text or "")


def validate_quotes(markdown: str, pack) -> tuple[str, int, int]:
    """只保留引文能在证据库逐字找到的“原文 + 紧跟讲解”；返回(文本,保留,删除)。"""
    lines = (markdown or "").splitlines()
    out: list[str] = []
    kept = dropped = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        m = QUOTE_LINE.match(line)
        if not m:
            out.append(line); i += 1; continue
        quote, page = m.group(1), int(m.group(2))
        qn = _norm(quote)
        ok = any(qn and qn in _norm(e.quote) and e.page == page for e in pack)
        if not ok:
            dropped += 1
            i += 1
            # 删掉紧跟着的讲解，直到空行/标题/下一条原文
            while i < len(lines) and not lines[i].startswith(("#", "> 原文")):
                i += 1
            continue
        out.append(line); kept += 1; i += 1
        # 保留紧跟讲解
        while i < len(lines) and not lines[i].startswith(("#", "> 原文")):
            out.append(lines[i]); i += 1
    return "\n".join(out), kept, dropped


def generate_grounded_chapter(raw_text: str, course, persona: str = "老师", user_choice: str = "",
                              weight_prompt: str = "", lang: str = "中文", chapter: dict | None = None,
                              user_note: str = "", constraint_block: str = "", retry_note: str = "") -> str:
    pages = [p for p in PAGE_SPLIT.split(raw_text or "") if p.strip()]
    pack = build_pack(pages, max_per_page=6)
    bans = (chapter or {}).get("ban_topics") or []
    if bans:
        pack = [e for e in pack if not any(b in e.quote for b in bans)]
    # 引文必须像正文，不能是纯元信息
    pack = [e for e in pack if len(re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", e.quote)) >= 10]
    if not pack:
        return ""
    title = str((chapter or {}).get("title") or "本章")
    target = int((chapter or {}).get("target_words") or 1200)
    weak = "、".join((chapter or {}).get("weak_topics") or [])
    sys_p = f"""你是大学期末讲义编辑。你只能使用下方【证据句库】里的原句，不允许新增事实、数字、定理编号或例题数据。
输出格式必须严格遵守：
## 核心考点：{title}
### 小节标题
> 原文：<证据句逐字原文>（P.页码）
**讲解**：用通俗话解释这句；可以打比方/给步骤，但不能新增事实；如需要延伸，另起一句标【延伸】。

要求：
1. 只允许使用证据句库里的原句做“> 原文”，不得改写引文；
2. 每个小节至少一条原文；讲解要围绕原文，不能写资料没有的结论；
3. 目标篇幅约 {target} 字；{('学生薄弱点必须加讲：' + weak) if weak else ''}
4. 不要输出结语/客套；不要重复证据句；不要编页码。
{constraint_block}
{retry_note}
"""
    user = f"【证据句库】\n{render_pack(pack, max_items=80)}\n\n【老师/学生说明】\n{user_note or '（无）'}"
    md = call_ai_with_retry(sys_p, user, temp=0.2, min_budget=4096)
    if not md.strip():
        return ""
    clean, kept, dropped = validate_quotes(md, pack)
    if kept == 0:
        # 一轮纠错：把无效引文告诉模型
        retry = call_ai_with_retry(sys_p, user + f"\n\n上一轮有 {dropped} 条引文不是证据库原句，全部作废；请重新写，引文必须逐字来自证据库。",
                                   temp=0.1, min_budget=4096)
        clean, kept, dropped = validate_quotes(retry, pack)
    if bans:
        blocks = re.split(r"(\n\s*\n)", clean)
        kept_blocks = []
        for b in blocks:
            if b and not b.isspace() and not b.lstrip().startswith("#") and any(x in b for x in bans):
                continue
            kept_blocks.append(b)
        clean = "".join(kept_blocks)
    if kept < max(2, len(pack) // 8):
        return ""
    return clean.strip()

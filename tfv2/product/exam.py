"""训练模式（AI 出卷）：真题参考、四种模式、100 分蓝图、题型/难度/配图描述。

这是 v1：结构、分值、答案、出处由确定性代码校验；计算/简答答案仍需人工复核。
"""
from __future__ import annotations

import base64
import difflib
import hashlib
import json
import re
import time
import uuid
from pathlib import Path

from loguru import logger

from tfv2.llm.client import DeepSeekClient, LLMError
from tfv2.product import delivery, exclusions, generate, service, source_pages, tasks
from tfv2.quality import trust
from tfv2.render import figure_spec as figspec
from tfv2.render import diagram, figure_compiler, figure_router

MODES = {
    "change_numbers": "原题改数",
    "variant": "原题变式",
    "mock": "模拟",
    "predict": "预测",
}

SUBJECT_TYPES = {
    "高等数学": ["choice", "fill_blank", "calculation", "proof", "short_answer"],
    "物理": ["choice", "fill_blank", "calculation", "experiment", "short_answer"],
    "电路": ["choice", "fill_blank", "calculation", "design", "short_answer"],
    "化学": ["choice", "fill_blank", "calculation", "short_answer"],
    "计算机": ["choice", "fill_blank", "calculation", "design", "short_answer"],
    "生物": ["choice", "term", "short_answer", "case"],
    "医学": ["choice", "term", "short_answer", "case"],
    "文科": ["choice", "term", "short_answer", "essay"],
    "其他": ["choice", "fill_blank", "calculation", "short_answer"],
}
MIN_QUESTIONS = 12

DEFAULT_BLUEPRINTS = {
    "高等数学": [
        {"name": "一、选择题", "type": "choice", "count": 8, "score": 24},
        {"name": "二、填空题", "type": "fill_blank", "count": 4, "score": 8},
        {"name": "三、计算题", "type": "calculation", "count": 5, "score": 50},
        {"name": "四、证明题", "type": "proof", "count": 2, "score": 18},
    ],
    "物理": [
        {"name": "一、选择题", "type": "choice", "count": 8, "score": 24},
        {"name": "二、填空题", "type": "fill_blank", "count": 4, "score": 8},
        {"name": "三、计算题", "type": "calculation", "count": 5, "score": 50},
        {"name": "四、实验题", "type": "experiment", "count": 2, "score": 18},
    ],
    "电路": [
        {"name": "一、选择题", "type": "choice", "count": 10, "score": 30},
        {"name": "二、填空题", "type": "fill_blank", "count": 5, "score": 10},
        {"name": "三、计算题", "type": "calculation", "count": 4, "score": 40},
        {"name": "四、简答题", "type": "short_answer", "count": 2, "score": 20},
    ],
    "化学": [
        {"name": "一、选择题", "type": "choice", "count": 10, "score": 30},
        {"name": "二、填空题", "type": "fill_blank", "count": 4, "score": 10},
        {"name": "三、计算/机理题", "type": "calculation", "count": 4, "score": 40},
        {"name": "四、简答题", "type": "short_answer", "count": 2, "score": 20},
    ],
    "计算机": [
        {"name": "一、选择题", "type": "choice", "count": 10, "score": 30},
        {"name": "二、填空题", "type": "fill_blank", "count": 4, "score": 10},
        {"name": "三、设计/计算题", "type": "design", "count": 4, "score": 40},
        {"name": "四、简答题", "type": "short_answer", "count": 2, "score": 20},
    ],
    "生物": [
        {"name": "一、选择题", "type": "choice", "count": 15, "score": 30},
        {"name": "二、名词解释", "type": "term", "count": 4, "score": 20},
        {"name": "三、简答题", "type": "short_answer", "count": 3, "score": 30},
        {"name": "四、病例/材料分析", "type": "case", "count": 2, "score": 20},
    ],
    "医学": [
        {"name": "一、选择题", "type": "choice", "count": 15, "score": 30},
        {"name": "二、名词解释", "type": "term", "count": 4, "score": 20},
        {"name": "三、简答题", "type": "short_answer", "count": 3, "score": 30},
        {"name": "四、病例分析", "type": "case", "count": 2, "score": 20},
    ],
    "文科": [
        {"name": "一、选择题", "type": "choice", "count": 10, "score": 30},
        {"name": "二、名词解释", "type": "term", "count": 4, "score": 20},
        {"name": "三、简答题", "type": "short_answer", "count": 4, "score": 30},
        {"name": "四、论述题", "type": "essay", "count": 2, "score": 20},
    ],
    "其他": [
        {"name": "一、选择题", "type": "choice", "count": 10, "score": 30},
        {"name": "二、填空题", "type": "fill_blank", "count": 4, "score": 10},
        {"name": "三、计算题", "type": "calculation", "count": 4, "score": 40},
        {"name": "四、简答题", "type": "short_answer", "count": 2, "score": 20},
    ],
}

TYPE_LABELS = {
    "choice": "选择题", "fill_blank": "填空题", "calculation": "计算题",
    "proof": "证明题", "short_answer": "简答题", "experiment": "实验题",
    "design": "设计题", "term": "名词解释", "case": "病例分析", "essay": "论述题",
}


class ExamError(RuntimeError):
    pass


def _pdf_text(path: Path) -> str:
    import pymupdf
    doc = pymupdf.open(str(path))
    try:
        return "\n".join((p.get_text() or "") for p in doc)[:9000]
    finally:
        doc.close()


def _reference_text(path: Path, work: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        text = _pdf_text(path)
        if len(text.strip()) >= 100:
            return text
        # 扫描件：先用本地 MinerU（不花云端 token），失败再退回云端视觉 OCR。
        try:
            from tfv2.ingest.mineru_backend import MinerUError, ocr_pdf_text
            try:
                return ocr_pdf_text(path, page_spec="all")[:9000]
            except MinerUError as exc:
                logger.warning("MinerU 解析真题失败，退回云端 OCR：{}", exc)
        except Exception:
            pass
        try:
            import pymupdf
            from core.parser import _ocr_page
            doc = pymupdf.open(str(path))
            parts = []
            for i in range(min(6, len(doc))):
                parts.append(_ocr_page(doc[i]) or "")
            doc.close()
            return "\n".join(parts)[:9000]
        except Exception:
            return text
    if suffix in (".pptx", ".docx"):
        pdf = generate._convert_docx(path, work / "refs")
        return _pdf_text(pdf)
    if suffix in (".png", ".jpg", ".jpeg", ".webp"):
        from core.parser import _ocr_image_file
        return _ocr_image_file(str(path))[:9000]
    return ""


def _reference_bank_fallback(ref_text: str) -> list[dict]:
    items = []
    current_type = "choice"
    for line in str(ref_text or "").splitlines():
        line = line.strip()
        if not line:
            continue
        if "简答" in line or "论述" in line:
            current_type = "short_answer"
        elif "计算" in line:
            current_type = "calculation"
        elif "选择" in line or "判断" in line or "填空" in line:
            current_type = "choice"
        m = re.match(r"^\s*\|?\s*(\d+)\s*[.、．)]\s*(.+?)\s*\|?\s*$", line)
        if not m:
            continue
        topic = re.sub(r"\s+", " ", m.group(2)).strip()[:80]
        items.append({"no": m.group(1), "type": current_type, "points": "", "topic": topic})
    return items[:40]


def _cached_reference_bank(client, ref_text: str) -> dict:
    """Keep the same reference bank for the same OCR text across runs."""
    import hashlib
    key = hashlib.md5(("v2:" + str(ref_text or "")).encode("utf-8")).hexdigest()
    cache_dir = generate.ARTIFACT_ROOT.parent / "reference_bank_cache"
    path = cache_dir / f"{key}.json"
    try:
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("items"):
                return data
    except Exception:
        pass
    bank = _reference_bank(client, ref_text)
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(bank, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
    return bank


_QNUM = re.compile(r"^\s*\|?\s*(\d{1,3})\s*[.、．)]\s*\S", re.M)
_OPTION = re.compile(r"^\s*[A-DＡ-Ｄ]\s*[.、．)]\s*\S|^\s*[（(]\s*[A-D]\s*[）)]", re.M)
_ANSWER = re.compile(r"(参考答案|答案[：:]|解析[：:]|【答案】|【解析】)")
_QHEAD = re.compile(r"(选择题|填空题|计算题|简答题|判断题|证明题|名词解释|论述题|问答题|综合题)")


def looks_like_question_paper(ref_text: str) -> dict:
    """判断一份文本像不像题目卷，而不是讲义/教材。

    只看可数的结构特征，不调模型：题号、选项、答案/解析、题型标题。
    讲义里也有“1. 电流放大系数”这类编号标题，所以必须同时看到题卷特征才算数。
    """
    text = str(ref_text or "")
    qnum = len(_QNUM.findall(text))
    options = len(_OPTION.findall(text))
    answers = len(_ANSWER.findall(text))
    heads = len(_QHEAD.findall(text))
    lines = [x for x in text.splitlines() if x.strip()]
    avg_line = sum(len(x) for x in lines) / max(1, len(lines))
    # 题卷特征：题号 + 选项/答案标记，或题型标题 + 足够题号；讲义只有编号标题。
    structured = (
        (qnum >= 3 and (options >= 3 or answers >= 2))
        or (qnum >= 8 and heads >= 2)
        or (qnum >= 2 and (options >= 2 or answers >= 1))
    )
    return {"qnum": qnum, "options": options, "answers": answers, "heads": heads,
            "avg_line": round(avg_line, 1), "looks": bool(structured),
            "reason": "" if structured else (
                f"题号 {qnum} 个、选项 {options} 个、答案标记 {answers} 个、题型标题 {heads} 个，"
                "不构成题目卷特征")}


def reference_guard(ref_text: str, bank: dict, *, allow_non_question: bool = False) -> str | None:
    """返回拒绝原因；None 表示可以用作真题参考。"""
    shape = looks_like_question_paper(ref_text)
    items = list((bank or {}).get("items") or [])
    if shape["looks"] and items:
        return None
    reason = shape["reason"] or "没有解析出题级清单"
    if allow_non_question:
        return None
    return (f"参考文件里没有识别到可用的题目（{reason}）："
            "请换一份试卷，或勾选“按模拟出卷继续”。不会静默把非题目文件当结构参考。")


def _reference_bank(client, ref_text: str) -> dict:
    """把参考真题解析成题级清单：题号/题型/分值/考点，供变式映射使用。"""
    if not (ref_text or "").strip():
        return {"items": [], "used": False}
    shape = looks_like_question_paper(ref_text)
    if not shape["looks"]:
        # 讲义/教材也有编号标题，不能当成题目卷；这里直接判非题目并说明原因。
        return {"items": [], "used": False, "reason": shape["reason"], "shape": shape}
    # The deterministic numbered-line parser is the stable source of truth.
    # The model used to change the bank size between identical runs (18 -> 11).
    fallback = _reference_bank_fallback(ref_text)
    if len(fallback) >= 3:
        return {"items": fallback, "used": True}
    try:
        data = client.json(
            "你是命题研究员。把给定的参考真题解析成题级清单，题干太长就只概括考点，不要抄全题。"
            '只输出 JSON：{"items":[{"no":"1","type":"choice|calculation|short_answer","points":"5","topic":"考点"}]}。',
            str(ref_text)[:6000], max_tokens=2500, temperature=0.1,
        )
        items = [x for x in (data.get("items") or []) if isinstance(x, dict) and x.get("no")][:40]
        if not items:
            items = _reference_bank_fallback(ref_text)
        return {"items": items, "used": True}
    except Exception:
        return {"items": _reference_bank_fallback(ref_text), "used": True}


_SEC_HEADER = re.compile(
    r"([一二三四五六七八九十]+)\s*[、.]\s*([^()（）\n]{2,20}?)\s*[（(]\s*每小?题\s*(\d+)\s*分"
    r"\s*[,，、]?\s*共\s*(\d+)\s*分\s*[)）]")
# 另一种常见格式：“一、(本题30分,每小题6分)”“二、（本题14分）”
_SEC_HEADER_B = re.compile(
    r"([一二三四五六七八九十]+)\s*[、.]\s*[（(]\s*本题\s*(\d+)\s*分"
    r"(?:\s*[,，、]\s*每小题\s*(\d+)\s*分)?\s*[)）]")
_TYPE_WORDS = [("选择", "choice"), ("填空", "fill_blank"), ("计算", "calculation"),
               ("证明", "proof"), ("简答", "short_answer"), ("实验", "experiment"),
               ("设计", "design"), ("名词", "term"), ("病例", "case"), ("材料", "case"),
               ("论述", "essay"), ("解答", "calculation"), ("应用", "calculation")]


def _type_of_name(name: str) -> str:
    for word, t in _TYPE_WORDS:
        if word in name:
            return t
    return "other"


def parse_sections_deterministic(ref_text: str) -> list[dict]:
    """从真题文本里确定性解析题型结构（“一、单项选择题(每小题3分,共18分)”）。

    不调模型；只要能看见题型标题，就能给出题数/分值，用来校验模型解析的结构对不对。
    """
    out: list[dict] = []
    seen: set[str] = set()
    text = str(ref_text or "")
    for m in _SEC_HEADER.finditer(text):
        name = re.sub(r"\s+", " ", m.group(2)).strip()
        per = int(m.group(3))
        total = int(m.group(4))
        if per <= 0 or total <= 0 or name in seen:
            continue
        seen.add(name)
        out.append({"name": f"{m.group(1)}、{name}", "type": _type_of_name(name),
                    "per_question": per, "count": max(1, round(total / per)), "score": total})
    for m in _SEC_HEADER_B.finditer(text):
        num = m.group(1)
        total = int(m.group(2))
        per = int(m.group(3)) if m.group(3) else total
        if total <= 0 or per <= 0:
            continue
        name = f"{num}、"
        if name in seen:
            continue
        seen.add(name)
        count = max(1, round(total / per))
        out.append({"name": name, "type": "other", "per_question": per,
                    "count": count, "score": total})
    return out


def structure_fidelity(parsed: list[dict], expected: list[dict]) -> dict:
    """模型解析的题型结构 vs 真题里看得见的结构：题型命中、题量偏差、分值偏差。"""
    def _types(rows: list[dict]) -> set[str]:
        return {str(r.get("type") or "other") for r in rows}

    got, want = _types(parsed), _types(expected)
    hit = len(got & want)
    type_recall = hit / max(1, len(want))
    counts_got = sum(int(r.get("count") or 0) for r in parsed)
    counts_want = sum(int(r.get("count") or 0) for r in expected)
    count_error = abs(counts_got - counts_want) / max(1, counts_want)
    score_got = sum(float(r.get("score") or 0) for r in parsed)
    score_want = sum(float(r.get("score") or 0) for r in expected)
    score_error = abs(score_got - score_want) / max(1, score_want)
    ok = type_recall >= 0.99 and count_error <= 0.15 and score_error <= 0.05
    return {"types_expected": sorted(want), "types_parsed": sorted(got),
            "type_recall": round(type_recall, 3), "count_error": round(count_error, 3),
            "score_error": round(score_error, 3), "ok": ok,
            "score_expected": score_want, "score_parsed": score_got}


def plan_question_pages(sections: list[dict], pages: list[int]) -> list[list[int]]:
    """给每一道题分配资料页：一题一页、尽量铺开、能铺满就铺满。

    确定性轮转，不用外部求解器：
    - 题量 ≤ 页数：从整份资料里等距取页，保证覆盖分散而不是从第 1 页往后顺排；
    - 题量 > 页数：每页先用一遍，再循环补齐（此时必然有页复用）；
    - 返回与 sections 等长的列表，每项是该题型逐题的页码，顺序稳定。
    """
    ordered = sorted({int(p) for p in pages or []})
    total = sum(max(0, int(sec.get("count") or 0)) for sec in sections or [])
    if not ordered or total <= 0:
        return [[] for _ in sections or []]

    if total <= len(ordered):
        # 等距取页：stride = 页数/题量，避免全挤在开头
        stride = len(ordered) / total
        picks = [ordered[min(len(ordered) - 1, int(i * stride))] for i in range(total)]
        # 极端取整可能重复，按顺序补上没用到的页
        seen = set()
        deduped = []
        for p in picks:
            if p in seen:
                continue
            deduped.append(p)
            seen.add(p)
        for p in ordered:
            if len(deduped) >= total:
                break
            if p not in seen:
                deduped.append(p)
                seen.add(p)
        assignment = deduped[:total]
    else:
        assignment = []
        while len(assignment) < total:
            assignment.extend(ordered)
        assignment = assignment[:total]

    out: list[list[int]] = []
    cursor = 0
    for sec in sections or []:
        count = max(0, int(sec.get("count") or 0))
        out.append(assignment[cursor:cursor + count])
        cursor += count
    return out


def audit_paper(bp: dict, *, audit: dict | None = None) -> dict:
    """整卷体检（确定性，不调模型）：题型完整、题量、分值、答案、总分。

    只做结构性判断，不评价题目质量；答案对不对由 answer_audit 的独立解题复核负责。
    """
    issues: list[str] = []
    sections = bp.get("sections") or []
    if not sections:
        issues.append("试卷没有任何题型")
    if not any((sec.get("questions") or []) for sec in sections):
        issues.append("试卷没有任何题目")
    total = 0.0
    for sec in sections:
        qs = sec.get("questions") or []
        name = str(sec.get("name") or "未命名题型")
        want = int(sec.get("count") or 0)
        if want and len(qs) != want:
            issues.append(f"{name} 题量 {len(qs)}/{want}")
        got = round(sum(float(q.get("score") or 0) for q in qs), 1)
        need = round(float(sec.get("score") or 0), 1)
        if need and abs(got - need) > 0.05:
            issues.append(f"{name} 分值 {got} 与蓝图 {need} 不一致")
        for i, q in enumerate(qs, start=1):
            # 选择题用 answer(0-3)，填空/计算/简答用 answer_text；不能拿同一字段判所有题型。
            if q.get("qtype") == "choice":
                ans = q.get("answer")
                if not isinstance(ans, int) or ans not in range(4):
                    issues.append(f"{name} 第 {i} 题答案不在 0–3")
            elif not str(q.get("answer_text") or q.get("answer") or "").strip():
                issues.append(f"{name} 第 {i} 题没有答案")
            if float(q.get("score") or 0) <= 0:
                issues.append(f"{name} 第 {i} 题分值不大于 0")
        total += got
    total = round(total, 1)
    if total != 100:
        issues.append(f"总分不是 100：{total:.1f}")
    conflicts = list((audit or {}).get("conflicts") or [])
    if conflicts:
        issues.append(f"答案审计仍有 {len(conflicts)} 处冲突")
    checked = bool((audit or {}).get("checked"))
    status = "rejected" if issues else ("validated" if checked else "review")
    return {"issues": issues, "total_score": total, "status": status, "checked": checked,
            "section_count": len(sections)}


def _json_retry(call, attempts: int = 3):
    """Retry transient LLM/JSON failures with backoff instead of dropping a whole section."""
    last = None
    for n in range(attempts):
        try:
            return call()
        except LLMError as exc:
            last = exc
            time.sleep(4 * (n + 1))
    raise last


def _norm_sections(raw) -> list[dict]:
    if not isinstance(raw, list):
        raise ExamError("蓝图 sections 不是数组")
    out = []
    for i, sec in enumerate(raw, start=1):
        if not isinstance(sec, dict):
            continue
        name = str(sec.get("name") or "").strip()
        qtype = str(sec.get("type") or "").strip()
        if qtype not in TYPE_LABELS:
            qtype = "choice"
        try:
            count = max(1, min(50, int(sec.get("count"))))
            score = max(count, int(sec.get("score")))
        except Exception:
            continue
        out.append({"name": name or f"{TYPE_LABELS[qtype]}（第{i}部分）", "type": qtype,
                    "count": count, "score": score})
    if not out:
        raise ExamError("蓝图没有可用 section")
    total_count = sum(s["count"] for s in out)
    if total_count < MIN_QUESTIONS:
        raise ExamError(f"题量过少：100 分试卷至少 {MIN_QUESTIONS} 题；当前 {total_count} 题")
    if total_count > 50:
        raise ExamError("单份试卷最多 50 题；请拆成两份，避免模型输出/审计超时")
    total = sum(s["score"] for s in out)
    if total != 100:
        # 按比例归一化，尾差给最后一部分；保证总分 100、每部分至少 1 分/题
        raw_total = total
        scaled = [max(s["count"], round(s["score"] * 100 / raw_total)) for s in out]
        diff = 100 - sum(scaled)
        scaled[-1] = max(out[-1]["count"], scaled[-1] + diff)
        # 若最后一部分被压到低于题数，从最大的部分借分
        if scaled[-1] < out[-1]["count"]:
            need = out[-1]["count"] - scaled[-1]
            scaled[-1] = out[-1]["count"]
            for j in range(len(scaled) - 2, -1, -1):
                take = min(need, scaled[j] - out[j]["count"])
                scaled[j] -= take
                need -= take
                if need <= 0:
                    break
        for s, v in zip(out, scaled):
            s["score"] = v
        if sum(s["score"] for s in out) != 100:
            raise ExamError("无法把蓝图分数归一到 100")
    return out




def _reference_sections(client, reference: str) -> list[dict]:
    """把真题先解析成题型表，而不是只在 prompt 里“参考一下”。"""
    system = (
        "你是试卷结构分析器。只分析这份真题的题型结构，不要出题。"
        "只输出 JSON：{\"title\":\"...\",\"sections\":[{\"name\":\"一、选择题\",\"type\":\"choice\",\"count\":10,\"score\":30}]}。"
        "type 只能是 choice/fill_blank/calculation/proof/short_answer/experiment/design/term/case/essay；"
        "section 的 score 之和必须 100；score≥count。"
    )
    user = f"真题文本：\n{reference[:8000]}\n请输出结构 JSON。"
    data = client.json(system, user, max_tokens=1600, temperature=0.1)
    return _norm_sections(data.get("sections"))

_TYPE_BY_WORD = [
    ("选择", "choice"), ("单选", "choice"), ("填空", "fill_blank"), ("计算", "calculation"),
    ("证明", "proof"), ("简答", "short_answer"), ("问答", "short_answer"),
    ("实验", "experiment"), ("设计", "design"), ("名词", "term"),
    ("病例", "case"), ("材料", "case"), ("论述", "essay"),
]
_BLUEPRINT_ITEM = re.compile(r"([^\d；;，,\n]{2,12}?)\s*(\d{1,2})\s*题\s*(\d{1,3})\s*分")


def parse_blueprint_text(text: str) -> list[dict]:
    """把用户蓝图（“选择题 2 题 50 分；填空题 2 题 50 分”）解析成题型表。

    解析不出来就返回空，交给模型理解；能解析就必须照做，不能“大概参考一下”。
    """
    items: list[dict] = []
    for m in _BLUEPRINT_ITEM.finditer(str(text or "")):
        name = re.sub(r"^[一二三四五六七八九十]+\s*[、.]\s*", "", m.group(1).strip())
        name = name.strip(" ：:、")
        if not name:
            continue
        qtype = None
        for word, t in _TYPE_BY_WORD:
            if word in name:
                qtype = t
                break
        if qtype is None:
            return []
        count = int(m.group(2))
        score = int(m.group(3))
        if count < 1 or score < count:
            return []
        items.append({"name": name, "type": qtype, "count": count, "score": score})
    return items if len(items) >= 1 else []


def _blueprint(client, *, subject: str, types: list[str], difficulty: int,
               reference: str, user_blueprint: str, mode: str, gen_lang: str = "zh") -> dict:
    type_text = "、".join(f"{t}={TYPE_LABELS.get(t, t)}" for t in types)
    system = (
        "你是大学课程命题组长。设计一份满分 100 分的试卷蓝图，只输出 JSON。"
        "题型要与科目匹配、覆盖课程核心考点；难度 1–5，区分度要合理，不能全是送分题或全是压轴题。"
        "100 分试卷题量必须 18–28 题（选择题/填空题可多，计算/简答按分值），不能只出 4 道大题。"
        '格式：{"title":"...","sections":[{"name":"一、选择题","type":"choice","count":10,"score":30}]}。'
        "type 只能是 choice/fill_blank/calculation/proof/short_answer/experiment/design/term/case/essay。"
        "所有 section 的 score 之和必须等于 100；score≥count。"
    )
    ref = f"\n参考真题（必须模仿其题型结构/顺序/格式，不要照抄题目）：\n{reference[:6000]}" if reference else "\n没有参考真题：按科目常规自由命题。"
    user = (
        f"科目：{subject}\n模式：{MODES.get(mode, mode)}\n难度：{difficulty}/5\n"
        f"生成语言：{generate.GEN_LANG_LABEL.get(gen_lang, '简体中文')}（题型名称可用该语言，原题引用保留原文）\n"
        f"允许题型：{type_text}\n用户自定义蓝图（可为空）：{user_blueprint or '无'}\n"
        f"{ref}\n请输出 100 分蓝图 JSON。"
    )
    ref_error = ""
    if reference:
        try:
            ref_sections = _reference_sections(client, reference)
            det = parse_sections_deterministic(reference)
            fidelity = structure_fidelity(ref_sections, det) if len(det) >= 2 else None
            return {"title": f"{subject}训练卷（仿真题结构）", "sections": ref_sections,
                    "reference_structure": True, "reference_fidelity": fidelity}
        except Exception as exc:  # noqa: BLE001
            # 解析失败不能静默：记下原因，后面写进 warnings，让用户知道这次没按真题结构走。
            ref_error = f"{type(exc).__name__}: {str(exc)[:160]}"
    parsed = parse_blueprint_text(user_blueprint)
    if parsed:
        total = sum(x["count"] for x in parsed)
        if total > 50:
            raise ExamError(f"用户蓝图共 {total} 题，超过单份试卷 50 题上限；请拆成两份")
        return {"title": f"{subject}训练卷（按你的蓝图）", "sections": _norm_sections(parsed),
                "user_blueprint": True, "blueprint_parsed": parsed,
                "reference_structure": False, "reference_structure_error": ref_error}
    if not user_blueprint.strip():
        base = [dict(x) for x in DEFAULT_BLUEPRINTS.get(subject, DEFAULT_BLUEPRINTS["其他"])]
        filtered = [x for x in base if x["type"] in types]
        if sum(x["count"] for x in filtered) < MIN_QUESTIONS:
            filtered = base
        return {"title": f"{subject}训练卷（{MODES.get(mode, mode)}）", "sections": _norm_sections(filtered),
                "reference_structure": False, "reference_structure_error": ref_error}
    data = client.json(system, user, max_tokens=5000, temperature=0.25)
    sections = _norm_sections(data.get("sections"))
    return {"title": str(data.get("title") or f"{subject}训练卷"), "sections": sections,
            "reference_structure": False, "reference_structure_error": ref_error}


def _artifact_exclusion_specs(path) -> list[dict]:
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


def _lecture_scope_pages(path) -> set[int]:
    """Pages the lecture actually covers (sections source_refs), not the raw PDF."""
    try:
        data = json.loads((path / "sections.json").read_text(encoding="utf-8"))
        pages: set[int] = set()
        for sec in data:
            for ref in sec.get("source_refs") or []:
                try:
                    pages.update(range(int(ref["page_start"]), int(ref.get("page_end") or ref["page_start"]) + 1))
                except Exception:
                    continue
            for b in sec.get("blocks") or []:
                for ref in b.get("source_refs") or []:
                    try:
                        pages.update(range(int(ref["page_start"]), int(ref.get("page_end") or ref["page_start"]) + 1))
                    except Exception:
                        continue
        if pages:
            return pages
    except Exception:
        pass
    try:
        project = json.loads((path / "project.json").read_text(encoding="utf-8"))
        scope = project.get("scope_pages") or []
        if scope:
            return {int(p) for p in scope}
    except Exception:
        pass
    return set()


def _source_context(aid: str, limit: int = 9000) -> tuple[str, list[int]]:
    path = service.artifact_path(aid)
    if path is None:
        raise ExamError("讲义不存在")
    raw = source_pages.load_source_pages(path)
    if raw:
        all_pages = sorted(source_pages.page_map(raw))
        scope = _lecture_scope_pages(path)
        pages = [p for p in all_pages if p in scope] or all_pages
        return source_pages.source_context(raw, None, limit), pages
    data = json.loads((path / "sections.json").read_text(encoding="utf-8"))
    pages: set[int] = set()
    chunks: list[str] = []
    for sec in data:
        chunks.append(str(sec.get("title") or ""))
        for b in sec.get("blocks") or []:
            text = str(b.get("text") or "").strip()
            if not text:
                continue
            chunks.append(text)
            for ref in b.get("source_refs") or []:
                try:
                    pages.update(range(int(ref["page_start"]), int(ref.get("page_end") or ref["page_start"]) + 1))
                except Exception:
                    continue
    return "\n".join(chunks)[:limit], sorted(pages)


def _parse_question(raw: dict, allowed: set[int], page_text: dict[int, str], mode: str, subject: str,
                    expected_type: str | None = None, figure_map: dict[int, dict] | None = None,
                    excluded_specs: list[dict] | None = None) -> tuple[dict | None, str]:
    if not isinstance(raw, dict):
        return None, "题目不是对象"
    stem = str(raw.get("stem") or "").strip()
    if excluded_specs and exclusions.question_excluded(
            {"stem": stem, "options": raw.get("options") or [], "analysis": raw.get("analysis") or ""}, excluded_specs):
        return None, "用户已将本题内容排除"
    if len(stem) < 12:
        return None, "题干过短，缺少背景/条件"
    qtype = str(raw.get("qtype") or "").strip()
    if expected_type in TYPE_LABELS and expected_type != "choice":
        # 计算/简答 section 里模型常省略 qtype；按本部分题型纠正，不能落成选择题
        if qtype not in TYPE_LABELS or qtype == "choice":
            qtype = expected_type
    if qtype not in TYPE_LABELS:
        qtype = "choice"
    p = tasks._page(raw.get("source_page"), allowed)
    if p is None:
        norm = tasks._norm(stem)
        hits = [pg for pg, text in page_text.items() if norm and norm[:40] in tasks._norm(text)]
        if len(hits) == 1:
            p = hits[0]
    if p is None:
        return None, "缺有效资料页码"
    analysis = str(raw.get("analysis") or "").strip()
    if len(analysis) < 8:
        return None, "缺解析"
    source_no = str(raw.get("source_no") or "").strip()
    provenance = str(raw.get("provenance") or "").strip()
    if mode in ("change_numbers", "variant") and not source_no:
        return None, f"{MODES[mode]}题缺原题号/出处"
    if mode == "variant" and not provenance:
        provenance = f"改编自第 {p} 页"
    opts = raw.get("options")
    if qtype == "choice":
        if not isinstance(opts, list) or len(opts) != 4:
            return None, "选择题必须有 4 个选项"
        opts = [str(x).strip() for x in opts]
        if any(not x for x in opts) or len(set(opts)) != 4:
            return None, "选项为空或重复"
        try:
            answer = int(raw.get("answer"))
        except Exception:
            answer = -1
        if answer not in range(4):
            return None, "选择题答案不在选项内"
        answer_text = chr(65 + answer)
    else:
        opts = []
        answer = None
        answer_text = str(raw.get("answer_text") or raw.get("answer") or "").strip()
        if not answer_text:
            return None, f"{TYPE_LABELS[qtype]}缺参考答案"
    figure = str(raw.get("figure_description") or raw.get("figure") or "").strip()
    needs_figure = bool(raw.get("needs_figure"))
    # 只有“原题改数”且明确标记原题有图时，才允许复用资料原图。
    # 原题改数：只有模型标记原题有图，或题干明确提到图时，才复用该页原图。
    # 不能因为“这一页恰好有 PPT 图”就无脑塞图。
    page_fig = (figure_map or {}).get(p)
    text_refs_fig = bool(re.search(r"(如图|图中|图示|下图|上图|原题图|figure|diagram)", stem, re.I)) or bool(
        figure and "无图" not in figure)
    original_figure = mode == "change_numbers" and (
        bool(raw.get("original_figure")) or bool(page_fig) and text_refs_fig
    )
    fig = page_fig if original_figure else None
    figure_asset = str(fig.get("asset_path") or "") if fig else ""
    figure_caption = str(fig.get("caption") or "") if fig else ""
    figure_data = ""
    figure_spec = raw.get("figure_spec") if needs_figure else None
    if not needs_figure and "无图" in figure:
        figure_spec = None
    if figure_spec is not None and not original_figure:
        # 新题图只从合法结构化 spec 生成，绝不从资料页抓图。
        try:
            errs = figspec.validate(figure_spec)
            if str(figure_spec.get("kind") or "").lower() == "circuit" and not (figure_spec.get("nodes") and figure_spec.get("edges")) and not figure_spec.get("netlist"):
                errs.append("电路图缺完整节点/连线拓扑")
            if errs:
                figure_spec = None
                raise ValueError("figure spec 缺少可绘制结构")
            out = generate.ARTIFACT_ROOT.parent / "exam_figures" / f"{uuid.uuid4().hex}.png"
            res = figure_compiler.compile_figure(figure_spec, subject=subject, out_path=out)
            if res:
                figure_data = "data:image/png;base64," + base64.b64encode(out.read_bytes()).decode()
                figure_caption = f"AI 生成配图（{subject}，程序绘制，请核对）"
                figure = figure or "AI 生成配图"
        except Exception:
            figure_data = ""
    if figure_asset and not figure:
        figure = figure_caption or f"原题第 {p} 页图"
    return {
        "qtype": qtype, "stem": stem, "options": opts, "answer": answer,
        "answer_text": answer_text, "analysis": analysis, "source_page": p,
        "source_no": source_no, "provenance": provenance,
        "figure_description": figure, "figure_asset": figure_asset,
        "figure_caption": figure_caption, "figure_data": figure_data,
        "needs_figure": needs_figure, "original_figure": original_figure,
        "figure_spec": figure_spec,
        "variant_of": (lambda v: (re.search(r"\d+", v).group() if re.search(r"\d+", v) else v))(str(raw.get("variant_of") or "new").strip()),
        "answer_audit": "auto" if qtype == "choice" else "manual",
    }, ""





def _relabel_question_pages(bp, pages, page_text) -> None:
    """Move a question to the page its text actually matches best.

    The model often stamps every question with the first page it saw. Content
    overlap is stronger evidence than that self-reported number. Only unused
    pages with at least two shared content tokens are eligible.
    """
    used = {q.get("source_page") for sec in bp["sections"] for q in sec.get("questions") or [] if q.get("source_page")}
    page_tokens = {p: set(trust.tokens(page_text.get(p, ""))) for p in pages}

    for sec in bp["sections"]:
        for q in sec.get("questions") or []:
            text = " ".join([str(q.get("stem") or ""), " ".join(map(str, q.get("options") or [])), str(q.get("analysis") or "")])
            qt = set(trust.tokens(text))
            current = q.get("source_page")
            best_page, best_score = current, len(qt & page_tokens.get(current, set()))
            for p in pages:
                if p in used and p != current:
                    continue
                score = len(qt & page_tokens.get(p, set()))
                if score > best_score:
                    best_page, best_score = p, score
            if best_score >= 2 and best_page != current:
                used.discard(current)
                used.add(best_page)
                q["source_page"] = best_page


def _top_up_sections(bp: dict, pages: list[int], page_text: dict[int, str], mode: str, subject: str,
                     figure_map, gen_client, *, difficulty: int = 3, gen_lang: str = "zh",
                     custom_prompt: str = "", rounds: int = 1) -> dict:
    """题型没凑够题时补一轮：把缺口补上，补不上就如实留缺口。

    主生成流程已经试过批量 + 单题；这里再做一轮“只补这点缺口”的针对性重试，
    避免整卷因为少一道题就作废。每次只补 1 题，题量/分值重新按本部分对齐。
    """
    filled = 0
    for _ in range(max(1, rounds)):
        short = [sec for sec in bp.get("sections") or [] if len(sec.get("questions") or []) < int(sec.get("count") or 0)]
        if not short:
            break
        for sec in short:
            need = int(sec.get("count") or 0) - len(sec.get("questions") or [])
            if need <= 0:
                continue
            existing = [tasks._norm(str(q.get("stem") or ""))[:160] for q in sec.get("questions") or []]
            used_pages = sorted({q.get("source_page") for sec2 in bp["sections"]
                                 for q in sec2.get("questions") or [] if q.get("source_page")})
            free_pages = [p for p in pages if p not in used_pages] or pages
            per = round(float(sec.get("score") or 0) / max(1, int(sec.get("count") or 1)), 1)
            system = (
                f"你是大学{TYPE_LABELS[sec['type']]}命题老师。整卷还缺 {need} 道{TYPE_LABELS[sec['type']]}，"
                "现在只补这些缺口，不要重复已有题目。只输出 JSON："
                '{"questions":[{"qtype":"' + sec["type"] + '","stem":"...","answer_text":"...","analysis":"...",'
                '"source_page":1,"source_no":"补充","needs_figure":false,"original_figure":false,'
                '"figure_description":"无图"}]}。'
                "题干必须有背景/条件；解析不超过 120 字；不要 Markdown。"
            )
            user = (
                f"资料页码：{pages}\n可用页码（优先用没被占用的）：{free_pages[:12]}\n"
                f"本部分：{sec['name']}，共 {sec['count']} 题、{sec['score']} 分，每题 {per:g} 分。\n"
                f"已经有的题干（禁止重复或近似）：\n" + "\n".join(f"- {x[:60]}" for x in existing[-12:]) +
                f"\n用户补充：{custom_prompt or '无'}。请补齐 {need} 道题。"
            )
            try:
                raw = _json_retry(lambda: gen_client.json(system, user, max_tokens=6000, temperature=0.3))
            except Exception:
                continue
            for rawq in (raw.get("questions") or [])[:need]:
                q, issue = _parse_question(rawq, set(pages), page_text, mode, subject,
                                           expected_type=sec["type"], figure_map=figure_map)
                if issue or not q:
                    continue
                norm_stem = tasks._norm(str(q.get("stem") or ""))[:160]
                if any(prev and difflib.SequenceMatcher(None, norm_stem, prev).ratio() >= 0.86 for prev in existing):
                    continue
                q["score"] = per
                sec.setdefault("questions", []).append(q)
                existing.append(norm_stem)
                filled += 1
            # 补完这一部分，重新把分数对齐到蓝图分
            qs = sec.get("questions") or []
            if qs:
                used = round(sum(float(q.get("score") or 0) for q in qs[:-1]), 1)
                qs[-1]["score"] = round(float(sec.get("score") or 0) - used, 1)
    if filled:
        for sec in bp.get("sections") or []:
            if sec.get("questions"):
                sec["count"] = len(sec["questions"])
    return {"filled": filled}


def _repair_exam_coverage(bp, pages, page_text, mode, subject, figure_map, gen_client, excluded_specs=None) -> None:
    """Guarantee the 45% page floor by appending page-anchored questions.

    Each supplement is generated from that page's own text and accepted only
    when its stem/options/analysis share at least two content tokens with the
    page. Appending (instead of replacing) avoids losing a page already cited;
    section count/scores are rebalanced so the paper still totals 100.
    """
    page_set = set(pages)
    cited = {q["source_page"] for sec in bp["sections"] for q in sec.get("questions") or [] if q.get("source_page")}
    existing_stems = [tasks._norm(str(q.get("stem") or ""))[:180] for sec in bp["sections"] for q in sec.get("questions") or []]
    target = int(0.45 * len(page_set) + 0.999) if page_set else 0
    attempts = 0
    max_attempts = max(6, len(page_set) * 2)
    for p in [x for x in pages if x not in cited]:
        if len(cited) >= target or attempts >= max_attempts:
            break
        attempts += 1
        text = str(page_text.get(p) or "").strip()
        if len(text) < 20:
            continue
        try:
            raw = _json_retry(lambda: gen_client.json(
                "只出 1 道有真实背景的选择题，只输出 JSON："
                f'{{"question":{{"qtype":"choice","stem":"...","options":["A","B","C","D"],"answer":0,"answer_text":"A","analysis":"...","source_page":{p},"source_no":"补充","variant_of":"new","needs_figure":false,"original_figure":false,"figure_description":"无图"}}}}。'
                f"source_page 必须写 {p}；options 必须恰好 4 个；题干必须直接使用本页内容。",
                f"资料页码：{p}\n资料内容：\n{text[:2500]}\n请出 1 道基于本页内容的选择题。",
                max_tokens=4000, temperature=0.2,
            ))
            rawq = raw.get("question") if isinstance(raw.get("question"), dict) else None
            if rawq is None:
                continue
            q, issue = _parse_question(rawq, set(pages), page_text, mode, subject, expected_type="choice", figure_map=figure_map, excluded_specs=excluded_specs)
            if issue or not q:
                continue
            norm_stem = tasks._norm(str(q.get("stem") or ""))[:180]
            if any(norm_stem and prev and difflib.SequenceMatcher(None, norm_stem, prev).ratio() >= 0.86 for prev in existing_stems):
                continue
            q_text = " ".join([str(q.get("stem") or ""), " ".join(map(str, q.get("options") or [])), str(q.get("analysis") or "")])
            overlap = set(trust.tokens(q_text)) & set(trust.tokens(text))
            if len(overlap) < 2:
                continue
            # The model often copies the example page instead of the assigned
            # page. Content overlap with the page is the authority, not its
            # self-reported number.
            q["source_page"] = p
            secs = [s for s in bp["sections"] if s.get("questions") and s["questions"][-1].get("qtype") == "choice"]
            if not secs:
                break
            sec = max(secs, key=lambda s: len(s["questions"]))
            q["score"] = 0
            sec["questions"].append(q)
            sec["count"] = len(sec["questions"])
            per = float(sec["score"]) / max(1, sec["count"])
            for idx, item in enumerate(sec["questions"]):
                item["score"] = round(per, 1)
            used = round(sum(float(x["score"]) for x in sec["questions"][:-1]), 1)
            sec["questions"][-1]["score"] = round(float(sec["score"]) - used, 1)
            cited.add(p)
        except Exception:
            continue


def _attach_specs(client, qs: list[dict], subject: str, gen_lang: str = "zh") -> list[str]:
    """由 AI 为“需要图但还没有图”的题生成结构化 spec，再编译成图。"""
    type_ok = set(TYPE_LABELS)
    cand = [
        q for q in qs
        if q.get("qtype") in type_ok and not q.get("figure_data") and not q.get("figure_asset")
        and bool(q.get("needs_figure"))
    ]
    if not cand:
        return []

    if subject == "化学":
        rule = ('{"kind":"chem","smiles":"CCO"}（smiles 必须来自题干，不能编造）')
    elif subject == "计算机":
        rule = ('{"kind":"flow","nodes":[{"id":"n1","label":"输入"},{"id":"n2","label":"处理"}],'
                '"edges":[{"from":"n1","to":"n2"}]}（节点/边必须来自题干）')
    elif subject == "高等数学":
        rule = ('{"kind":"math","title":"...","points":[[0,0],[1,1]],"x_label":"x","y_label":"y"}'
                '（points 必须来自题干函数/条件）')
    elif subject in ("历史", "文科", "地理"):
        rule = ('{"kind":"timeline|map|concept","title":"...","nodes":[{"label":"...","year":"..."}]}'
                '（节点必须来自题干）')
    elif subject in ("医学", "生物", "其他"):
        rule = ('{"kind":"concept|table","title":"...","nodes":[{"id":"n1","label":"..."}],'
                '"edges":[{"from":"n1","to":"n2"}]}（节点/表头必须来自题干）')
    elif subject == "电路":
        rule = ('{"kind":"circuit","nodes":[{"id":"n1","type":"battery","x":80,"y":210,"label":"U","value":"12V"},'
                '{"id":"n2","type":"node","x":80,"y":80},{"id":"n3","type":"resistor","x":300,"y":80,"label":"R1","value":"2Ω"},'
                '{"id":"n4","type":"node","x":500,"y":80}],"edges":[{"from":"n1","to":"n2"},{"from":"n2","to":"n3"},'
                '{"from":"n3","to":"n4"}]}；必须给出完整节点/连线和坐标，不能只列元件名称；label/value 必须来自题干')
    else:
        rule = ('{"kind":"force","elements":[{"type":"arrow","x1":100,"y1":300,"x2":220,"y2":300,"label":"F"}]}；'
                '坐标 0–720 × 0–420，label/value 必须来自题干')

    system = (
        "你是学科示意图的结构化绘图助手。只输出 JSON，不生成图片、不解释。"
        "只为确实需要配图的题生成 spec；不需要图的题 spec 返回 null。"
        "不能使用讲义里的原图，不能画与题干无关的装饰图。"
        "只输出：{\"figures\":[{\"index\":0,\"spec\":...},{\"index\":1,\"spec\":null}]}。"
        f"本科目可用 spec：{rule}。"
    )
    payload = [{"index": i, "stem": q.get("stem", ""), "qtype": q.get("qtype", ""),
                "figure_description": q.get("figure_description", "")} for i, q in enumerate(cand)]
    try:
        data = client.json(system, "逐题判断是否需要图并给 spec：\n" + json.dumps(payload, ensure_ascii=False),
                           max_tokens=4200, temperature=0.15)
    except Exception as exc:
        return [f"结构图生成失败：{exc}"]
    by_index = {}
    for row in data.get("figures") or []:
        try:
            by_index[int(row.get("index"))] = row.get("spec")
        except Exception:
            continue
    issues: list[str] = []
    figure_hashes: set[str] = set()
    for i, q in enumerate(cand):
        spec = by_index.get(i)
        if not isinstance(spec, dict):
            continue
        errors = figspec.validate(spec)
        if str(spec.get("kind") or "").lower() == "circuit" and not (spec.get("nodes") and spec.get("edges")) and not spec.get("netlist"):
            errors.append("电路图缺完整节点/连线拓扑")
        if errors:
            # Figures are optional. A malformed diagram must never reject a
            # complete paper; keep the textual figure description instead.
            continue
        try:
            out = generate.ARTIFACT_ROOT.parent / "exam_figures" / f"{uuid.uuid4().hex}.png"
            res = figure_compiler.compile_figure(spec, subject=subject, out_path=out)
            if not res:
                continue
            digest = hashlib.md5(out.read_bytes()).hexdigest()
            if digest in figure_hashes:
                continue
            figure_hashes.add(digest)
            q["figure_spec"] = spec
            q["figure_data"] = "data:image/png;base64," + base64.b64encode(out.read_bytes()).decode()
            q["figure_caption"] = f"AI 生成配图（{subject}，程序绘制，请核对）"
        except Exception:
            continue
    return issues


def _dedupe_exam_figures(sections: list[dict]) -> int:
    """同一张资料图不要在整卷重复；只有题干明确提到图才挂原图。"""
    used: set[str] = set()
    removed = 0
    for sec in sections:
        for q in sec.get("questions") or []:
            asset = str(q.get("figure_asset") or "")
            if not asset:
                continue
            stem = str(q.get("stem") or "")
            desc = str(q.get("figure_description") or "")
            wants = bool(re.search(r"(如图|图中|图示|下图|上图|示意图|figure|diagram)", stem, re.I))
            original = bool(q.get("original_figure"))
            if (original or wants) and "无图" not in desc and (original or asset not in used):
                used.add(asset)
                continue
            q["figure_asset"] = ""
            q["figure_caption"] = ""
            removed += 1
    return removed


def run_exam(aid: str, *, mode: str = "mock", subject: str = "其他", difficulty: int = 3,
             types: str = "", blueprint_text: str = "", references: list[Path] | None = None,
             custom_prompt: str = "", gen_lang: str = "zh", client=None, work: Path | None = None,
             progress=None, checkpoint: dict | None = None, checkpoint_path: Path | None = None,
             allow_non_question: bool = False) -> dict:
    if mode not in MODES:
        raise ExamError("未知模式")
    difficulty = max(1, min(5, int(difficulty)))
    allowed_types = SUBJECT_TYPES.get(subject, SUBJECT_TYPES["其他"])
    chosen_types = [x.strip() for x in re.split(r"[,，、;；\s]+", types or "") if x.strip()]
    if not chosen_types:
        chosen_types = allowed_types
    chosen_types = [x for x in chosen_types if x in TYPE_LABELS] or allowed_types
    ref_text = ""
    if mode in ("change_numbers", "variant") and not references:
        raise ExamError("原题改数/原题变式需要先上传至少一份真题；否则请用模拟/预测模式")
    if references:
        work = work or (generate.UPLOAD_ROOT / "exam_refs")
        refs = []
        for p in references[:3]:
            try:
                refs.append(_reference_text(p, work))
            except Exception:
                continue
        ref_text = "\n\n".join(refs)[:7000]
    client = client or DeepSeekClient()
    bank = _cached_reference_bank(client, ref_text) if ref_text else {"items": [], "used": False}
    if references:
        refusal = reference_guard(ref_text, bank, allow_non_question=allow_non_question)
        if refusal:
            raise ExamError(refusal)
        if not (bank.get("items") or []):
            # 结构像题卷但没解析出题级清单：继续可用，但必须说明，不静默当结构参考。
            ref_text = ref_text
            bank = {**bank, "used": False, "reason": "题型结构未能拆到题级，只做文本参考"}
    # Question batches are the slow part of an exam. Generate them with Pro-low
    # (same model family, less reasoning) and keep the high-effort client for
    # blueprint/audit/tiebreak so quality gates still run at full strength.
    gen_client = client
    if isinstance(client, DeepSeekClient):
        try:
            gen_client = DeepSeekClient(model="deepseek-flash")
        except Exception:
            gen_client = client
    source, pages = _source_context(aid)
    if not pages:
        raise ExamError("这份讲义没有可用页码")
    path = service.artifact_path(aid)
    exclusion_specs = _artifact_exclusion_specs(path) if path is not None else []
    exclusion_meta = []
    page_text_for_specs: dict[int, str] = {}
    if path is not None:
        try:
            data_meta = json.loads((path / "sections.json").read_text(encoding="utf-8"))
            for sec in data_meta:
                sec_pages = set()
                for block in sec.get("blocks") or []:
                    for ref in block.get("source_refs") or []:
                        try:
                            sec_pages.update(range(int(ref.get("page_start")),
                                                   int(ref.get("page_end") or ref.get("page_start")) + 1))
                        except Exception:
                            continue
                exclusion_meta.append({"id": str(sec.get("id") or ""),
                                       "title": str(sec.get("title") or ""),
                                       "pages": sorted(sec_pages)})
            raw_pages = source_pages.load_source_pages(path)
            if raw_pages:
                page_text_for_specs = source_pages.page_map(raw_pages)
        except Exception:
            exclusion_meta = []
    matched_exclusions = exclusions.match_specs(
        exclusion_specs,
        exclusions.build_index(page_text_for_specs, exclusion_meta),
    )
    active_specs = [s for s in matched_exclusions if not s.get("needs_confirm")]
    exclusion_note = exclusions.exclusion_prompt(active_specs, "exam")
    excluded_pages = {
        p for spec in active_specs
        if spec.get("scope") in ("page", "section", "section_limit")
        for p in (spec.get("matched") or {}).get("pages") or []
    }
    pages = [p for p in pages if p not in excluded_pages]
    if not pages:
        raise ExamError("这份讲义的内容被用户全部排除")
    if progress:
        progress(15, "DeepSeek 正在设计试卷蓝图")
    audit_warnings: list[str] = []
    bp = _blueprint(client, subject=subject, types=chosen_types, difficulty=difficulty,
                    reference=ref_text, user_blueprint=(blueprint_text + ("\n" + exclusion_note if exclusion_note else "")), mode=mode, gen_lang=gen_lang)
    fidelity = bp.get("reference_fidelity") or {}
    if references and fidelity and not fidelity.get("ok"):
        audit_warnings.append(
            "参考真题的题型结构只还原了一部分：题型命中 {:.0%}、题量偏差 {:.0%}、分值偏差 {:.0%}".format(
                float(fidelity.get("type_recall") or 0), float(fidelity.get("count_error") or 0),
                float(fidelity.get("score_error") or 0))
        )
    if references and not bp.get("reference_structure"):
        audit_warnings.append(
            "参考真题的结构没有解析成功，这次按模型蓝图出卷，题型/题数可能与真题不同"
            + (f"（原因：{bp.get('reference_structure_error')}）" if bp.get("reference_structure_error") else "")
        )
    if bp.get("reference_structure") and str(blueprint_text or "").strip():
        audit_warnings.append("已按参考真题结构出卷：你的自定义蓝图这次没有生效（参考结构优先）")
    deny_types = {s["value"] for s in active_specs if s.get("scope") == "question_type"}
    allow_types = {s["value"] for s in active_specs if s.get("scope") == "question_type_allow"}
    if deny_types or allow_types:
        kept_sections = [
            sec for sec in bp.get("sections") or []
            if sec.get("type") not in deny_types
            and (not allow_types or sec.get("type") in allow_types)
        ]
        if not kept_sections:
            raise ExamError("用户排除的题型覆盖了整张试卷，无法出卷")
        bp["sections"] = _norm_sections(kept_sections)
    if checkpoint and isinstance(checkpoint.get("sections"), list) and checkpoint["sections"]:
        bp["sections"] = checkpoint["sections"]
        if checkpoint.get("title"):
            bp["title"] = checkpoint["title"]
    path = service.artifact_path(aid)
    view = service.get_artifact(aid) or {}
    figure_map: dict[int, dict] = {}
    for fig in view.get("figure_list") or []:
        for pg in fig.get("source_pages") or []:
            figure_map.setdefault(int(pg), fig)
    if path is None:
        raise ExamError("找不到这份讲义；请先在课程里生成讲义")
    sections_path = path / "sections.json"
    if not sections_path.is_file():
        raise ExamError("这份资料还没有讲义结构（缺 sections.json），不能出卷；请先把它生成成讲义")
    try:
        data = json.loads(sections_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ExamError(f"讲义结构读取失败：{exc}") from exc
    page_text: dict[int, str] = {}
    raw_pages = source_pages.load_source_pages(path)
    if raw_pages:
        page_text = source_pages.page_map(raw_pages)
    else:
        for sec in data:
            for b in sec.get("blocks") or []:
                text = str(b.get("text") or "")
                for ref in b.get("source_refs") or []:
                    try:
                        for pg in range(int(ref["page_start"]), int(ref.get("page_end") or ref["page_start"]) + 1):
                            page_text[pg] = page_text.get(pg, "") + "\n" + text
                    except Exception:
                        continue
    all_questions: list[dict] = []
    seen_stems: set[str] = set()
    seen_norm: list[str] = []
    issues: list[str] = []

    def _too_similar(stem: str) -> bool:
        norm = tasks._norm(stem)[:180]
        if norm and norm in seen_stems:
            return True
        return any(difflib.SequenceMatcher(None, norm, prev).ratio() >= 0.86 for prev in seen_norm if prev)

    def _remember_stem(stem: str) -> None:
        norm = tasks._norm(stem)[:180]
        if norm:
            seen_stems.add(norm)
            seen_norm.append(norm)
    for _sec in bp["sections"]:
        for _q in _sec.get("questions") or []:
            all_questions.append(_q)
            _remember_stem(str(_q.get("stem") or ""))
    if checkpoint_path is not None:
        try:
            checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
            checkpoint_path.write_text(json.dumps({
                "artifact_id": aid, "mode": mode, "subject": subject,
                "difficulty": difficulty, "types": types,
                "custom_prompt": custom_prompt, "gen_lang": gen_lang,
                "title": bp.get("title"), "sections": bp["sections"],
            }, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
    page_plan = plan_question_pages(bp["sections"], pages)
    for si, sec in enumerate(bp["sections"], start=1):
        section_issues: list[str] = []
        if progress:
            progress(20 + int(55 * (si - 1) / max(1, len(bp["sections"]))),
                     f"生成第 {si}/{len(bp['sections'])} 部分：{sec['name']}")
        per = sec["score"] / max(1, sec["count"])
        bank_line = ""
        if bank.get("items"):
            bank_line = (
                "参考真题题级清单（每道新题必须选一道真题作为变式来源，在 variant_of 里写该真题题号；"
                "确实没有对应真题就写 \"new\"）："
                + "；".join(f"{i.get('no')}({i.get('type')},{i.get('points')}分,{i.get('topic')})" for i in bank["items"][:20])
            )
        system = (
            f"你是大学{TYPE_LABELS[sec['type']]}命题老师。只依据给定讲义和参考真题，出 {sec['count']} 道"
            f"{TYPE_LABELS[sec['type']]}，每题 {per:.1f} 分，满分 {sec['score']} 分。"
            f"模式：{MODES[mode]}；科目：{subject}；难度：{difficulty}/5。"
            "题目必须有真实背景/条件/推理，不是只给公式套数；难度有区分度但不能极端。"
            "覆盖与多样性硬要求：source_page 必须尽量分散，整卷至少覆盖给定页码的 60%；"
            "同一页最多 1 题；同一疾病/同一情境/同一模板最多 1 题，禁止只换数字重复同一题。"
            "每题必须有 qtype、stem、answer_text（选择题用 answer 0-3 + 4 选项）、analysis、source_page、source_no、variant_of、needs_figure、original_figure、figure_description。"
            "needs_figure=true 仅在题目确实需要配图；不需要图时写 false、figure_description='无图'。"
            "mock/predict 新题绝不复用讲义 PPT 图；需要图时只输出 figure_spec，由程序生成。"
            "原题改数时，只有原题本身有图才把 original_figure 设为 true；否则 false。"
            "如果需要图，figure_spec 可输出结构化绘图（不要生成图片）："
            '{"kind":"circuit|force|geometry","elements":['
            '{"type":"battery","x":80,"y":200,"length":60,"orientation":"v","label":"U","value":"12V"},'
            '{"type":"resistor","x":300,"y":80,"length":100,"orientation":"h","label":"R1","value":"2Ω"},'
            '{"type":"wire","points":[[80,170],[80,80],[250,80]]},'
            '{"type":"arrow","x1":100,"y1":300,"x2":220,"y2":300,"label":"F"}]}。'
            "坐标范围 0–720 × 0–420；type 只能是 wire/resistor/capacitor/inductor/battery/switch/lamp/arrow/line/circle/rect/label/ground/node；"
            "label/value 必须来自题干，不能编造；画不出就省略 figure_spec，保留 figure_description。"
            f"题目、选项、解析用 {generate.GEN_LANG_LABEL.get(gen_lang, '简体中文')}；资料原文引用/术语保留原文。"
            "只输出 JSON：{\"questions\":[{...}]}。"
        )
        if bank_line:
            system += "\n" + bank_line
        if exclusion_note:
            system += "\n" + exclusion_note
        fig_ctx = "；".join(f"第{pg}页：{str(f.get('caption') or '')[:80]}" for pg, f in sorted((figure_map or {}).items()))
        qs: list[dict] = list(sec.get("questions") or [])
        if len(qs) >= sec["count"]:
            continue
        # 分批出题：一次 12 道容易截断/漏逗号；每批最多 4 道，稳定优先
        while len(qs) < sec["count"]:
            batch = min(4, sec["count"] - len(qs))
            prior_stems = "\n".join(f"- {q['stem'][:90]}" for q in all_questions[-16:])
            prior_stems += "\n" + "\n".join(f"- {q['stem'][:90]}" for q in qs)
            if prior_stems.strip() == "- ":
                prior_stems = ""
            batch_system = system.replace(f"出 {sec['count']} 道", f"出 {batch} 道")
            used_pages = sorted({q["source_page"] for q in all_questions})
            unused_pages = [p for p in pages if p not in used_pages]
            planned = page_plan[si - 1] if si - 1 < len(page_plan) else []
            assigned_pages = planned[len(qs):len(qs) + batch]
            if not assigned_pages:
                assigned_pages = (unused_pages or pages)[:batch]
            fallback_pages = [p for p in assigned_pages if p not in used_pages] or assigned_pages
            batch_user = (
                f"资料范围页码：{pages}\n资料页图注（仅原题改数可复用）：{fig_ctx or '无'}\n讲义：\n{source}\n\n参考真题格式：\n{ref_text[:4000] or '无'}\n"
                f"本部分：{sec['name']}，{TYPE_LABELS[sec['type']]}，本批 {batch} 题，共 {sec['count']} 题、{sec['score']} 分。\n"
                f"硬性页码分配：本批 {batch} 题的 source_page 必须依次为 {assigned_pages}（一题一页，顺序可换但不得重复、不得用其他页）；已覆盖页 {used_pages} 本批禁止使用。"
                f"已生成 {len(qs)} 题。优先使用未覆盖页：{fallback_pages or unused_pages}；同一页最多 1 题。用户补充：{custom_prompt or '无'}\n"
                f"禁止与下列已生成题干重复或近似重复：\n{prior_stems or '无'}\n"
                f"请输出本批 {batch} 道题的 JSON。"
            )
            try:
                raw = _json_retry(lambda: gen_client.json(batch_system, batch_user, max_tokens=12000, temperature=0.4))
                raw_qs = raw.get("questions")
                if not isinstance(raw_qs, list):
                    # 一批返回结构不对就整卷失败太脆：记下来，转下面的逐题补题。
                    section_issues.append(f"{sec['name']}：本批模型没给出题目，改逐题补")
                    break
                added = 0
                for rawq in raw_qs[:batch]:
                    q, issue = _parse_question(rawq, set(pages), page_text, mode, subject, expected_type=sec["type"], figure_map=figure_map, excluded_specs=active_specs)
                    if issue:
                        continue
                    if _too_similar(q["stem"]):
                        section_issues.append(f"{sec['name']}：重复题干已丢弃")
                        continue
                    _remember_stem(q["stem"])
                    q["score"] = round(per, 1)
                    qs.append(q)
                    added += 1
                if added == 0:
                    break
            except LLMError as exc:
                section_issues.append(f"{sec['name']} 分批生成失败：{exc}")
                break
        # 批量 JSON 失败/截断时，逐题补；比整卷直接失败可靠
        # 批量 JSON 失败/截断时，逐题补；比整卷直接失败可靠
        single_attempts = 0
        single_errors = 0
        while len(qs) < sec["count"] and single_attempts < max(4, sec["count"]):
            single_attempts += 1
            single_system = (
                f"你是大学{TYPE_LABELS[sec['type']]}命题老师。只出 1 道题，只输出 JSON："
                '{"question":{"qtype":"...","stem":"...","options":[...],"answer":0,"answer_text":"...",'
                '"analysis":"...","source_page":12,"source_no":"...","needs_figure":false,'
                '"original_figure":false,"figure_description":"无图","figure_spec":null}}。'
                f"题型 {TYPE_LABELS[sec['type']]}，难度 {difficulty}/5，科目 {subject}，模式 {MODES[mode]}。"
                f"解析最多 120 字；题干必须有背景/条件；题目/解析用 {generate.GEN_LANG_LABEL.get(gen_lang, '简体中文')}；不要 Markdown/代码围栏。"
                "选择题 options 必须是恰好 4 个不同字符串组成的数组，answer 是 0-3；少一个选项整题作废。"
                "每题带 variant_of（没有参考真题写 new）。"
                "只有确实需要图时才 needs_figure=true 并提供 figure_spec；原题改数只在原题有图时 original_figure=true。"
            )
            single_user = (
                f"资料页码：{pages}\n讲义节选：{source[:5500]}\n本部分：{sec['name']}，第 {len(qs)+1}/{sec['count']} 题。"
                f"用户补充：{custom_prompt or '无'}。请输出 1 道题的 JSON。"
            )
            try:
                raw1 = _json_retry(lambda: gen_client.json(single_system, single_user, max_tokens=8000, temperature=0.2))
                qraw = raw1.get("question")
                if not isinstance(qraw, dict):
                    qlist = raw1.get("questions")
                    qraw = qlist[0] if isinstance(qlist, list) and qlist else None
                if not isinstance(qraw, dict):
                    break
                q, issue = _parse_question(qraw, set(pages), page_text, mode, subject, expected_type=sec["type"], figure_map=figure_map, excluded_specs=active_specs)
                if issue:
                    section_issues.append(f"{sec['name']}：{issue}")
                    continue
                if _too_similar(q["stem"]):
                    section_issues.append(f"{sec['name']}：重复题干已丢弃")
                    continue
                _remember_stem(q["stem"])
                q["score"] = round(per, 1)
                qs.append(q)
            except LLMError:
                single_errors += 1
                if single_errors >= 2:
                    break
                continue
        if len(qs) < sec["count"]:
            # 缺口只记成提示：后面可能有补充题把它填上，真正的判定交给 audit_paper
            # 按最终题量/分值统一做，避免“已经补齐却还挂着旧错误”。
            audit_warnings.extend(section_issues)
            audit_warnings.append(f"{sec['name']} 生成过程中缺题：{len(qs)}/{sec['count']}（已尝试补充）")
        # If the section was refilled to its required count, its transient parse
        # failures are no longer paper-level defects.
        if qs:
            qs = qs[:sec["count"]]
            used = round(sum(float(q["score"]) for q in qs[:-1]), 1)
            qs[-1]["score"] = round(float(sec["score"]) - used, 1)
            issues.extend(f"{sec['name']}：{x}" for x in _attach_specs(client, qs, subject, gen_lang))
        sec["questions"] = qs
        existing_ids = {id(x) for x in all_questions}
        all_questions.extend([q for q in qs if id(q) not in existing_ids])
        if checkpoint_path is not None:
            try:
                checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
                checkpoint_path.write_text(json.dumps({
                    "artifact_id": aid, "mode": mode, "subject": subject,
                    "difficulty": difficulty, "types": types,
                    "custom_prompt": custom_prompt, "gen_lang": gen_lang,
                    "title": bp.get("title"), "sections": bp["sections"],
                }, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception:
                pass
    topup = _top_up_sections(bp, pages, page_text, mode, subject, figure_map, gen_client,
                             difficulty=difficulty, gen_lang=gen_lang, custom_prompt=custom_prompt)
    if topup["filled"]:
        audit_warnings.append(f"补题：为凑够题量追加 {topup['filled']} 道（已重新对齐分值）")
    _dedupe_exam_figures(bp["sections"])
    _relabel_question_pages(bp, pages, page_text)
    coverage_client = gen_client
    if isinstance(client, DeepSeekClient):
        try:
            coverage_client = DeepSeekClient(model="deepseek-v4-pro", effort="low")
        except Exception:
            coverage_client = gen_client
    # 用户自带蓝图时，尊重用户题型/题量：不为了覆盖率悄悄加题。
    if bp.get("user_blueprint"):
        audit_warnings.append("用户自定义蓝图：按你的题型/题量出卷，未追加覆盖补充题")
    else:
        _repair_exam_coverage(bp, pages, page_text, mode, subject, figure_map, coverage_client, active_specs)
    if progress:
        progress(82, "DeepSeek 正在审计答案 / 冲突复核")
    # 选择题答案审计
    choice = [q for q in all_questions if q["qtype"] == "choice"]
    audit = {"checked": False, "conflicts": [], "manual": len(all_questions) - len(choice) > 0}
    # Answer auditing is mechanical and must be fast. Flash is enough here and
    # keeps a Pro paper from spending another 3 minutes on a 600-token answer
    # list that was truncating.
    audit_client = client
    try:
        if isinstance(client, DeepSeekClient):
            audit_client = DeepSeekClient(model="deepseek-v4-pro", effort="low")
    except Exception:
        pass
    def _solve_with(ac, batch: list[dict]) -> list[int] | None:
        try:
            audited = ac.json(
                "你是独立解题人。不要看答案，只根据题干/选项解题。只输出 JSON：{\"answers\":[0,1,...]}。",
                "\n\n".join(f"{i+1}. {q['stem']}\n" + "\n".join(f"{chr(65+j)}. {o}" for j, o in enumerate(q["options"]))
                            for i, q in enumerate(batch)),
                max_tokens=1500, temperature=0.1,
            )
            ans = audited.get("answers")
            if not isinstance(ans, list) or len(ans) != len(batch):
                return None
            parsed: list[int] = []
            for x in ans:
                if isinstance(x, int):
                    parsed.append(x)
                    continue
                text = str(x).strip().upper()
                if text in ("A", "B", "C", "D"):
                    parsed.append(ord(text) - 65)
                else:
                    try:
                        parsed.append(int(text))
                    except ValueError:
                        parsed.append(-1)
            if any(a not in range(4) for a in parsed):
                return None
            return parsed
        except (LLMError, ValueError, TypeError):
            return None

    def _solve_batch(batch: list[dict]) -> list[int] | None:
        for ac in (audit_client, client):
            if ac is None:
                continue
            parsed = _solve_with(ac, batch)
            if parsed is not None:
                return parsed
        return None

    if choice:
        # Audit in small batches; fall back to one-question-at-a-time on failure.
        answers: list[int] = []
        audit_failed = False
        for start in range(0, len(choice), 2):
            batch = choice[start:start + 2]
            parsed = _solve_batch(batch)
            if parsed is None:
                parsed = []
                for q in batch:
                    single = _solve_batch([q])
                    if single is None:
                        audit_failed = True
                        parsed.append(-1)
                    else:
                        parsed.append(single[0])
            answers.extend(parsed)
        if audit_failed or len(answers) != len(choice) or any(a not in range(4) for a in answers):
            audit_warnings.append("选择题自动审计未完成（分批与单题均失败），不阻塞交付")
        else:
            audit["checked"] = True
            for i, (q, a) in enumerate(zip(choice, answers)):
                if a != q["answer"]:
                    audit["conflicts"].append({"no": i + 1, "paper": q["answer"], "audit": a,
                                               "stem": q["stem"], "options": q["options"]})
    resolved = []
    for conf in list(audit["conflicts"]):
        idx = conf["no"] - 1
        if not (0 <= idx < len(choice)):
            continue
        q = choice[idx]
        try:
            judge = audit_client.json(
                "你是第三位独立阅卷人。只根据题干和选项判断唯一正确答案；不要看“试卷答案”或“审计答案”的权威性。"
                '只输出 JSON：{"answer":0,"reason":"..."}。',
                f"题干：{q['stem']}\n" + "\n".join(f"{chr(65+j)}. {o}" for j, o in enumerate(q["options"]))
                + f"\n试卷答案：{chr(65+conf['paper'])}；审计答案：{chr(65+conf['audit'])}。请给最终答案。",
                max_tokens=600, temperature=0.1,
            )
            final = int(judge.get("answer"))
            if final in range(4):
                if final == q["answer"]:
                    conf["resolution"] = "paper"
                elif final == conf["audit"]:
                    q["answer"] = final
                    q["answer_text"] = chr(65 + final)
                    conf["resolution"] = "audit"
                else:
                    q["answer"] = final
                    q["answer_text"] = chr(65 + final)
                    conf["resolution"] = "tiebreak"
                resolved.append(conf)
        except Exception:
            continue
    if resolved:
        audit["conflicts"] = [c for c in audit["conflicts"] if c not in resolved]
        audit["resolved"] = len(resolved)
    # 三审仍冲突：换一道同页、无歧义的新选择题，并独立复核新答案
    fresh_resolved = 0
    still = []
    for conf in list(audit["conflicts"]):
        idx = conf["no"] - 1
        if not (0 <= idx < len(choice)):
            still.append(conf)
            continue
        q = choice[idx]
        parent = next((sec for sec in bp["sections"] if q in sec.get("questions", [])), None)
        if parent is None:
            still.append(conf)
            continue
        ok = False
        for attempt in range(2):
            try:
                fresh = gen_client.json(
                    "你是命题老师。上一道选择题答案存在争议，请换一道同页、考查同一考点、表述无歧义的新选择题。"
                    '只输出 JSON：{"question":{"qtype":"choice","stem":"...","options":["A","B","C","D"],'
                    '"answer":0,"analysis":"...","source_page":12,"source_no":"..."}}。',
                    f"资料页：{q['source_page']}\n原题：{q['stem']}\n请换题，不要重复原题。",
                    max_tokens=1800, temperature=0.5,
                )
                rawq = fresh.get("question") or (fresh.get("questions") or [None])[0]
                newq, issue = _parse_question(rawq, set(pages), page_text, mode, subject, expected_type="choice", figure_map=figure_map, excluded_specs=active_specs)
                if issue or not newq:
                    continue
                check = client.json(
                    '你是独立解题人。只根据题干/选项解题，只输出 JSON：{"answer":0}。',
                    newq["stem"] + "\n" + "\n".join(f"{chr(65+j)}. {o}" for j, o in enumerate(newq["options"])),
                    max_tokens=300, temperature=0.1,
                )
                if int(check.get("answer")) == newq["answer"]:
                    newq["score"] = q.get("score", 0)
                    q.clear(); q.update(newq)
                    fresh_resolved += 1
                    ok = True
                    break
            except Exception:
                continue
        if not ok:
            still.append(conf)
    audit["conflicts"] = still
    if fresh_resolved:
        audit["resolved_fresh"] = fresh_resolved
    for c in audit["conflicts"]:
        issues.append(f"选择题第 {c['no']} 题答案审计冲突（换题重审仍未解决）")
    removed_excluded = 0
    for sec in bp["sections"]:
        kept_qs, removed = exclusions.filter_questions(sec.get("questions") or [], active_specs, "exam")
        if removed:
            sec["questions"] = kept_qs
            removed_excluded += removed
    if removed_excluded:
        issues.append(f"用户排除的题目已过滤：{removed_excluded} 题")
    all_questions = [q for sec in bp["sections"] for q in sec.get("questions") or []]
    paper = audit_paper(bp)
    total = paper["total_score"]
    for msg in paper["issues"]:
        if msg not in issues:
            issues.append(msg)
    if progress:
        progress(96, "本地整理试卷 / 生成结果")
    if not issues and not audit["conflicts"]:
        status = "validated" if audit["checked"] else "review"
    else:
        status = "rejected"
    result = {
        "kind": "exam", "title": bp["title"], "artifact_id": aid, "section": "",
        "status": status, "issues": issues, "warnings": audit_warnings,
        "coverage": {"pages": pages, "pages_cited": sorted({q["source_page"] for q in all_questions})},
        "content": {"mode": mode, "subject": subject, "difficulty": difficulty,
                    "sections": bp["sections"], "total_score": round(total, 1),
                    "answer_audit": audit, "paper_audit": paper,
                    "blueprint_source": ("user" if bp.get("user_blueprint")
                                         else "reference" if bp.get("reference_structure") else "default"),
                    "reference_used": bool(ref_text),
                    "reference_structure": bool(bp.get("reference_structure")),
                    "reference_bank": bank,
                    "exclusions": exclusions.report(active_specs, removed_questions=removed_excluded)},
    }
    try:
        from tfv2.product import coverage
        path = service.artifact_path(aid)
        if path is not None:
            module = coverage.module_coverage(result, len(pages))
            coverage.write_report(path, {"material": aid, "page_count": len(pages),
                                         "scanned_pages": len(pages), "coverage_percent": 100.0,
                                         "status_counts": {}, "pages": []},
                                  [module], filename="coverage_exam.json")
    except Exception:
        pass
    return delivery.apply_exam_delivery(result)

"""答案双解校验：第二遍不看答案独立作答，再和已有答案对比。

- 选择题：比字母；
- 填空题：比规范化后的最终值；
- 计算题：多问/多步，默认标“需人工复核”，不假装自动判对。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

ANSWER_SPLIT_RE = re.compile(r"(?m)^#\s*答案与解析\s*$")
SECTION_RE = re.compile(r"(?m)^##\s+(.+?)\s*$")
ANS_ITEM_RE = re.compile(r"(?m)^\s*(\d+)\.\s*\*\*(.+?)\*\*")
CHOICE_RE = re.compile(r"^[A-D]$")


@dataclass
class AnswerCheck:
    section: str
    no: int
    expected: str
    got: str
    status: str  # match / mismatch / manual
    note: str = ""


@dataclass
class AnswerReport:
    total: int = 0
    match: int = 0
    mismatch: int = 0
    manual: int = 0
    items: list[AnswerCheck] = field(default_factory=list)


def split_exam(md: str) -> tuple[str, str]:
    m = ANSWER_SPLIT_RE.search(md or "")
    if not m:
        return md or "", ""
    return md[:m.start()], md[m.end():]


def answer_key(answer_md: str) -> dict[tuple[str, int], str]:
    out = {}
    section = ""
    for line in (answer_md or "").splitlines():
        sm = SECTION_RE.match(line)
        if sm:
            section = sm.group(1).strip()
            continue
        am = ANS_ITEM_RE.match(line)
        if am:
            out[(section, int(am.group(1)))] = am.group(2).strip()
    return out


def _equivalent(a: str, b: str) -> bool:
    """数值/代数式/等式等价：无 sympy 时用多点数值抽样。"""
    if _norm(a) == _norm(b) and _norm(a):
        return True
    if "=" not in a or "=" not in b:
        return False
    def expr(x):
        x = (x or "").replace("$", "").replace("^", "**").strip()
        l, r = x.split("=", 1)
        return f"({l})-({r})"
    try:
        ea, eb = expr(a), expr(b)
        safe = {"__builtins__": {}, "sin": __import__("math").sin,
                "cos": __import__("math").cos, "tan": __import__("math").tan}
        for xv, yv in ((1.0, 2.0), (2.0, 3.0), (-1.0, 0.5)):
            env = {**safe, "x": xv, "y": yv, "t": xv, "e": 2.718281828}
            if abs(eval(ea, env) - eval(eb, env)) > 1e-6:
                return False
        return True
    except Exception:
        return False


def _norm(text: str) -> str:
    t = (text or "").replace("\\dfrac", "").replace("\\frac", "")
    t = t.replace("dfrac", "").replace("frac", "")
    t = re.sub(r"[\\${}()\[\]\s]", "", t)
    return t.replace("−", "-").replace("，", ",").replace("；", ";")


def compare(key: dict[tuple[str, int], str], got: dict[tuple[str, int], str]) -> AnswerReport:
    rep = AnswerReport()
    for k, expected in key.items():
        rep.total += 1
        section, no = k
        actual = got.get(k, "")
        if "选择" in section or "单项" in section:
            el = re.findall(r"[A-D]", expected)
            gl = re.findall(r"[A-D]", actual)
            e = el[0] if el else ""
            g = gl[0] if gl else ""
            if e and e == g:
                rep.match += 1; status = "match"
            elif g:
                rep.mismatch += 1; status = "mismatch"
            else:
                rep.manual += 1; status = "manual"
        elif "填空" in section:
            ep = [x for x in re.split(r"[;；]", expected) if x.strip()]
            gp = [x for x in re.split(r"[;；]", actual) if x.strip()]
            if _norm(actual) and len(ep) == len(gp) and all(_equivalent(x, y) for x, y in zip(ep, gp)):
                rep.match += 1; status = "match"
            elif _norm(actual):
                rep.mismatch += 1; status = "mismatch"
            else:
                rep.manual += 1; status = "manual"
        else:
            rep.manual += 1; status = "manual"
        rep.items.append(AnswerCheck(section, no, expected, actual, status))
    return rep


def independent_prompt(question_md: str) -> str:
    return f"""你是独立阅卷人。下面只有题目，没有任何标准答案。请逐题独立作答。
选择题只写字母；填空题按空格顺序写最终值；计算题写清各小问最终结果。
只输出 JSON，不要解释：
{{"answers":[{{"section":"单项选择题","no":1,"answer":"B"}},{{"section":"填空题","no":1,"answer":"-1; x+y=3"}}]}}

【题目】
{question_md}
"""


def parse_independent(text: str) -> dict[tuple[str, int], str]:
    try:
        m = re.search(r"\{.*\}", text or "", re.S)
        data = json.loads(m.group(0)) if m else {}
    except Exception:
        return {}
    out = {}
    for item in data.get("answers") or []:
        try:
            out[(str(item.get("section") or ""), int(item.get("no")))] = str(item.get("answer") or "")
        except Exception:
            continue
    return out

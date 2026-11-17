
"""Small deterministic math checks for generated exam answers.

This is deliberately conservative: it only flags a question when both the
answer and the analysis expose a single parseable expression and SymPy can
prove they are not equal. It is not a solver and never rewrites an answer.
"""
from __future__ import annotations

import re

_NUM_EXPR = re.compile(r"[-+]?\d+(?:\.\d+)?(?:\s*/\s*\d+(?:\.\d+)?)?")
_ARITH = re.compile(r"(-?\d+(?:\.\d+)?)\s*([+\-*/])\s*(-?\d+(?:\.\d+)?)\s*=\s*(-?\d+(?:\.\d+)?)")
_TAIL_PATTERNS = (
    r"(?:答案|结果|所以|故|得|为)\s*[:：=]?\s*\$?([^，。；;、\n]{1,80})",
    r"=\s*\$?([^，。；;、\n]{1,80})",
)


def _clean(text: str) -> str:
    return (
        str(text or "")
        .replace("$", "")
        .replace("\\dfrac", "\\frac")
        .replace("\\left", "")
        .replace("\\right", "")
        .replace("\\,", "")
        .replace("\\;", "")
        .replace("\\!", "")
        .replace("\\cdot", "*")
        .replace("\\times", "*")
        .strip()
    )


def parse_expr(text: str):
    if not text or "=" in text or len(text) > 120:
        return None
    if re.search(r"[\u4e00-\u9fff，。；、]", text):
        return None
    try:
        from sympy.parsing.latex import parse_latex
        return parse_latex(_clean(text))
    except Exception:
        return None


def equivalent(a, b) -> bool | None:
    try:
        import sympy as sp
        if a is None or b is None:
            return None
        diff = sp.simplify(a - b)
        if diff == 0:
            return True
        if a.is_number and b.is_number:
            return bool(sp.N(sp.Abs(a - b)) < 1e-9)
        return False
    except Exception:
        return None


def final_exprs(analysis: str) -> list[tuple[str, object]]:
    """Return parseable expressions near the end, latest first."""
    text = _clean(analysis)
    out: list[tuple[str, object]] = []
    for segment in reversed(re.split(r"[。；;\n]", text)):
        for match in re.finditer(r"(?:=|为|得|答案[是为：:]?)\s*([^，。；;、]{1,80})", segment):
            cand = match.group(1).strip()
            # A candidate may still carry a short left side (e.g. y''=...).
            if "=" in cand:
                cand = cand.split("=", 1)[-1].strip()
            expr = parse_expr(cand)
            if expr is not None:
                out.append((cand, expr))
        if out:
            break
    return out


def last_analysis_expr(analysis: str) -> str:
    items = final_exprs(analysis)
    return items[0][0] if items else ""


def check_arithmetic(text: str) -> list[str]:
    issues: list[str] = []
    for lhs, op, rhs, claimed in _ARITH.findall(text or ""):
        try:
            a, b, c = float(lhs), float(rhs), float(claimed)
            value = {"+": a + b, "-": a - b, "*": a * b, "/": a / b if b else None}[op]
            if value is not None and abs(value - c) > 1e-9:
                issues.append(f"算术不成立：{lhs}{op}{rhs}={claimed}")
        except Exception:
            continue
    return issues


def audit_answer(q: dict) -> dict:
    if str(q.get("qtype") or "") == "choice":
        return {"checked": False, "issues": []}
    answer = str(q.get("answer_text") or "").strip()
    analysis = str(q.get("analysis") or "")
    issues: list[str] = []
    if not answer or not analysis:
        return {"checked": False, "issues": issues}
    # Multi-part answers need a human; do not guess.
    if any(sep in answer for sep in ("；", ";", "，", ",", "、", "或")):
        return {"checked": False, "issues": issues}
    if any(sep in answer for sep in ("_", "\\begin", "\\end")):
        return {"checked": False, "issues": issues}
    ans = parse_expr(answer)
    if ans is not None:
        candidates = final_exprs(analysis)
        if candidates:
            tail_text, tail = candidates[-1]
            # Do not compare a numeric answer with a function definition or a
            # different symbol (e.g. answer 1 vs analysis "sin 2x sin 3x").
            if ans.is_number != tail.is_number:
                return {"checked": False, "issues": issues}
            if (not ans.is_number and set(ans.free_symbols) != set(tail.free_symbols)):
                return {"checked": False, "issues": issues}
            same = equivalent(ans, tail)
            if same is False:
                issues.append(f"答案与解析最后结果不等：answer={answer} / analysis={tail_text}")
            return {"checked": True, "issues": issues}
    issues.extend(check_arithmetic(analysis))
    return {"checked": bool(issues), "issues": issues}

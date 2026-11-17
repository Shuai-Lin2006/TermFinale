"""LaTeX math -> Typst math conversion (lecture subset).

This is intentionally a deterministic converter, not a full TeX engine. It
covers the formulas our lecture generator actually emits: fractions, roots,
scripts, Greek/symbols, text, matrices/cases, sums/integrals/limits.
"""
from __future__ import annotations

import re

_SUB = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
_SUP = str.maketrans("0123456789+-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻")


def _chem_text(inner: str) -> str:
    """Conservative mhchem subset -> readable Unicode chemistry."""
    text = inner
    text = re.sub(r"\\text\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"\\mathrm\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"\\xrightarrow\{([^{}]*)\}", lambda m: "→(" + m.group(1) + ")" if m.group(1).strip() else "→", text)
    text = re.sub(r"\\xleftarrow\{([^{}]*)\}", lambda m: "←(" + m.group(1) + ")" if m.group(1).strip() else "←", text)
    text = re.sub(r"\\xrightleftharpoons\{([^{}]*)\}", "⇌", text)
    text = re.sub(r"\\xrightarrow", "→", text).replace("\\xleftarrow", "←")
    text = text.replace("<=>", "⇌").replace("->", "→").replace("<-", "←")
    text = text.replace("\\Delta", "Δ").replace("\\delta", "δ")
    # Isotopes: ^{14}_{6}C -> ¹⁴₆C
    text = re.sub(r"\^\{?([0-9]+)\}?", lambda m: m.group(1).translate(_SUP), text)
    text = re.sub(r"_\{?([0-9]+)\}?", lambda m: m.group(1).translate(_SUB), text)
    # Element counts: H2O -> H₂O, Ca(OH)2 -> Ca(OH)₂
    def sub(m):
        return m.group(1) + m.group(2).translate(_SUB)
    text = re.sub(r"([A-Z][a-z]?|[)\]])" + r"(\d+)", sub, text)
    # Charges: ^2- / ^+ -> superscripts
    def sup(m):
        return m.group(1).translate(_SUP)
    text = re.sub(r"\^(\d*[+-])", sup, text)
    text = re.sub(r"\^(\d+)", lambda m: m.group(1).translate(_SUP), text)
    text = re.sub(r"([A-Z][a-z]?|[)\]])[+]", lambda m: m.group(1) + "⁺", text)
    text = re.sub(r"([A-Z][a-z]?|[)\]])[-]", lambda m: m.group(1) + "⁻", text)
    text = text.replace("^", "")
    text = text.replace("\\cdot", "·").replace("\\nu", "ν").replace("\\mu", "μ")
    text = re.sub(r"\\[A-Za-z]+", "", text)
    text = text.replace("\\", "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


_GREEK = {
    "alpha": "alpha", "beta": "beta", "gamma": "gamma", "delta": "delta",
    "epsilon": "epsilon", "varepsilon": "epsilon", "zeta": "zeta", "eta": "eta",
    "theta": "theta", "vartheta": "theta", "iota": "iota", "kappa": "kappa",
    "lambda": "lambda", "mu": "mu", "nu": "nu", "xi": "xi", "pi": "pi",
    "rho": "rho", "sigma": "sigma", "tau": "tau", "upsilon": "upsilon",
    "phi": "phi", "varphi": "phi", "chi": "chi", "psi": "psi", "omega": "omega",
    "Gamma": "Gamma", "Delta": "Delta", "Theta": "Theta", "Lambda": "Lambda",
    "Xi": "Xi", "Pi": "Pi", "Sigma": "Sigma", "Phi": "Phi", "Psi": "Psi",
    "Omega": "Omega",
}
_SYMBOLS = {
    "rangle": "⟩",
    "langle": "⟨",
    "oint": "∮",
    "hbar": "ℏ",
    "le": "≤", "leq": "≤", "ge": "≥", "geq": "≥", "ne": "≠", "neq": "≠",
    "approx": "≈", "equiv": "≡", "sim": "∼", "times": "×",
    "cdot": "·", "pm": "±", "mp": "∓", "div": "÷",
    "to": "→", "rightarrow": "→", "leftarrow": "←", "Rightarrow": "⇒",
    "infty": "∞", "partial": "∂", "nabla": "∇", "forall": "∀",
    "exists": "∃", "in": "∈", "notin": "∉", "subset": "⊂",
    "subseteq": "⊆", "cup": "∪", "cap": "∩", "emptyset": "∅",
    "sum": "∑", "prod": "∏", "int": "∫", "iint": "∬",
    "lim": "lim", "log": "log", "ln": "ln", "sin": "sin", "cos": "cos", "tan": "tan",
    "max": "max", "min": "min", "deg": "degree", "angle": "angle",
    "quad": "space", "qquad": "space space", "ldots": "dots", "cdots": "dots",
    "dots": "dots", "prime": "prime",
}


def _read_group(s: str, i: int) -> tuple[str, int]:
    while i < len(s) and s[i].isspace():
        i += 1
    if i >= len(s):
        return "", i
    if s[i] != "{":
        return s[i], i + 1
    depth = 0
    start = i + 1
    while i < len(s):
        if s[i] == "{":
            depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth == 0:
                return s[start:i], i + 1
        i += 1
    return s[start:], i


def _text_group(inner: str) -> str:
    inner = inner.replace("\\_", "_").replace("\\%", "%").replace("\\&", "&")
    inner = inner.replace('"', '\\"')
    return f'"{inner}"'


def _convert_matrix(env: str, body: str) -> str:
    delim = {"pmatrix": "(", "bmatrix": "[", "vmatrix": "|", "Vmatrix": "||", "matrix": "("}.get(env, "(")
    rows = re.split(r"\\\\", body)
    row_src = []
    for row in rows:
        cells = [c.strip() for c in row.split("&")]
        if not any(cells):
            continue
        row_src.append(", ".join(convert_math(c) for c in cells))
    if not row_src:
        return "mat()"
    return f'mat(delim: "{delim}", ' + "; ".join(row_src) + ")"


def _convert_aligned(body: str) -> str:
    rows = re.split(r"\\\\", body)
    parts = []
    for row in rows:
        cells = [c.strip().replace("&", "").lstrip("=").strip() for c in row.split("&")]
        if any(cells):
            parts.append(" = ".join(convert_math(c) for c in cells if c))
    if not parts:
        return ""
    return 'mat(delim: #none, ' + "; ".join(parts) + ")" if len(parts) > 1 else parts[0]


def _convert_cases(body: str) -> str:
    rows = re.split(r"\\\\", body)
    parts = []
    for row in rows:
        cells = [c.strip() for c in row.split("&")]
        if not any(cells):
            continue
        parts.append(", ".join(convert_math(c) for c in cells))
    return "cases(" + "; ".join(parts) + ")"


def _convert_command(name: str, s: str, i: int) -> tuple[str, int]:
    if name == "ce":
        inner, i = _read_group(s, i)
        return f'"{_chem_text(inner).replace(chr(34), chr(92)+chr(34))}"', i
    if name in ("chemfig", "schemestart"):
        _ignored, i = _read_group(s, i)
        return '"【化学结构式】"', i
    if name == "SI":
        a, i = _read_group(s, i)
        b, i = _read_group(s, i)
        unit = _chem_text(b).replace("^2", "²").replace("^3", "³")
        return f'"{_chem_text(a)} {unit}"', i
    if name in ("vec", "hat", "bar", "dot", "ddot"):
        inner, i = _read_group(s, i)
        fn = {"vec": "arrow", "hat": "hat", "bar": "overline", "dot": "dot", "ddot": "dot.double"}.get(name, "arrow")
        return f" {fn}({convert_math(inner)}) ", i
    if name in ("frac", "dfrac", "tfrac"):
        a, i = _read_group(s, i)
        b, i = _read_group(s, i)
        return f"({convert_math(a)})/({convert_math(b)})", i
    if name == "sqrt":
        while i < len(s) and s[i].isspace():
            i += 1
        if i < len(s) and s[i] == "[":
            end = s.find("]", i)
            if end != -1:
                n = s[i + 1:end]
                x, i = _read_group(s, end + 1)
                return f"root({convert_math(n)}, {convert_math(x)})", i
        x, i = _read_group(s, i)
        return f"sqrt({convert_math(x)})", i
    if name in ("text", "textrm", "mathrm", "mathbf", "mathit", "operatorname"):
        inner, i = _read_group(s, i)
        if name == "mathrm" and any(x in inner for x in ("xrightarrow", "xleftarrow", "xrightleftharpoons", "Cl", "CH", "Cl_2")):
            return '"' + _chem_text(inner).replace('"', '\\"') + '"', i
        if "_" in inner or "^" in inner:
            # Keep simple subscripts/superscripts outside the quoted text.
            m = re.match(r"^([^_^{}]+)([_^])([^{}]+)$", inner)
            if m:
                head, op, tail = m.groups()
                return f'{_text_group(head)}{op}{convert_math(tail)}', i
        return _text_group(inner), i
    if name == "begin":
        env, i = _read_group(s, i)
        end_tag = f"\\end{{{env}}}"
        end = s.find(end_tag, i)
        if end == -1:
            return "", i
        body = s[i:end]
        if env in ("aligned", "align", "gathered", "split"):
            return _convert_aligned(body), end + len(end_tag)
        if env in ("pmatrix", "bmatrix", "vmatrix", "Vmatrix", "matrix"):
            return _convert_matrix(env, body), end + len(end_tag)
        if env in ("cases", "array"):
            return _convert_cases(body), end + len(end_tag)
        return convert_math(body), end + len(end_tag)
    if name in ("left", "right", "big", "Big", "bigg", "Bigg"):
        return "", i
    if name in ("displaystyle", "textstyle", "scriptstyle"):
        return "", i
    if name == "\\":
        return " \\ ", i
    if name in _GREEK:
        return " " + _GREEK[name] + " ", i
    if name in _SYMBOLS:
        return " " + _SYMBOLS[name] + " ", i
    # Unknown command: render its name as an upright identifier rather than
    # leaking a backslash into Typst.
    return f'"{name}"', i


def convert_math(expr: str) -> str:
    s = (expr or "").strip()
    i = 0
    out: list[str] = []
    while i < len(s):
        ch = s[i]
        if ch == "\\":
            if i + 1 < len(s) and s[i + 1] in "{}%$&#_":
                out.append(s[i + 1]); i += 2; continue
            if i + 1 < len(s) and s[i + 1] == "\\":
                out.append(" \\ "); i += 2; continue
            m = re.match(r"\\([A-Za-z]+)", s[i:])
            if m:
                name = m.group(1)
                piece, i = _convert_command(name, s, i + len(m.group(0)))
                out.append(piece)
                continue
            i += 1
            continue
        if ch in "_^":
            # Typst groups scripts with parentheses when >1 token.
            j = i + 1
            while j < len(s) and s[j].isspace():
                j += 1
            if j < len(s) and s[j] == "{":
                inner, j = _read_group(s, j)
                out.append(ch + "(" + convert_math(inner) + ")")
                if j < len(s) and s[j].isalpha():
                    out.append(" ")
                i = j
                continue
            if j < len(s) and s[j] == "\\":
                m = re.match(r"\\([A-Za-z]+)", s[j:])
                if m:
                    piece, j2 = _convert_command(m.group(1), s, j + len(m.group(0)))
                    out.append(ch + piece)
                    if j2 < len(s) and s[j2].isalpha():
                        out.append(" ")
                    i = j2; continue
            if j < len(s):
                out.append(ch + s[j])
                if j + 1 < len(s) and s[j + 1].isalpha():
                    out.append(" ")
                i = j + 1; continue
        if ch == "~":
            out.append(" "); i += 1; continue
        out.append(ch)
        # Typst treats adjacent ASCII letters as one identifier (dt -> unknown
        # variable). Separate ordinary math letters; quoted text/commands are
        # inserted as whole pieces and are unaffected.
        if ch.isalpha() and i + 1 < len(s) and s[i + 1].isalpha():
            out.append(" ")
        i += 1
    text = "".join(out)
    # Common TeX spacing and escapes.
    for a, b in (("{", "("), ("}", ")"), ("\\,", " "), ("\\;", " "), ("\\!", ""), ("\\ ", " ")):
        text = text.replace(a, b)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def latex_to_typst_segments(text: str) -> str:
    """Convert $$...$$ and $...$ segments in prose; leave other text alone."""
    def repl(m):
        body = m.group(1) if m.group(1) is not None else m.group(2)
        return "$" + convert_math(body) + "$"
    return re.sub(r"\$\$(.+?)\$\$|\$(.+?)\$", repl, text or "", flags=re.S)

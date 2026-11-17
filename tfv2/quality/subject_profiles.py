"""Cross-subject capability contracts for lecture output.

One quality contract for every subject; profiles only describe how a
representation (formula/figure/code/table) is expected to be rendered.
"""
from __future__ import annotations

from dataclasses import dataclass, field

UNIVERSAL_MODULES = ("objectives", "key_terms", "self_test", "source_index")
UNIVERSAL_GATES = ("coverage", "source", "formula", "figure", "layout", "delivery")


@dataclass(frozen=True)
class SubjectProfile:
    id: str
    label: str
    keywords: tuple[str, ...]
    formula: tuple[str, ...] = ("katex", "typst", "raster_fallback")
    figures: tuple[str, ...] = ("source_image", "vector_crop", "vision_check")
    structures: tuple[str, ...] = ()
    code: bool = False
    tables: bool = False
    notes: str = ""


PROFILES: tuple[SubjectProfile, ...] = (
    SubjectProfile("math", "数学", ("数学", "高数", "高等数学", "线性代数", "概率", "微积分")),
    SubjectProfile("physics", "物理", ("物理", "力学", "电磁", "热学", "光学", "量子")),
    SubjectProfile("chemistry", "化学", ("化学", "有机", "无机", "分析化学", "物理化学", "结构式"),
                   structures=("source_image", "rdkit_or_chemdraw", "structure_fallback")),
    SubjectProfile("circuits", "电路/电子", ("电路", "电子", "电工", "模拟电路", "数字电路"),
                   structures=("source_image", "circuit_diagram")),
    SubjectProfile("medical", "医学/生物", ("医学", "解剖", "生理", "病理", "生物", "药理"),
                   structures=("source_image", "medical_diagram")),
    SubjectProfile("law", "法学/人文", ("法学", "刑法", "民法", "宪法", "法理", "历史", "哲学")),
    SubjectProfile("economics", "经济/商科", ("经济", "金融", "会计", "管理", "商科"), tables=True),
    SubjectProfile("cs", "计算机", ("计算机", "算法", "数据结构", "编程", "操作系统", "网络"),
                   code=True, tables=True),
    SubjectProfile("general", "通用", ()),
)

PROFILE_BY_ID = {p.id: p for p in PROFILES}


def detect_subject(*, course: str = "", title: str = "", text: str = "") -> SubjectProfile:
    hay = f"{course} {title} {text[:5000]}"
    best = None
    best_score = 0
    for p in PROFILES:
        score = sum(hay.count(k) for k in p.keywords)
        if score > best_score:
            best, best_score = p, score
    return best or PROFILE_BY_ID["general"]


def capability_matrix(spec, *, formula_assets=None, figures=None) -> dict:
    course = getattr(getattr(spec, "header", None), "course", "") or ""
    title = getattr(getattr(spec, "header", None), "title", "") or ""
    sections = list(getattr(spec, "sections", []) or [])
    sample = " ".join((getattr(s, "title", "") or "") for s in sections[:5])
    profile = detect_subject(course=course, title=title, text=sample)
    module_presence = {
        "objectives": sum(1 for s in sections if getattr(s, "objectives", None)),
        "key_terms": sum(1 for s in sections if getattr(s, "key_terms", None)),
        "self_test": sum(1 for s in sections if getattr(s, "self_test", None)),
        "source_index": sum(1 for s in sections if getattr(s, "source_refs", None)),
    }
    assets = list(formula_assets or [])
    figs = list(figures or [])
    return {
        "profile": profile.id,
        "label": profile.label,
        "universal_modules": list(UNIVERSAL_MODULES),
        "universal_gates": list(UNIVERSAL_GATES),
        "modules": module_presence,
        "sections": len(sections),
        "formula_assets": len(assets),
        "formula_fallback": sum(1 for a in assets if getattr(a, "status", "ok") != "ok"),
        "figures": len(figs),
        "figure_sourced": sum(1 for f in figs if getattr(f, "origin", "") == "source"),
        "representations": {
            "formula": list(profile.formula),
            "figures": list(profile.figures),
            "structures": list(profile.structures),
            "code": profile.code,
            "tables": profile.tables,
        },
        "capabilities": {
            "code": "supported" if profile.code else "not_applicable",
            "tables": "supported" if profile.tables else "not_applicable",
            "structures": "needs_source_image" if profile.structures else "not_applicable",
        },
        "notes": profile.notes,
    }


def matrix_markdown(matrix: dict) -> str:
    lines = ["# 学科能力矩阵", "", f"- 识别学科：**{matrix.get('label')}** (`{matrix.get('profile')}`)",
             f"- 小节数：{matrix.get('sections')}", f"- 公式资产：{matrix.get('formula_assets')}，回退：{matrix.get('formula_fallback')}",
             f"- 图片：{matrix.get('figures')}，资料原图：{matrix.get('figure_sourced')}", "",
             "## 统一契约", ""]
    lines += [f"- {x}" for x in matrix.get("universal_modules") or []]
    lines += [f"- {x}" for x in matrix.get("universal_gates") or []]
    lines += ["", "## 表示层", ""]
    for k, v in (matrix.get("representations") or {}).items():
        lines.append(f"- {k}: {v}")
    return "\n".join(lines) + "\n"


def capability_gate(matrix: dict) -> dict:
    """Same contract across all subjects; warnings never pretend success."""
    issues: list[dict] = []
    sections = int(matrix.get("sections") or 0)
    mods = matrix.get("modules") or {}
    for key in UNIVERSAL_MODULES:
        if sections and int(mods.get(key) or 0) < sections:
            issues.append({"code": f"module.{key}", "severity": "warn",
                           "message": f"{key} 覆盖 {mods.get(key) or 0}/{sections}"})
    if int(matrix.get("formula_fallback") or 0) > 0:
        issues.append({"code": "formula.fallback", "severity": "warn",
                       "message": f"{matrix.get('formula_fallback')} 条公式未原生渲染"})
    profile = matrix.get("profile")
    reps = matrix.get("representations") or {}
    if reps.get("structures") and int(matrix.get("figures") or 0) == 0:
        issues.append({"code": "structure.no_figure", "severity": "warn",
                       "message": "该学科需要结构/图，但没有可用原图；不能伪造"})
    if reps.get("code"):
        issues.append({"code": "representation.code", "severity": "warn",
                       "message": "当前 schema 没有代码块专用渲染，需后续适配器"})
    if reps.get("tables"):
        issues.append({"code": "representation.table", "severity": "warn",
                       "message": "当前 schema 没有表格专用渲染，需后续适配器"})
    return {"profile": profile, "passed": not any(x["severity"] == "hard" for x in issues),
            "issues": issues}


def gate_markdown(gate: dict) -> str:
    lines = ["# 学科能力门禁", "", f"- 学科：{gate.get('profile')}",
             f"- 结果：{'通过' if gate.get('passed') else '失败'}", ""]
    for x in gate.get("issues") or []:
        lines.append(f"- `{x['code']}`（{x['severity']}）{x['message']}")
    return "\n".join(lines) + "\n"

"""Four-module golden verifier; local files only, no LLM."""
from __future__ import annotations
import json, sys
from pathlib import Path

from tfv2.product import question_bank


def read(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def verify(root: Path) -> dict:
    m = read(root / "data/golden/modules.json")
    out = {"modules": {}, "passed": True}
    def check(name, ok, detail=""):
        out["modules"].setdefault(name, {"passed": True, "checks": {}})
        out["modules"][name]["checks"][name] = {"ok": bool(ok), "detail": detail}
        if not ok:
            out["modules"][name]["passed"] = False
            out["passed"] = False

    # lecture
    aid = m["lecture"]["artifact"]; p = root / "data/artifacts" / aid
    man = read(p / "manifest.json") if (p / "manifest.json").is_file() else {}
    audit = read(p / "coverage_audit.json") if (p / "coverage_audit.json").is_file() else []
    covered = sum(1 for x in audit if x.get("status") == "covered")
    check("lecture", bool(man.get("gate", {}).get("passed")) and len(audit) >= 100 and covered >= 90,
          f"gate={man.get('gate',{}).get('passed')} pages={len(audit)} covered={covered}")

    def module_outputs(name):
        cfg = m[name]; ws = root / cfg["workspace"] / "outputs" / name
        rows = []
        for x in cfg["outputs"]:
            f = ws / f"{x}.json"
            rows.append(read(f) if f.is_file() else {})
        return rows

    p100 = root / "data/workspaces/modules_100p"
    ex = read(p100 / "gen_20261115_123905_f21786.json")["result"] if (p100 / "gen_20261115_123905_f21786.json").is_file() else {}
    check("extract", ex.get("status") == "validated" and ex.get("items", 0) >= 200 and ex.get("coverage", 0) >= 0.95,
          f"status={ex.get('status')} items={ex.get('items')} coverage={ex.get('coverage')}")
    exam = read(p100 / "gen_20261115_123905_f21786_exam.json")["result"] if (p100 / "gen_20261115_123905_f21786_exam.json").is_file() else {}
    check("exam", exam.get("status") == "validated" and exam.get("questions", 0) >= 40 and exam.get("total_score") == 100,
          f"status={exam.get('status')} questions={exam.get('questions')} score={exam.get('total_score')}")
    bank_path = root / "data/workspaces/math_answers/question_bank.json"
    bank = read(bank_path)["items"] if bank_path.is_file() else []
    groups = {}
    for x in bank:
        groups.setdefault(x.get("material_id"), []).append(x)
    ok = len(groups) >= 2 and all(len(g) >= 5 and question_bank.validated(g) for g in groups.values())
    check("questions", ok, str({k: (len(v), question_bank.validated(v)) for k, v in groups.items()}))
    return out


if __name__ == "__main__":
    res = verify(Path(__file__).resolve().parents[1])
    print(json.dumps(res, ensure_ascii=False, indent=2))
    sys.exit(0 if res["passed"] else 1)

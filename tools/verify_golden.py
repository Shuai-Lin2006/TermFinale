"""Local golden verifier: deterministic checks, no LLM calls."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def verify(manifest_path: Path, artifacts: Path) -> dict:
    m = json.loads(manifest_path.read_text(encoding="utf-8"))
    aid = m["artifact"]
    p = artifacts / aid
    out = {"name": m["name"], "artifact": aid, "checks": {}, "passed": True}

    def check(name, ok, detail=""):
        out["checks"][name] = {"ok": bool(ok), "detail": detail}
        if not ok:
            out["passed"] = False

    check("artifact_exists", p.is_dir(), str(p))
    if not p.is_dir():
        return out
    man = json.loads((p / "manifest.json").read_text(encoding="utf-8"))
    req = m["requirements"]
    check("gate", bool(man.get("gate", {}).get("passed")) == req["gate"], str(man.get("gate")))
    check("figures", int(man.get("figures") or 0) >= req["figures_min"], str(man.get("figures")))
    check("sections", int(man.get("sections") or 0) >= req["sections_min"], str(man.get("sections")))
    check("pdf_pages", int(man.get("pdf_pages") or 0) > 0, str(man.get("pdf_pages")))
    fact = json.loads((p / "fact_map.json").read_text(encoding="utf-8")) if (p / "fact_map.json").is_file() else None
    cov = float(fact.get("coverage") or 0) if isinstance(fact, dict) else 0.0
    check("fact_coverage", cov >= req["fact_coverage_min"], f"{cov:.3f} < {req['fact_coverage_min']}")
    audit = man.get("audit") or {}
    check("audit_ok", bool(audit.get("audit_ok")), str(audit))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ap.add_argument("--artifacts", default="data/artifacts")
    args = ap.parse_args()
    result = verify(Path(args.manifest), Path(args.artifacts))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()

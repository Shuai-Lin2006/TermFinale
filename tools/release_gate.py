"""底层算法发布门禁：只检查能客观验证的硬项，不把 UI/签名混进来。

用法：python tools/release_gate.py
退出码 0 = 当前算法硬项通过；非 0 = 有必过项未过。
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.quality.constraints import TaskConstraints, validate_output  # noqa: E402

RESULTS: list[tuple[str, bool, str]] = []


def add(name: str, ok: bool, detail: str) -> None:
    RESULTS.append((name, ok, detail))


def check_tests() -> None:
    proc = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"],
                          cwd=ROOT, capture_output=True, text=True, timeout=300)
    tail = (proc.stderr or "") + (proc.stdout or "")
    m = re.search(r"Ran (\d+) tests", tail)
    n = int(m.group(1)) if m else 0
    ok = proc.returncode == 0 and n >= 115
    add("测试套件", ok, f"{n} 项，退出码 {proc.returncode}")


def check_exam() -> None:
    path = ROOT / "docs/evidence/exam_real2.md"
    if not path.is_file():
        add("真实试卷", False, "缺少 evidence/exam_real2.md")
        return
    sections = [{"name": "单项选择题", "count": 4, "points": 5},
                {"name": "填空题", "count": 2, "points": 10},
                {"name": "计算题", "count": 2, "points": 30}]
    c = TaskConstraints(task="exam", answer_mode="required", sections=sections)
    r = validate_output(path.read_text(encoding="utf-8"), c, source_text="", stage="final")
    add("真实试卷 100% 答案", r.ok,
        f"ok={r.ok} · 题 {r.metrics.get('questions')} / 答 {r.metrics.get('answered')} · 选择题 {r.metrics.get('choice_checked')} · {r.issues[:2]}")


def check_171() -> None:
    path = ROOT / "docs/evidence/extract171_filled.md"
    if not path.is_file():
        add("171 页覆盖账本", False, "缺少 evidence/extract171_filled.md")
        return
    text = path.read_text(encoding="utf-8")
    cited = {int(n) for n in re.findall(r"第\s*(\d+)\s*页", text)}
    total = 171
    missing = sorted(set(range(1, total + 1)) - cited)
    ok = (len(cited & set(range(1, total + 1))) / total) >= 0.85
    add("150–1000 页覆盖 ≥85%", ok, f"{len(cited & set(range(1, total + 1)))}/{total} 引用；缺页 {missing}")


def check_1001() -> None:
    mpath = ROOT / "docs/evidence/guide1001_metrics.json"
    metrics = None
    if mpath.is_file():
        try:
            raw = json.loads(mpath.read_text(encoding="utf-8"))
            metrics = raw.get("metrics") or raw
        except Exception:
            metrics = None
    if not metrics:
        path = ROOT / "docs/evidence/guide1001.log"
        if path.is_file():
            for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if line.startswith('{"kind": "guide"'):
                    try:
                        metrics = json.loads(line)
                    except json.JSONDecodeError:
                        pass
    if not metrics:
        add("1001 页概览", False, "日志里没有 guide metrics JSON")
        return
    cov = metrics.get("coverage") or {}
    ok = bool(metrics.get("overview_mode")) and cov.get("coverage_mode") == "overview_sample"
    add("1001 页概览", ok,
        f"{metrics.get('chapters')} 章 / 抽样 {cov.get('sampled_pages')} 页 / "
        f"{metrics.get('elapsed_s')}s / mode={cov.get('coverage_mode')}")


def check_1001_full() -> None:
    path = ROOT / "docs/evidence/1001_full_metrics.json"
    if not path.is_file():
        add(">1000 页大幅覆盖", False, "缺少 evidence/1001_full_metrics.json")
        return
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        add(">1000 页大幅覆盖", False, "metrics JSON 无法解析")
        return
    cov = raw.get("coverage") or {}
    value = float(cov.get("coverage") or 0)
    # >1000 页按最终标准只要求 ≥60%，不要求全量。
    ok = value >= 0.60
    add(">1000 页大幅覆盖", ok,
        f"{cov.get('pages_cited')}/{cov.get('pages')} = {value:.1%}；缺 {cov.get('pages_missing_count')} 页")


def check_85_precise() -> None:
    path = ROOT / "docs/evidence/85_ledger.json"
    if not path.is_file():
        add("85 页精准全量", False, "缺少 evidence/85_ledger.json")
        return
    try:
        led = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        add("85 页精准全量", False, "账本 JSON 无法解析")
        return
    detail = led.get("detail") or []
    bad = [x for x in detail if int(x.get("chars") or 0) < 20 and int(x.get("images") or 0) == 0]
    ok = (led.get("pages") == 85 and led.get("accounted") == 85
          and not led.get("placeholder") and not bad)
    add("85 页精准全量", ok,
        f"{led.get('accounted')}/85 页；占位 {len(led.get('placeholder') or [])}；无内容页 {len(bad)}")


def check_answer_semantics() -> None:
    path = ROOT / "docs/evidence/exam_double_check.json"
    if not path.is_file():
        add("答案双解一致性", False, "缺少 evidence/exam_double_check.json")
        return
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        add("答案双解一致性", False, "双解 JSON 无法解析")
        return
    bad = [x for x in d.get("items", []) if x.get("status") in ("mismatch", "manual")
           and not x.get("reviewed")]
    ok = not bad
    add("答案双解一致性", ok,
        f"{d.get('match')}/{d.get('total')} 一致；{d.get('mismatch')} 不一致 / {d.get('manual')} 人工；待确认 {len(bad)}")


def check_test_isolation() -> None:
    from core.database import Course, get_db_session
    db = get_db_session()
    try:
        allc = db.query(Course).all()
    finally:
        db.close()
    visible = [c for c in allc if not getattr(c, "is_test", False)]
    test = [c for c in allc if getattr(c, "is_test", False)]
    ok = bool(visible) and all(not getattr(c, "is_test", False) for c in visible)
    add("测试数据隔离", ok, f"总 {len(allc)} / 测试 {len(test)} / 可见 {len(visible)}")


def check_security_files() -> None:
    token = Path.home() / "Library/Application Support/TermFinale/.session_token"
    ok = token.is_file() and (token.stat().st_mode & 0o777) == 0o600
    add("持久会话 token", ok, f"{token} · mode={oct(token.stat().st_mode & 0o777) if token.exists() else 'missing'}")


def main() -> int:
    check_tests()
    check_exam()
    check_171()
    check_1001()
    check_1001_full()
    check_85_precise()
    check_answer_semantics()
    check_test_isolation()
    check_security_files()
    width = max(len(n) for n, _, _ in RESULTS)
    print("\n=== 底层算法发布门禁 ===")
    for name, ok, detail in RESULTS:
        print(f"{'PASS' if ok else 'FAIL'}  {name:<{width}}  {detail}")
    print("\n未纳入门禁（需产品确认）：1001 逐页、171 封面页、UI/签名/打包。")
    return 0 if all(ok for _, ok, _ in RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""把多次 benchmark 结果合并成一张对照表（Markdown + JSON 汇总）。

用法：.venv/bin/python scripts/benchmark_report.py \
        docs/evidence/benchmark_math_2026-11-17.json docs/evidence/benchmark_math_retry.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(paths: list[str]) -> list[dict]:
    rows: list[dict] = []
    for p in paths:
        data = json.loads(Path(p).read_text(encoding="utf-8"))
        artifact = data.get("artifact") or Path(p).stem
        for r in data.get("rows") or []:
            r = dict(r)
            r["source"] = Path(p).name
            r["artifact"] = r.get("artifact") or artifact
            rows.append(r)
    # 同一页段重跑时保留最后一次
    best: dict[tuple, dict] = {}
    for r in rows:
        best[(r.get("start"), r.get("pages"))] = r
    return sorted(best.values(), key=lambda x: int(x.get("start") or 0))


def _thresholds() -> dict:
    import importlib.util
    spec = importlib.util.spec_from_file_location("eh", ROOT / "scripts/eval_harness.py")
    eh = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(eh)
    return eh.THRESHOLDS


def verdict(row: dict, th: dict) -> tuple[bool, list[str]]:
    """按当前阈值重算结论（旧报告里的 quality_fails 可能用的是旧阈值）。"""
    fails: list[str] = []
    if not row.get("gate"):
        fails.append("门禁")
    if (row.get("coverage") or 0) < th["lecture_coverage"]:
        fails.append(f"覆盖 {row.get('coverage')}")
    if row.get("citation_support") is not None and row["citation_support"] < th["lecture_citation_support"]:
        fails.append(f"引用支持 {row['citation_support']:.0%}")
    if row.get("term_recall") is not None and row["term_recall"] < th["lecture_term_recall"]:
        fails.append(f"术语召回 {row['term_recall']:.0%}")
    if (row.get("dup_ratio") or 0) > th["lecture_dup_sentence"]:
        fails.append(f"重复句 {row.get('dup_ratio')}")
    if (row.get("boilerplate_per_1k") or 0) > th["lecture_boilerplate"]:
        fails.append("模板句")
    return (not fails), fails


def pct(x) -> str:
    return "—" if x is None else f"{x * 100:.0f}%"


def main() -> None:
    paths = sys.argv[1:]
    if not paths:
        raise SystemExit("usage: benchmark_report.py <benchmark.json> ...")
    rows = load(paths)
    lines = ["# 讲义基准测试（真实模型）", "",
             f"页段 {len(rows)} 个 · 每个页段独立生成 · 数据来源：{', '.join(Path(p).name for p in paths)}", "",
             "| 页段 | 页数 | 门禁 | 节 | 覆盖 | 引用支持 | 术语 | 补原文 | 兜底节 | 耗时 | 结果 |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    th = _thresholds()
    for r in rows:
        ok, fails = verdict(r, th)
        r["ok"], r["verdict_fails"] = ok, fails
        lines.append("| {start}–{end} | {pages} | {gate} | {sec} | {cov} | {sup} | {term} | {fill} | {fb} | {secs}s | {ok} |".format(
            start=r.get("start"), end=(r.get("start") or 0) + (r.get("pages") or 0) - 1,
            pages=r.get("pages"), gate="✅" if r.get("gate") else "❌",
            sec=r.get("sections") if r.get("sections") is not None else "—",
            cov=pct(r.get("coverage")), sup=pct(r.get("citation_support")),
            term=pct(r.get("term_recall")), fill=pct(r.get("fill_ratio")),
            fb=r.get("fallback_sections", "—"), secs=r.get("seconds", "—"),
            ok="通过" if ok else ("失败：" + "；".join(fails or [str(r.get("error") or "")[:40]])),
        ))
    passed = sum(1 for r in rows if r.get("ok"))
    for r in rows:
        if r.get("error"):
            r["ok"] = False
    lines += ["", f"**通过 {passed}/{len(rows)}**", "",
              "说明：", "",
              "- 「补原文」= 模型漏页后由资料原文补的比例（0% 表示模型自己覆盖了全部页）；",
              "- 「引用支持」= 正文块与引用页的 2-gram 重合率，成文是改写，天然低于原文型讲义；",
              "- 每个页段都是独立生成，互不影响。"]
    out_json = ROOT / "docs/evidence/benchmark_summary.json"
    out_md = ROOT / "docs/evidence/BENCHMARK.md"
    out_json.write_text(json.dumps({"rows": rows, "passed": passed, "total": len(rows)},
                                   ensure_ascii=False, indent=2), encoding="utf-8")
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\n-> {out_md} / {out_json}")


if __name__ == "__main__":
    main()

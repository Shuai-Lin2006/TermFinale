"""Canonical pipeline: pages -> facts -> coverage plans -> deterministic gate."""
from __future__ import annotations

from tfv2.authoring.page_facts import extract_page_facts
from tfv2.domain.page import PageLedger
from .model import CanonicalDocument, Fact, FactKind, SectionPlan
from .curate import curate_facts

_KIND = {
    "definitions": FactKind.DEFINITION,
    "formulas": FactKind.FORMULA,
    "conclusions": FactKind.CONCLUSION,
    "pitfalls": FactKind.PITFALL,
    "figures": FactKind.FIGURE,
}


def facts_from_ledger(ledger: PageLedger, *, per_kind: int = 8) -> list[Fact]:
    facts: list[Fact] = []
    seen: set[str] = set()
    for page in ledger.pages:
        raw = extract_page_facts(page.text, limit=per_kind)
        for key, kind in _KIND.items():
            for text in raw.get(key, []):
                key_text = " ".join(text.split())[:120]
                if key_text in seen:
                    continue
                seen.add(key_text)
                facts.append(Fact(
                    fact_id=f"p{page.page_no}-{len([f for f in facts if f.page == page.page_no]) + 1}",
                    page=page.page_no, kind=kind, text=text,
                    source_span=f"p{page.page_no}",
                ))
    return facts


def plan_sections(facts: list[Fact], *, pages_per_section: int = 2, max_facts: int = 16) -> list[SectionPlan]:
    """Greedy page-adjacent coverage: every fact lands in exactly one plan."""
    if not facts:
        return []
    pages = sorted({f.page for f in facts})
    plans: list[SectionPlan] = []
    current: list[Fact] = []
    start = pages[0]
    end = start + pages_per_section - 1
    for fact in sorted(facts, key=lambda f: (f.page, f.fact_id)):
        if fact.page > end or len(current) >= max_facts:
            plans.append(SectionPlan(plan_id=f"pl{len(plans)+1}", page_start=start,
                                     page_end=min(end, max(f.page for f in current)),
                                     fact_ids=[f.fact_id for f in current]))
            start = fact.page
            end = start + pages_per_section - 1
            current = []
        current.append(fact)
    if current:
        plans.append(SectionPlan(plan_id=f"pl{len(plans)+1}", page_start=start,
                                 page_end=max(f.page for f in current),
                                 fact_ids=[f.fact_id for f in current]))
    return plans


def run_canonical(ledger: PageLedger, *, document_id: str | None = None) -> CanonicalDocument:
    facts = curate_facts(facts_from_ledger(ledger))
    plans = plan_sections(facts)
    planned = {fid for p in plans for fid in p.fact_ids}
    missing = sorted({f.fact_id for f in facts} - planned)
    issues = []
    if ledger.page_count != len(ledger.pages):
        issues.append("page ledger incomplete")
    if not facts:
        issues.append("no facts extracted")
    if missing:
        issues.append(f"unplanned facts: {len(missing)}")
    document = CanonicalDocument(
        document_id=document_id or ledger.material,
        material=ledger.material, page_count=ledger.page_count,
        facts=facts, plans=plans,
        status="validated" if not issues else "partial",
        issues=issues,
    )
    return document

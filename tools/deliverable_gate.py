"""交付 PDF 硬门禁：空白页/raw LaTeX/乱码。"""
from __future__ import annotations
from pathlib import Path
from tfv2.quality.pdf_gate import validate_pdf

def main() -> None:
    files = sorted(Path('deliverables').glob('*.pdf'))
    bad = 0
    for p in files:
        issues = validate_pdf(p)
        print(f"{'PASS' if not issues else 'FAIL'} {p.name} {issues}")
        bad += 1 if issues else 0
    print(f"pdfs={len(files)} bad={bad}")
    if bad:
        raise SystemExit(1)

if __name__ == '__main__':
    main()

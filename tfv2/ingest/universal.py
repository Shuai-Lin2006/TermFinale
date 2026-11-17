"""Universal source ingress: PDF / PPTX / PPT / DOC / DOCX -> PageLedger."""
from __future__ import annotations

import subprocess
from pathlib import Path

from core.platform_utils import find_soffice
from tfv2.ingest.pdf import build_pdf_page_ledger
from tfv2.ingest.pptx import build_pptx_page_ledger

SUPPORTED = (".pdf", ".pptx", ".ppt", ".doc", ".docx")


class IngestError(RuntimeError):
    pass


def office_to_pdf(source: Path, out_dir: Path) -> Path:
    exe = find_soffice()
    if not exe:
        raise IngestError("需要 LibreOffice（soffice）才能转换 PPT/DOC/DOCX")
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run([exe, "--headless", "--convert-to", "pdf", "--outdir", str(out_dir), str(source)],
                       check=False, capture_output=True, text=True, timeout=180)
    except Exception as exc:
        raise IngestError(f"LibreOffice 转换失败：{exc}") from exc
    pdf = out_dir / f"{source.stem}.pdf"
    if not pdf.is_file():
        raise IngestError(f"LibreOffice 没有生成 PDF：{source.name}")
    return pdf


def open_source(source: str | Path, *, image_dir: str | Path | None = None):
    source = Path(source)
    suffix = source.suffix.lower()
    if suffix not in SUPPORTED:
        raise IngestError(f"不支持的类型：{suffix}；支持 {'/'.join(SUPPORTED)}")
    if suffix == ".pdf":
        return build_pdf_page_ledger(source, material_name=source.name, image_dir=image_dir)
    if suffix == ".pptx":
        return build_pptx_page_ledger(source, material_name=source.name, image_dir=image_dir)
    pdf = office_to_pdf(source, source.parent / ".converted_pdf")
    return build_pdf_page_ledger(pdf, material_name=source.name, image_dir=image_dir)

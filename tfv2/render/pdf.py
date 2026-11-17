"""把教材式 HTML 打成 A4 PDF，并回填真实目录页码。

依赖：Playwright（本机 Edge/Chromium）+ PyMuPDF。
不执行 KaTeX 之外的业务逻辑；页码由 PDF 实际分页测量。
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import fitz  # PyMuPDF
from playwright.sync_api import sync_playwright

from tfv2.domain.lecture import LectureSpec

EDGE = "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"
ROOT = Path(__file__).resolve().parents[2]
PAGEDJS = ROOT / "web_v2" / "assets" / "paged.polyfill.js"


def _set_toc_pages(html: str, mapping: dict[str, int]) -> str:
    for anchor, page in mapping.items():
        # <a href="#anchor"><span>title</span><span class="page">N</span></a>
        pattern = re.compile(
            r'(<a href="#' + re.escape(anchor) + r'"><span>.*?</span><span class="page">)\d+(</span>)',
            re.S,
        )
        html = pattern.sub(lambda m: m.group(1) + str(page) + m.group(2), html, count=1)
    return html


def _page_map(pdf_path: Path, spec: LectureSpec) -> tuple[dict[str, int], int]:
    doc = fitz.open(pdf_path)
    pages = [p.get_text("text") for p in doc]
    toc_page = next((i for i, t in enumerate(pages) if "目录" in t), 0)
    mapping: dict[str, int] = {}
    for item in spec.toc:
        found = None
        for i in range(toc_page + 1, len(pages)):
            for block in doc[i].get_text("dict").get("blocks", []):
                for line in block.get("lines", []):
                    text = "".join(span.get("text", "") for span in line.get("spans", [])).strip()
                    size = max((span.get("size", 0) for span in line.get("spans", [])), default=0)
                    if size >= 12.6 and (text == item.title or
                                         (text.startswith(item.title) and len(text) <= len(item.title) + 6)):
                        found = i + 1
                        break
                if found:
                    break
            if found:
                break
        if found:
            mapping[item.anchor] = found
    total = len(pages)
    doc.close()
    return mapping, total

def _browser_launch() -> dict:
    """Use the OS browser on Windows instead of relying on a bundled Chromium."""
    launch = {"headless": True, "args": ["--no-sandbox"]}
    if sys.platform == "win32":
        # Playwright's msedge channel uses the WebView2-era Edge install that
        # Windows 10/11 ships/updates automatically.
        launch["channel"] = "msedge"
        return launch
    if sys.platform == "darwin" and Path(EDGE).is_file():
        launch["executable_path"] = EDGE
        return launch
    override = os.getenv("TERMFINALE_BROWSER", "").strip()
    if override and Path(override).is_file():
        launch["executable_path"] = override
    return launch


def _use_pagedjs(spec: LectureSpec) -> bool:
    forced = os.getenv("TERMFINALE_PAGEDJS", "").strip().lower()
    if forced in ("0", "false", "no"):
        return False
    if forced in ("1", "true", "yes"):
        return True
    # Paged.js currently breaks KaTeX in this document template. Only enable it
    # automatically for formula-free lectures; formula fidelity is the hard rule.
    for sec in spec.sections:
        for block in sec.blocks:
            if "formula" in str(getattr(block.kind, "value", block.kind)).lower():
                return False
            if "$" in (block.text or ""):
                return False
            # Paged.js does not reliably repeat <thead> across pages; native
            # Chromium does. A pipe table therefore forces native pagination.
            if (block.text or "").count("|") >= 4:
                return False
            fig = getattr(block, "figure", None)
            if fig is not None and str(getattr(fig, "origin", "")) == "source":
                # Paged.js can create a blank page before a tall source figure.
                # Native Chromium pagination handles mixed text+images better.
                return False
    return PAGEDJS.is_file()


def _with_pagedjs(html: str) -> str:
    if not PAGEDJS.is_file():
        return html
    tag = f'<script src="{PAGEDJS.as_uri()}"></script>'
    if "</body>" in html:
        # The reader JS contains a literal "</body></html>" inside an export
        # string. Replacing the first occurrence injected Paged.js into the
        # script and made the whole JS block print as PDF text.
        head, tail = html.rsplit("</body>", 1)
        return head + tag + "</body>" + tail
    return html + tag


_CURRENT_SPEC = None


def _print_pdf(html_path: Path, pdf_path: Path, spec: LectureSpec | None = None) -> None:
    global _CURRENT_SPEC
    _CURRENT_SPEC = spec
    with sync_playwright() as p:
        browser = p.chromium.launch(**_browser_launch())
        page = browser.new_page()
        page.goto(html_path.resolve().as_uri(), wait_until="networkidle", timeout=120000)
        try:
            page.wait_for_function(
                "() => window.renderMathInElement && document.querySelectorAll('.katex').length > 0",
                timeout=20000,
            )
        except Exception:
            pass
        page.wait_for_timeout(2500)
        if _use_pagedjs(_CURRENT_SPEC) and PAGEDJS.is_file():
            try:
                page.evaluate("""async () => {
                    if (window.Paged && window.Paged.Previewer) {
                        await new Paged.Previewer().preview();
                    }
                }""")
                page.wait_for_timeout(800)
            except Exception:
                pass
        page.emulate_media(media="print")
        # Reader controls are interactive chrome; they must never become
        # printed pages. Remove them from the temporary print DOM instead of
        # relying only on @media print (Paged.js clones the DOM).
        try:
            page.evaluate("""() => {
                document.querySelectorAll('.tf-reader-tools,.tf-search-bar,.tf-ai-panel,.tf-export-menu,.tf-practice,.tf-selection-tools').forEach(function (n) { n.remove(); });
            }""")
        except Exception:
            pass
        page.pdf(
            path=str(pdf_path),
            format="A4",
            print_background=True,
            display_header_footer=True,
            header_template="<div></div>",
            footer_template=(
                '<div style="font-size:9px;width:100%;text-align:center;color:#666;'
                'font-family:Arial,sans-serif;"><span class="pageNumber"></span> / '
                '<span class="totalPages"></span></div>'
            ),
            margin={"top": "17mm", "bottom": "17mm", "left": "18mm", "right": "18mm"},
        )
        browser.close()


def write_pdf(html_path: Path, pdf_path: Path, spec: LectureSpec, *, passes: int = 2) -> tuple[Path, dict[str, int], int]:
    """生成 PDF；用实际 PDF 分页回填 TOC 页码，迭代到页码稳定。"""
    html_path = Path(html_path)
    pdf_path = Path(pdf_path)
    html = html_path.read_text(encoding="utf-8")
    mapping: dict[str, int] = {}
    total = 0
    for _ in range(max(1, passes)):
        work = _set_toc_pages(html, mapping) if mapping else html
        tmp_html = html_path.with_name(html_path.stem + "_paged.html")
        if _use_pagedjs(spec):
            work = _with_pagedjs(work)
        tmp_html.write_text(work, encoding="utf-8")
        _print_pdf(tmp_html, pdf_path, spec)
        new_map, total = _page_map(pdf_path, spec)
        if new_map == mapping:
            break
        mapping = new_map
        html = _set_toc_pages(html, mapping)
    # final print with stable mapping
    tmp_html = html_path.with_name(html_path.stem + "_paged.html")
    final_html = _set_toc_pages(html, mapping)
    if _use_pagedjs(spec):
        final_html = _with_pagedjs(final_html)
    tmp_html.write_text(final_html, encoding="utf-8")
    _print_pdf(tmp_html, pdf_path, spec)
    # add PDF outline + clickable TOC
    doc = fitz.open(pdf_path)
    outline = [[t.level, t.title, mapping.get(t.anchor, 1)] for t in spec.toc]
    if outline:
        doc.set_toc(outline)
    chapter_page = mapping.get("chapter-title", 1)
    for item in spec.toc:
        target = mapping.get(item.anchor)
        if not target:
            continue
        for pno in range(0, max(0, chapter_page - 1)):
            page = doc[pno]
            if "目录" not in page.get_text():
                continue
            for rect in page.search_for(item.title):
                page.insert_link({
                    "kind": fitz.LINK_GOTO,
                    "from": rect,
                    "page": target - 1,
                    "to": fitz.Point(0, 0),
                })
    doc.saveIncr()
    total = doc.page_count
    doc.close()
    # update the screen HTML so目录页码和 PDF 一致
    html_path.write_text(_set_toc_pages(html, mapping), encoding="utf-8")
    return pdf_path, mapping, total

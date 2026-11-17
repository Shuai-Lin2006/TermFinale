"""把考试 JSON 渲染成 HTML（KaTeX）再打印 PDF，避免 docx 中文/公式问题。"""
from __future__ import annotations
import html, json, sqlite3
from pathlib import Path
from playwright.sync_api import sync_playwright
from tfv2.quality.pdf_gate import validate_pdf

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:8907/"


def esc(x): return html.escape(str(x or ""))


def build_html(doc: dict, title: str) -> str:
    content = doc.get("content") or doc
    out = [f"<h1>{esc(title)}</h1>",
           f"<p class=meta>满分 {content.get('total_score')} 分 · 科目 {esc(content.get('subject'))} · 难度 {content.get('difficulty')}/5</p>"]
    n = 0
    answers = []
    for sec in content.get("sections") or []:
        out.append(f"<h2>{esc(sec.get('name'))}</h2>")
        for q in sec.get("questions") or []:
            n += 1
            out.append(f"<div class=q><div class=stem>{n}. {esc(q.get('stem'))} <span class=score>（{q.get('score')} 分）</span></div>")
            if q.get("figure_data"):
                out.append(f"<figure><img src='{q['figure_data']}'><figcaption>{esc(q.get('figure_caption') or 'AI 结构示意图')}</figcaption></figure>")
            for i, opt in enumerate(q.get("options") or []):
                out.append(f"<div class=opt>{chr(65+i)}. {esc(opt)}</div>")
            answers.append(f"<div class=ans><strong>{n}. 参考答案：</strong>{esc(q.get('answer_text') or q.get('answer'))}<br><em>解析：</em>{esc(q.get('analysis'))}</div>")
            out.append("</div>")
    out.append("<h2>参考答案与解析</h2>" + "".join(answers))
    return f"""<!doctype html><html lang=zh-CN><head><meta charset=utf-8>
<link rel=stylesheet href="/web/assets/katex/katex.min.css">
<style>
@page {{ size: A4; margin: 18mm 16mm; }}
body {{ font-family: "Songti SC","Noto Serif CJK SC",serif; font-size: 12pt; line-height: 1.75; color:#111; }}
h1 {{ font-size: 22pt; text-align:center; margin: 0 0 6px; }}
h2 {{ font-size: 15pt; margin: 18px 0 8px; border-bottom:1px solid #999; padding-bottom:4px; }}
.meta {{ text-align:center; color:#555; font-size:10pt; margin-bottom:18px; }}
.q {{ margin: 10px 0 14px; break-inside: avoid; }}
.stem {{ font-weight:600; }}
.score {{ font-weight:400; color:#666; font-size:10pt; }}
.opt {{ margin-left: 2em; }}
figure {{ margin: 8px auto; text-align:center; break-inside:avoid; }}
figure img {{ max-width: 78%; max-height: 230px; object-fit:contain; border:1px dashed #9ab7b3; }}
figcaption {{ font-size:9pt; color:#666; }}
.ans {{ font-size:10.5pt; margin: 6px 0 12px; page-break-inside: avoid; }}
</style></head><body>{''.join(out)}
<script src="/web/assets/katex/katex.min.js"></script>
<script src="/web/assets/katex/auto-render.min.js"></script>
<script>renderMathInElement(document.body,{{delimiters:[{{left:'$$',right:'$$',display:true}},{{left:'$',right:'$',display:false}},{{left:'\\\\(',right:'\\\\)',display:false}}]}});</script>
</body></html>"""


def main():
    db = sqlite3.connect(ROOT / "data/product.sqlite3")
    jobs = {
        "0b644a6621cf4790abaf824fb71c1fc5": "deliverables/05_电路12题.pdf",
        "c8bb6c959efd492dbf6386a4589bf00d": "deliverables/06_高等数学12题.pdf",
    }
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel="msedge")
        page = browser.new_page()
        page.goto(BASE, wait_until="networkidle")
        for did, rel in jobs.items():
            row = db.execute("SELECT title,content FROM documents WHERE id=?", (did,)).fetchone()
            doc = json.loads(row[1]); out = ROOT / rel
            page.set_content(build_html(doc, row[0]), wait_until="networkidle")
            page.wait_for_timeout(800)
            page.pdf(path=str(out), format="A4", print_background=True)
            issues = validate_pdf(out)
            if issues:
                raise RuntimeError(f"{out}: {issues}")
            print(out, out.stat().st_size)
        browser.close()


if __name__ == "__main__":
    main()

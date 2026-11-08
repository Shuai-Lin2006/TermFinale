import markdown
import re
import os
import json
import base64
import html as _html




def _gen_meta() -> str:
    try:
        from core.build_info import BUILD_TIME, VERSION
        return f"v{VERSION} · {BUILD_TIME}"
    except Exception:  # noqa: BLE001
        return "dev"

def _repair_image_tags(markdown: str) -> str:
    """AI 偶尔漏写 ]]]，会让正则一路吞到下一段，表现为图注里出现大段正文。"""
    fixed = []
    for line in markdown.split("\n"):
        if "[[[IMAGE:" in line and "]]]" not in line:
            line = line.rstrip() + "]]]"
        fixed.append(line)
    return "\n".join(fixed)


from pathlib import Path as _Path
import sys as _sys


def _katex_assets() -> str:
    """内联 KaTeX（含字体），避免离线/CDN 被墙时公式变成源码或整页白屏。"""
    roots = []
    if getattr(_sys, "_MEIPASS", ""):
        roots.append(_Path(_sys._MEIPASS))
    roots.append(_Path(_sys.executable).resolve().parent)
    roots.append(_Path(__file__).resolve().parent)
    rels = ("assets/katex", "core/assets/katex",
            "Resources/core/assets/katex", "../Resources/core/assets/katex")
    for root in roots:
        for rel in rels:
            base = (root / rel).resolve()
            if (base / "katex.inline.css").is_file():
                try:
                    css = (base / "katex.inline.css").read_text(encoding="utf-8")
                    js = (base / "katex.min.js").read_text(encoding="utf-8")
                    auto = (base / "auto-render.min.js").read_text(encoding="utf-8")
                    return f"<style>{css}</style>\n<script>{js}</script>\n<script>{auto}</script>"
                except OSError:
                    break
    # 兜底：异步 CDN，不阻塞页面渲染
    return ('<link rel="stylesheet" href="https://cdn.bootcdn.net/ajax/libs/KaTeX/0.16.8/katex.min.css">'
            '<script async src="https://cdn.bootcdn.net/ajax/libs/KaTeX/0.16.8/katex.min.js"></script>'
            '<script async src="https://cdn.bootcdn.net/ajax/libs/KaTeX/0.16.8/contrib/auto-render.min.js"></script>')


def export_to_html(markdown_text: str, output_file: str = "讲义.html", course=None, persona: str = "老师",
                   doc_type: str = "讲义", lang: str = "中文"):
    markdown_text = _repair_image_tags(markdown_text)
    # 常见 OCR/AI 误写的 LaTeX 命令，KaTeX 会把它们渲染成红色错误
    markdown_text = markdown_text.replace("\\cdotp", "\\cdot").replace("\\cdtos", "\\cdot")
    markdown_text = re.sub(r'\\\[(.*?)\\\]', r'$$\1$$', markdown_text, flags=re.DOTALL)
    markdown_text = re.sub(r'\\\((.*?)\\\)', r'$\1$', markdown_text, flags=re.DOTALL)
    markdown_text = re.sub(r'(?<!\[)\[([^\[\]|]+)\s*\|\s*([^\[\]]+)\](?!\])', r'[[\1 | \2]]', markdown_text)

    img_blocks = []

    def protect_img(match):
        img_blocks.append(match.group(1).strip())
        return f"@@IMAGEBLOCK{len(img_blocks) - 1}@@"

    processed_md = re.sub(r'\[\[\[IMAGE:\s*([^]]+)\]\]\]', protect_img, markdown_text)

    # 🚨 终极防白屏：只要是被 ``` 包裹的，统统当思维导图抓出来
    blank_blocks = []

    def protect_blank(match):
        blank_blocks.append(match.group(1) or "140")
        return f"@@BLANKBLOCK{len(blank_blocks) - 1}@@"

    processed_md = re.sub(r"\[\[BLANK(?::(\d+))?\]\]", protect_blank, processed_md)

    mermaid_blocks = []

    def protect_mermaid(match):
        code = match.group(1).strip()
        mermaid_blocks.append(f'<div class="mermaid-container"><div class="mermaid">\n{code}\n</div></div>')
        return f"@@MERMAIDBLOCK{len(mermaid_blocks) - 1}@@"

    processed_md = re.sub(r'```(?:mermaid)?\s*([\s\S]*?)```', protect_mermaid, processed_md)

    keyword_blocks = []

    def protect_keyword(match):
        full_text = match.group(1).strip()
        if "|" in full_text:
            word, explain = full_text.split("|", 1)
            word = word.strip()
            explain = explain.strip()
        else:
            word = full_text
            explain = "暂无详细解释" if lang == "中文" else "No detailed explanation yet."

        word = word.replace('"', '&quot;').replace("'", "&#39;")
        explain = explain.replace('"', '&quot;').replace("'", "&#39;")
        keyword_blocks.append(f'<span class="keyword" onclick="showModal(\'{word}\', \'{explain}\')">{word}</span>')
        return f"@@KEYWORD{len(keyword_blocks) - 1}@@"

    processed_md = re.sub(r'\[\[\s*(.*?)\s*\]\]', protect_keyword, processed_md, flags=re.DOTALL)

    if doc_type in ["训练试卷", "Test Paper", "Exam Paper"]:
        toc_html = ""
    else:
        chapter_counter = 0

        def add_chapter_num(match):
            nonlocal chapter_counter
            title = match.group(1).strip()
            clean_title = re.sub(r'@@KEYWORD\d+@@|@@MERMAIDBLOCK\d+@@|@@IMAGEBLOCK\d+@@', '图表', title).strip()
            # 去掉 AI 自带的编号/前缀，避免出现「第 1 章：核心考点：xxx」这种双前缀
            for _ in range(2):
                clean_title = re.sub(r'^\s*(第\s*\d+\s*章|Chapter\s*\d+)\s*[:：、.]?\s*', '',
                                     clean_title, flags=re.IGNORECASE).strip()
                clean_title = re.sub(r'^\s*(核心考点|章节导览|Core Concept)\s*[:：]\s*', '',
                                     clean_title, flags=re.IGNORECASE).strip()

            if clean_title.endswith("（续）") or clean_title.endswith("(cont.)"):
                return f"### {clean_title}"  # 续块不占章节号
            chapter_counter += 1
            if lang == "English":
                return f"## Chapter {chapter_counter}: {clean_title if clean_title else 'Core Concepts'}"
            return f"## 第 {chapter_counter} 章：{clean_title if clean_title else '核心考点解析'}"

        processed_md = re.sub(r'##\s*(核心考点：.*|章节导览.*|第.*章.*|Core Concept:.*|Chapter.*)', add_chapter_num,
                              processed_md)

        headers = []
        if lang == "English":
            headers = re.findall(r'^##\s+(.+)$', processed_md, flags=re.MULTILINE)
            toc_title = "Table of Contents"
        else:
            headers = re.findall(r'^##\s+(.+)$', processed_md, flags=re.MULTILINE)
            headers = [h for h in headers if '考点' not in h]
            toc_title = "目录"

        toc_html = f"<div class='toc-box'><h2>📑 {toc_title}</h2><ul>"
        for i, h in enumerate(headers): toc_html += f"<li><a href='#chapter-{i}'>{h}</a></li>"
        toc_html += "</ul></div>"
        if not headers: toc_html = ""

    math_blocks = []

    def protect_math(match):
        math_blocks.append(match.group(0))
        return f"@@MATHBLOCK{len(math_blocks) - 1}@@"

    processed_md = re.sub(r'\$\$.*?\$\$|\$.*?\$', protect_math, processed_md, flags=re.DOTALL)

    html_content = markdown.markdown(processed_md, extensions=['fenced_code', 'tables'])

    from core.paths import assets_dir

    img_dir = str(assets_dir())

    for i, kw in enumerate(keyword_blocks):
        html_content = html_content.replace(f"@@KEYWORD{i}@@", kw)
    for i, mb in enumerate(mermaid_blocks):
        html_content = html_content.replace(f"@@MERMAIDBLOCK{i}@@", mb)
    for i, math in enumerate(math_blocks):
        # 公式是最后塞回 HTML 的，必须转义 & < >：否则 $v_2<v_1$ 会被浏览器
        # 当成标签/实体，KaTeX 直接跳过，用户看到裸 LaTeX。
        html_content = html_content.replace(f"@@MATHBLOCK{i}@@",
                                            _html.escape(math, quote=False))

    for i, height in enumerate(blank_blocks):
        div = f'<div class="blank-space" style="height:{height}px"></div>'
        html_content = html_content.replace(f"<p>@@BLANKBLOCK{i}@@</p>", div)
        html_content = html_content.replace(f"@@BLANKBLOCK{i}@@", div)

    for i, raw in enumerate(img_blocks):
        parts = raw.split("|")
        filename = parts[0].strip()
        caption = parts[1].replace("图注:", "").strip() if len(parts) > 1 else ""
        caption = re.sub(r"（第\s*\d+\s*页）", "", caption).strip()
        caption = re.split(r"\[\[\[|#{2,}", caption)[0].strip()
        path = os.path.join(img_dir, filename)

        html_img = ""
        if os.path.exists(path):
            with open(path, "rb") as f: b64 = base64.b64encode(f.read()).decode('utf-8')
            ext = filename.split('.')[-1]
            html_img = f'<figure class="img-figure"><img src="data:image/{ext};base64,{b64}" class="img-responsive" alt="{caption}"><figcaption>{caption}</figcaption></figure>'

        html_content = html_content.replace(f"<p>@@IMAGEBLOCK{i}@@</p>", html_img)
        html_content = html_content.replace(f"@@IMAGEBLOCK{i}@@", html_img)

    html_content = re.sub(r'@@KEYWORD\d+@@', '', html_content)
    html_content = re.sub(r'@@MERMAIDBLOCK\d+@@', '', html_content)
    html_content = re.sub(r'@@IMAGEBLOCK\d+@@', '', html_content)
    html_content = re.sub(r'@@MATHBLOCK\d+@@', '', html_content)
    html_content = re.sub(r'@@BLANKBLOCK\d+@@', '', html_content)

    h2_counter = 0

    def add_h2_id(match):
        nonlocal h2_counter
        res = f'<h2 id="chapter-{h2_counter}" class="chapter-title">{match.group(1)}</h2>'
        h2_counter += 1
        return res

    html_content = re.sub(r'<h2>(.*?)</h2>', add_h2_id, html_content)

    html_content = re.sub(r'<blockquote>\s*<p>(📌 出处.*?|📌 Source.*?)</p>\s*</blockquote>',
                          r'<div class="meta-info">\1</div>', html_content, flags=re.DOTALL)
    html_content = re.sub(r'<p>\[出处：(.*?)\]</p>', r'<div class="meta-info">[出处：\1]</div>', html_content)
    html_content = re.sub(r'\[出处：(.*?)\]', r'<span class="meta-info">[出处：\1]</span>', html_content)

    custom_info = ""

    course_name = course.name if course else ""
    target_score = getattr(course, "target_score", None) if course else None
    cover_title = course_name or doc_type
    cover_desc = "" if doc_type in ("全量讲义", "讲义") else doc_type

    # 试卷专用卷头：姓名/学号/时间/满分 + 密封线
    exam_header = ""
    if doc_type in ("训练试卷", "Test Paper", "Exam Paper"):
        course_name = course.name if course else ""
        if lang == "English":
            exam_header = f"""
        <div class="exam-head">
            <h1>{course_name} Final Mock Exam</h1>
            <div class="exam-meta">
                <span>Name: ____________</span><span>ID: ____________</span>
                <span>Time: 120 min</span><span>Total: 100 pts</span>
            </div>
            <div class="seal-line">— — — — — — — —  Seal Line  — — — — — — — —</div>
        </div>"""
        else:
            exam_header = f"""
        <div class="exam-head">
            <h1>{course_name}期末模拟试卷</h1>
            <div class="exam-meta">
                <span>姓名：____________</span><span>学号：____________</span>
                <span>考试时间：120 分钟</span><span>满分：100 分</span>
            </div>
            <div class="seal-line">— — — — — — — — 密 封 线 — — — — — — — —</div>
        </div>"""

    btn_search = "Search" if lang == "English" else "搜索"
    btn_edit = "Edit" if lang == "English" else "编辑"
    btn_word = "Word" if lang == "English" else "Word"
    btn_pdf = "Print PDF" if lang == "English" else "打印 PDF"
    nav_reading = "Reading..." if lang == "English" else "正在阅读..."
    modal_title = "Explanation" if lang == "English" else "名词解释"

    cover_html = f'<div class="cover"><h1>{cover_title}</h1><p>{cover_desc}</p></div>' 
    if exam_header:
        cover_html = ""

    html_template = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{course.name if course else '文档'} - {doc_type}</title>
<style>.math-fallback{{font-family:ui-monospace,Menlo,monospace;color:var(--ink-2);background:var(--paper-2);border-radius:4px;padding:0 3px}}</style>
{_katex_assets()}
<script async src="https://cdn.bootcdn.net/ajax/libs/mermaid/10.6.1/mermaid.min.js"></script>
<script>
    document.addEventListener("DOMContentLoaded", function() {{
        if (window.renderMathInElement) {{
            renderMathInElement(document.body, {{ delimiters: [{{left: '$$', right: '$$', display: true}}, {{left: '$', right: '$', display: false}}], throwOnError: false }});
        }}
        // 残缺公式兜底：不把 KaTeX 红错交给用户/PDF
        setTimeout(function() {{
            document.querySelectorAll('.katex-error').forEach(function(el) {{
                var span = document.createElement('span');
                span.className = 'math-fallback';
                span.textContent = el.textContent || '';
                el.replaceWith(span);
            }});
        }}, 0);
        if (window.mermaid) {{
            mermaid.initialize({{ startOnLoad: true, theme: 'default', flowchart: {{ useMaxWidth: false }} }});
        }} else {{
            // Mermaid 未加载（离线/被墙）时，把源码显示成可读文本，而不是空白
            setTimeout(function() {{
                document.querySelectorAll('.mermaid-container').forEach(function(box) {{
                    var code = box.querySelector('.mermaid');
                    if (code) box.innerHTML = '<pre style="white-space:pre-wrap;text-align:left;font-size:13px;">' + code.textContent.trim() + '</pre>';
                }});
            }}, 2500);
        }}
    }});
    function showModal(title, content) {{
        document.getElementById('modalTitle').innerText = title;
        var _mc = document.getElementById('modalContent');
        _mc.innerText = content;
        // 名词解释里可能有 $...$；弹窗也要渲染，不能直接显示源码
        if (window.renderMathInElement) {{
            try {{
                renderMathInElement(_mc, {{delimiters: [
                    {{left: '$$', right: '$$', display: true}},
                    {{left: '$', right: '$', display: false}}
                ], throwOnError: false}});
            }} catch (e) {{}}
        }}
        document.getElementById('myModal').style.display = "flex";
    }}
    function closeModal() {{ document.getElementById('myModal').style.display = "none"; }}
    let isEditing = false;
    function toggleEdit() {{
        isEditing = !isEditing;
        const container = document.getElementById('main-container');
        const btn = document.getElementById('edit-btn');
        if (isEditing) {{
            container.setAttribute('contenteditable', 'true');
            container.style.outline = "2px dashed #007AFF";
            btn.innerText = "💾 {'Save & Exit' if lang == 'English' else '保存并退出编辑'}";
            btn.style.background = "#34C759";
        }} else {{
            container.removeAttribute('contenteditable');
            container.style.outline = "none";
            btn.innerText = "✏️ {'Edit Mode' if lang == 'English' else '编辑模式'}";
            btn.style.background = "#007AFF";
            alert("{'Exited edit. To save, press Ctrl+P.' if lang == 'English' else '已退出编辑。如需保存修改，请按 Ctrl+P 选择另存为PDF。'}");
        }}
    }}
    function exportWord() {{
        const clone = document.body.cloneNode(true);
        clone.querySelectorAll('.top-nav, #myModal, .search-container, .search-results').forEach(el => el.remove());
        const html = `<html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'><head><meta charset='utf-8'><style>body {{ font-family: 'PingFang SC', sans-serif; }} table {{ border-collapse: collapse; width: 100%; }} th, td {{ border: 1px solid #ccc; padding: 8px; }}</style></head><body>${{clone.innerHTML}}</body></html>`;
        const blob = new Blob(['\\ufeff', html], {{ type: 'application/msword' }});
        const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = "{course.name if course else '文档'}_导出.docx"; a.click();
    }}
    function toggleSearch() {{
        const box = document.getElementById('search-container');
        box.style.display = box.style.display === 'none' ? 'block' : 'none';
        if(box.style.display === 'block') document.getElementById('search-input').focus();
    }}
    function performSearch() {{
        const keyword = document.getElementById('search-input').value.trim().toLowerCase();
        const resultsBox = document.getElementById('search-results');
        resultsBox.innerHTML = '';
        if(!keyword) {{ resultsBox.style.display = 'none'; return; }}
        const elements = document.querySelectorAll('#main-container p, #main-container li');
        let count = 0;
        elements.forEach((el, index) => {{
            if(el.innerText.toLowerCase().includes(keyword)) {{
                count++;
                const id = 'search-hit-' + count;
                el.id = id;
                const div = document.createElement('div');
                div.className = 'search-item';
                div.innerText = el.innerText.substring(0, 50) + '...';
                div.onclick = function() {{
                    document.getElementById(id).scrollIntoView({{behavior: 'smooth', block: 'center'}});
                    document.getElementById(id).style.background = '#FFEB3B';
                    setTimeout(() => document.getElementById(id).style.background = 'transparent', 2000);
                }};
                resultsBox.appendChild(div);
            }}
        }});
        resultsBox.style.display = count > 0 ? 'block' : 'none';
        if(count === 0) resultsBox.innerHTML = '<div style="padding:10px;color:#999">{'Not found' if lang == 'English' else '未找到相关内容'}</div>';
    }}
</script>
<style>
    sup.src {{ font-size: 7px; color: #b3b3b3; margin-left: 2px; vertical-align: super; font-family: ui-monospace,Menlo,monospace; float: right; }}
    body {{ font-family: -apple-system, "PingFang SC", sans-serif; background-color: #f4f6f9; color: #2c3e50; line-height: 1.9; margin: 0; padding: 40px 20px; }}
    .container {{ max-width: 850px; margin: 0 auto; background: #ffffff; padding: 50px 60px; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); }}
    h3 {{ font-size: 18px; color: #1a1a1a; background: #F0F8FF; padding: 12px 15px; border-radius: 8px; border-left: 5px solid #007AFF; margin-top: 30px; margin-bottom: 15px; }}
    ul {{ list-style-type: none; padding-left: 0; }}
    li {{ background: #ffffff; border: 1px solid #E5E5E5; border-radius: 8px; padding: 15px; margin-bottom: 12px; line-height: 1.8; }}
    li strong {{ color: #007AFF; font-size: 16px; }}
    p {{ margin-bottom: 16px; line-height: 1.8; white-space: pre-wrap; }}
    .img-container {{ text-align: center; margin: 20px auto; background: #fafafa; padding: 10px; border-radius: 8px; border: 1px solid #eee; max-width: 95%; }}
    .img-responsive {{ max-width: 92%; height: auto; max-height: 360px; object-fit: contain; border-radius: 6px; display: block; margin: 0 auto; }}
    .img-caption {{ color: #666; font-size: 13px; margin-top: 7px; line-height: 1.5; }}
    .img-figure {{ margin: 16px auto; text-align: center; page-break-inside: avoid; max-width: 95%; }}
    .img-figure img {{ max-width: 100%; max-height: 520px; width: auto; height: auto; border-radius: 6px; }}
    .img-figure figcaption {{ color: #666; font-size: 13px; margin-top: 7px; line-height: 1.5; }}
    .source-line {{ font-size: 10px; color: #999; text-align: right; margin: 10px 0 18px; }}

    /* 🚨 防止白屏：如果渲染失败，至少有个虚线框提示 */
    .mermaid-container {{ width: 100%; overflow-x: auto; background: #fff; padding: 20px; border-radius: 8px; border: 1px dashed #007AFF; margin: 30px 0; min-height: 150px; display: flex; justify-content: center; align-items: center; }}
    .mermaid {{ display: flex; justify-content: center; min-width: max-content; }}

    @page {{ margin: 2cm; }}
    @media print {{
        .top-nav, .modal-overlay, .search-container {{ display: none !important; }}
        body {{ background: #fff; padding: 0; margin: 0; }}
        .container {{ box-shadow: none; padding: 20px; max-width: 100%; border: none; }}
        h2.chapter-title {{ page-break-before: always; margin-top: 0; padding-top: 20px; border-bottom: 2px solid #000; }}
        h2.chapter-title:first-of-type {{ page-break-before: auto; }}
        li, .img-container, p {{ page-break-inside: avoid; }}
    }}
    .keyword {{ color: #007AFF; font-weight: bold; border-bottom: 2px dashed #007AFF; cursor: pointer; }}
    .modal-overlay {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.4); backdrop-filter: blur(5px); z-index: 9999; justify-content: center; align-items: center; }}
    .modal-box {{ background: #ffffff; padding: 30px 40px; border-radius: 16px; box-shadow: 0 20px 50px rgba(0,0,0,0.2); max-width: 500px; width: 90%; position: relative; }}
    .modal-title {{ font-size: 22px; color: #0056b3; margin-bottom: 15px; font-weight: bold; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
    .modal-content {{ font-size: 16px; color: #333; line-height: 1.8; }}
    .close-btn {{ position: absolute; top: 15px; right: 20px; font-size: 24px; color: #999; cursor: pointer; }}
    .top-nav {{ position: fixed; top: 20px; right: 30px; z-index: 1000; display: flex; gap: 10px; align-items: center; }}
    .top-nav a, .top-nav button {{ display: inline-block; background: #ffffff; color: #0056b3; padding: 10px 20px; border-radius: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); text-decoration: none; font-weight: bold; border: 1px solid #e1e8ed; font-size: 14px; cursor: pointer; border: none; outline: none; }}
    .top-nav a:hover, .top-nav button:hover {{ background: #0056b3; color: #ffffff; }}
    .print-btn {{ background: #34C759 !important; color: #fff !important; }}
    .word-btn {{ background: #2B579A !important; color: #fff !important; }}
    .edit-btn {{ background: #007AFF !important; color: #fff !important; }}
    .search-btn {{ background: #FF9500 !important; color: #fff !important; }}
    .search-container {{ display: none; position: fixed; top: 70px; right: 30px; z-index: 1000; width: 300px; background: #fff; padding: 15px; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.15); border: 1px solid #eee; }}
    .search-container input {{ width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 8px; box-sizing: border-box; outline: none; }}
    .search-results {{ display: none; margin-top: 10px; max-height: 300px; overflow-y: auto; }}
    .search-item {{ padding: 10px; border-bottom: 1px solid #eee; cursor: pointer; font-size: 14px; color: #333; }}
    .search-item:hover {{ background: #f0f8ff; color: #007AFF; }}
    .current-chapter {{ background: #333; color: #fff; padding: 10px 20px; border-radius: 30px; font-weight: bold; font-size: 14px; max-width: 250px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
    .cover {{ text-align: center; padding: 60px 0; border-bottom: 2px dashed #eee; margin-bottom: 40px; }}
    .exam-head {{ text-align: center; margin-bottom: 26px; }}
    .exam-head h1 {{ font-size: 30px; color: #1a1a1a; border: none; margin-bottom: 14px; }}
    .exam-meta {{ display: flex; justify-content: center; gap: 18px; flex-wrap: wrap; font-size: 15px; color: #333; margin-bottom: 12px; }}
    .seal-line {{ color: #999; letter-spacing: 2px; font-size: 13px; margin: 10px 0 26px; }}
    .cover h1 {{ font-size: 38px; color: #0056b3; border: none; margin-bottom: 10px; }}
    .cover p {{ color: #86868B; font-size: 16px; letter-spacing: 1px; margin-bottom: 30px; }}
    .custom-info {{ display: flex; justify-content: center; gap: 15px; flex-wrap: wrap; margin-top: 20px; }}
    .info-item {{ background: #f8fafd; border: 1px solid #e1e8ed; padding: 10px 20px; border-radius: 12px; font-size: 14px; color: #555; }}
    .info-item strong {{ color: #0056b3; font-size: 16px; margin-left: 8px; }}
    .toc-box {{ background: #f8fafd; padding: 20px 30px; border-radius: 12px; margin-bottom: 40px; border: 1px solid #e1e8ed; }}
    .toc-box h2 {{ font-size: 20px; margin-top: 0; border: none; color: #1a1a1a; }}
    .toc-box ul {{ list-style: none; padding-left: 0; margin-bottom: 0; }}
    .toc-box li {{ margin: 10px 0; font-size: 15px; background: none; border: none; padding: 0; }}
    .toc-box a {{ color: #333333; text-decoration: none; }}
    h2.chapter-title {{ font-size: 24px; color: #0056b3; margin-top: 60px; padding-left: 12px; border-left: 5px solid #007AFF; }}


    /* ---------- v2 教材体 ---------- */
    body {{ background: #fafaf8; color: #14161a; padding: 0; }}
    .container {{ max-width: 900px; margin: 0 auto; padding: 0 36px 80px; background: #fff;
      box-shadow: 0 12px 40px rgba(20,22,26,.06); }}
    .cover {{ text-align: left; padding: 56px 0 30px; border-bottom: 1px solid #e6e4de; margin-bottom: 34px; }}
    .cover h1 {{ font-family: "Songti SC","STSong",serif; font-size: 44px; line-height: 1.2;
      color: #14161a; margin: 6px 0 10px; border: 0; }}
    .cover p {{ color: #6f7480; font-size: 15px; letter-spacing: .02em; margin: 0 0 6px; }}
    .designer {{ font-size: 11.5px; letter-spacing: .06em; color: #9aa0aa; }}
    .doc-stats {{ display: flex; flex-wrap: wrap; gap: 10px 30px; margin-top: 20px; padding-top: 14px;
      border-top: 1px solid #e6e4de; }}
    .doc-stats div {{ min-width: 76px; }}
    .doc-stats span {{ display: block; font-size: 11px; color: #9aa0aa; letter-spacing: .04em; }}
    .doc-stats b {{ display: block; font-size: 15px; color: #14161a; font-weight: 600; margin-top: 2px; }}
    .info-item {{ background: transparent; border: 1px solid #e6e4de; border-radius: 10px;
      padding: 8px 14px; font-size: 13px; color: #3a3d44; }}
    .info-item strong {{ color: #14161a; }}
    h2.chapter-title {{ font-family: "Songti SC","STSong",serif; font-size: 28px; color: #14161a;
      border-left: 0; border-bottom: 1px solid #e6e4de; padding: 0 0 10px; margin-top: 58px; }}
    .top-nav {{ top: 14px; right: 18px; gap: 4px; padding: 6px; border-radius: 12px;
      background: rgba(255,255,255,.88); backdrop-filter: blur(12px);
      border: 1px solid #e6e4de; box-shadow: 0 6px 20px rgba(20,22,26,.08); }}
    .top-nav a, .top-nav button, .search-btn, .edit-btn, .word-btn, .print-btn {{
      background: transparent !important; color: #3a3d44 !important; border: 0; border-radius: 8px;
      padding: 7px 10px; font-weight: 500; font-size: 12.5px; box-shadow: none; }}
    .top-nav a:hover, .top-nav button:hover {{ background: #f2f1ed !important; color: #14161a !important; }}
    .current-chapter {{ background: transparent !important; color: #6f7480 !important; font-size: 12px;
      padding: 6px 8px; max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
    blockquote {{ display: block !important; margin: 16px 0; padding: 12px 16px; background: #eaf2ef;
      border-left: 3px solid #0f5b4c; border-radius: 0 8px 8px 0; }}
    h2.chapter-title {{ border-left: 0 !important; background: transparent !important; }}
    h3 {{ background: transparent !important; border-left: 0 !important; padding-left: 0 !important;
      font-size: 17px !important; color: #14161a !important; margin: 28px 0 6px !important; }}
    .img-responsive {{ max-height: 360px; }}
    .toc-box {{ background: #fafaf8; border-color: #e6e4de; }}
    @media print {{
      body {{ background: #fff; }}
      .container {{ box-shadow: none; max-width: none; padding: 0; }}
      .cover {{ padding-top: 10px; }}
      h2.chapter-title {{ page-break-after: avoid; }}
    }}

    .blank-space {{ border-bottom: 1px dashed #c9c9c9; margin: 12px 0 22px; }}
    @media print {{ .blank-space {{ border-bottom: 1px dashed #bbb; }} }}
    .meta-info, p > .meta-info {{ font-size: 12px !important; color: #999 !important; background: transparent !important; border-left: none !important; padding: 0 !important; margin: 4px 0 !important; display: inline-block; }}
    blockquote {{ display: none; }} 
</style>
</head>
<body id="top">
    <div id="myModal" class="modal-overlay" onclick="closeModal()"><div class="modal-box" onclick="event.stopPropagation()"><span class="close-btn" onclick="closeModal()">&times;</span><div class="modal-title" id="modalTitle">{modal_title}</div><div class="modal-content" id="modalContent">Loading...</div></div></div>
    <div class="search-container" id="search-container">
        <input type="text" id="search-input" placeholder="{btn_search}..." oninput="performSearch()">
        <div class="search-results" id="search-results"></div>
    </div>
    <div class="top-nav">
        <div class="current-chapter" id="nav-title">{nav_reading}</div>
        <button class="search-btn" onclick="toggleSearch()">🔍 {btn_search}</button>
        <button class="edit-btn" id="edit-btn" onclick="toggleEdit()">✏️ {btn_edit}</button>
        <button class="word-btn" onclick="exportWord()">📄 {btn_word}</button>
        <a class="print-btn" onclick="window.print()">🖨️ {btn_pdf}</a>
    </div>
    <div class="container" id="main-container">
        {cover_html}
        {exam_header}
        {toc_html}
        {html_content}
    </div>
    <div style="text-align:center;color:#9ca3af;font-size:12px;margin:40px 0 20px;">
        Generated by TermFinale · {_gen_meta()}
    </div>
    <script>
        window.addEventListener('scroll', function() {{
            const titles = document.querySelectorAll('.chapter-title');
            const navTitle = document.getElementById('nav-title');
            let currentTitle = "{nav_reading}";
            titles.forEach(title => {{ if (title.getBoundingClientRect().top <= 100) currentTitle = title.innerText; }});
            if (navTitle.innerText !== currentTitle) navTitle.innerText = currentTitle;
        }});
    </script>
</body>
</html>"""
    # 阅读器增强：三栏目录/速查 + 选中提问（问答令牌由本地桥提供）
    try:
        assets = _Path(__file__).resolve().parent / "assets"
        reader_css = (assets / "reader.css").read_text(encoding="utf-8")
        reader_js = (assets / "reader.js").read_text(encoding="utf-8")
    except OSError:
        reader_css = reader_js = ""

    bridge = None
    try:
        from core.local_bridge import bridge_config
        bridge = bridge_config()
    except Exception:  # noqa: BLE001
        bridge = None
    course_name = ""
    if course:
        course_name = course.get("name", "") if isinstance(course, dict) else getattr(course, "name", "")

    head_extra = (f"<style>{reader_css}</style>\n"
                  f"<script>window.TF_BRIDGE={json.dumps(bridge)};"
                  f"window.TF_COURSE={json.dumps(course_name, ensure_ascii=False)};</script>")
    head_at = html_template.rfind("</head>")
    if head_at != -1:
        html_template = html_template[:head_at] + head_extra + "\n" + html_template[head_at:]
    body_at = html_template.rfind("</body>")
    if body_at != -1:
        html_template = (html_template[:body_at] + f"<script>{reader_js}</script>\n"
                         + html_template[body_at:])

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_template)
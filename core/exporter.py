import markdown
import re
import os
import base64


def export_to_html(markdown_text: str, output_file: str = "讲义.html", course=None, persona: str = "老师",
                   doc_type: str = "讲义", lang: str = "中文"):
    markdown_text = re.sub(r'\\\[(.*?)\\\]', r'$$\1$$', markdown_text, flags=re.DOTALL)
    markdown_text = re.sub(r'\\\((.*?)\\\)', r'$\1$', markdown_text, flags=re.DOTALL)
    markdown_text = re.sub(r'(?<!\[)\[([^\[\]|]+)\s*\|\s*([^\[\]]+)\](?!\])', r'[[\1 | \2]]', markdown_text)

    img_blocks = []

    def protect_img(match):
        img_blocks.append(match.group(1).strip())
        return f"@@IMAGEBLOCK{len(img_blocks) - 1}@@"

    processed_md = re.sub(r'\[\[\[IMAGE:\s*([^]]+)\]\]\]', protect_img, markdown_text)

    # 🚨 终极防白屏：只要是被 ``` 包裹的，统统当思维导图抓出来
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
            chapter_counter += 1
            title = match.group(1).strip()
            clean_title = re.sub(r'@@KEYWORD\d+@@|@@MERMAIDBLOCK\d+@@|@@IMAGEBLOCK\d+@@', '图表', title).strip()

            if lang == "English":
                return f"## Chapter {chapter_counter}: {clean_title if clean_title else 'Core Concepts'}"
            else:
                return f"## 第 {chapter_counter} 章：{clean_title if clean_title else '核心考点解析'}"

        processed_md = re.sub(r'##\s*(核心考点：.*|章节导览.*|第.*章.*|Core Concept:.*|Chapter.*)', add_chapter_num,
                              processed_md)

        headers = []
        if lang == "English":
            headers = re.findall(r'^##\s+(Chapter \d+:.*)', processed_md, flags=re.MULTILINE)
            toc_title = "Table of Contents"
        else:
            headers = re.findall(r'^##\s+(第 \d+ 章：.*)', processed_md, flags=re.MULTILINE)
            toc_title = "目录"

        toc_html = f"<div class='toc-box'><h2>📑 {toc_title}</h2><ul>"
        for i, h in enumerate(headers): toc_html += f"<li><a href='#chapter-{i}'>👉 {h}</a></li>"
        toc_html += "</ul></div>"
        if not headers: toc_html = ""

    math_blocks = []

    def protect_math(match):
        math_blocks.append(match.group(0))
        return f"@@MATHBLOCK{len(math_blocks) - 1}@@"

    processed_md = re.sub(r'\$\$.*?\$\$|\$.*?\$', protect_math, processed_md, flags=re.DOTALL)

    html_content = markdown.markdown(processed_md, extensions=['fenced_code', 'tables'])

    from core.database import BASE_DIR
    img_dir = os.path.join(BASE_DIR, "assets_images")

    for i, kw in enumerate(keyword_blocks):
        html_content = html_content.replace(f"@@KEYWORD{i}@@", kw)
    for i, mb in enumerate(mermaid_blocks):
        html_content = html_content.replace(f"@@MERMAIDBLOCK{i}@@", mb)
    for i, math in enumerate(math_blocks):
        html_content = html_content.replace(f"@@MATHBLOCK{i}@@", math)

    for i, raw in enumerate(img_blocks):
        parts = raw.split("|")
        filename = parts[0].strip()
        caption = parts[1].replace("图注:", "").strip() if len(parts) > 1 else ""
        path = os.path.join(img_dir, filename)

        html_img = ""
        if os.path.exists(path):
            with open(path, "rb") as f: b64 = base64.b64encode(f.read()).decode('utf-8')
            ext = filename.split('.')[-1]
            html_img = f'<div class="img-container"><img src="data:image/{ext};base64,{b64}" class="img-responsive"><div class="img-caption">📖 {caption}</div></div>'

        html_content = html_content.replace(f"<p>@@IMAGEBLOCK{i}@@</p>", html_img)
        html_content = html_content.replace(f"@@IMAGEBLOCK{i}@@", html_img)

    html_content = re.sub(r'@@KEYWORD\d+@@', '', html_content)
    html_content = re.sub(r'@@MERMAIDBLOCK\d+@@', '', html_content)
    html_content = re.sub(r'@@IMAGEBLOCK\d+@@', '', html_content)
    html_content = re.sub(r'@@MATHBLOCK\d+@@', '', html_content)

    h2_counter = 0

    def add_h2_id(match):
        nonlocal h2_counter
        res = f'<h2 id="chapter-{h2_counter}" class="chapter-title">{match.group(1)}</h2>'
        h2_counter += 1
        return res

    html_content = re.sub(r'<h2>(第 \d+ 章：.*?|Chapter \d+:.*?)</h2>', add_h2_id, html_content)

    html_content = re.sub(r'<blockquote>\s*<p>(📌 出处.*?|📌 Source.*?)</p>\s*</blockquote>',
                          r'<div class="meta-info">\1</div>', html_content, flags=re.DOTALL)
    html_content = re.sub(r'<p>\[出处：(.*?)\]</p>', r'<div class="meta-info">[出处：\1]</div>', html_content)
    html_content = re.sub(r'\[出处：(.*?)\]', r'<span class="meta-info">[出处：\1]</span>', html_content)

    custom_info = ""
    if course:
        lbl_target = "Target Score" if lang == "English" else "目标分数"
        lbl_days = "Days Left" if lang == "English" else "剩余天数"
        lbl_tutor = "Tutor" if lang == "English" else "专属导师"
        unit_score = "pts" if lang == "English" else "分"
        unit_day = "days" if lang == "English" else "天"

        custom_info = f"""
        <div class="custom-info">
            <div class="info-item"><span>🎯 {lbl_target}</span> <strong>{course.target_score} {unit_score}</strong></div>
            <div class="info-item"><span>⏳ {lbl_days}</span> <strong>{course.days_left} {unit_day}</strong></div>
            <div class="info-item"><span>💼 {lbl_tutor}</span> <strong>{persona}</strong></div>
        </div>
        """

    cover_title = "TermFinale Guide" if lang == "English" and doc_type == "专属讲义" else (
        "TermFinale Exam" if lang == "English" and doc_type == "训练试卷" else f"TermFinale {doc_type}")
    cover_desc = f"Your Personalized Final Prep · {course.name if course else ''}" if lang == "English" else f"为你量身定制的期末突击宝典 · {course.name if course else ''}"

    btn_search = "Search" if lang == "English" else "搜索"
    btn_edit = "Edit" if lang == "English" else "编辑"
    btn_word = "Word" if lang == "English" else "Word"
    btn_pdf = "Print PDF" if lang == "English" else "打印 PDF"
    nav_reading = "Reading..." if lang == "English" else "正在阅读..."
    modal_title = "Explanation" if lang == "English" else "名词解释"

    html_template = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{course.name if course else '文档'} - {doc_type}</title>
<link rel="stylesheet" href="https://cdn.bootcdn.net/ajax/libs/KaTeX/0.16.8/katex.min.css">
<script src="https://cdn.bootcdn.net/ajax/libs/KaTeX/0.16.8/katex.min.js"></script>
<script src="https://cdn.bootcdn.net/ajax/libs/KaTeX/0.16.8/contrib/auto-render.min.js"></script>
<script src="https://cdn.bootcdn.net/ajax/libs/mermaid/10.6.1/mermaid.min.js"></script>
<script>
    document.addEventListener("DOMContentLoaded", function() {{
        renderMathInElement(document.body, {{ delimiters: [{{left: '$$', right: '$$', display: true}}, {{left: '$', right: '$', display: false}}], throwOnError: false }});
        mermaid.initialize({{ startOnLoad: true, theme: 'default', flowchart: {{ useMaxWidth: false }} }});
    }});
    function showModal(title, content) {{
        document.getElementById('modalTitle').innerText = title;
        document.getElementById('modalContent').innerText = content;
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
    body {{ font-family: -apple-system, "PingFang SC", sans-serif; background-color: #f4f6f9; color: #2c3e50; line-height: 1.9; margin: 0; padding: 40px 20px; }}
    .container {{ max-width: 850px; margin: 0 auto; background: #ffffff; padding: 50px 60px; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); }}
    h3 {{ font-size: 18px; color: #1a1a1a; background: #F0F8FF; padding: 12px 15px; border-radius: 8px; border-left: 5px solid #007AFF; margin-top: 30px; margin-bottom: 15px; }}
    ul {{ list-style-type: none; padding-left: 0; }}
    li {{ background: #ffffff; border: 1px solid #E5E5E5; border-radius: 8px; padding: 15px; margin-bottom: 12px; line-height: 1.8; }}
    li strong {{ color: #007AFF; font-size: 16px; }}
    p {{ margin-bottom: 16px; line-height: 1.8; white-space: pre-wrap; }}
    .img-container {{ text-align: center; margin: 25px auto; background: #fafafa; padding: 15px; border-radius: 8px; border: 1px solid #eee; max-width: 95%; }}
    .img-responsive {{ max-width: 100%; height: auto; max-height: 500px; object-fit: contain; border-radius: 6px; display: block; margin: 0 auto; }}
    .img-caption {{ color: #666; font-size: 14px; margin-top: 10px; font-weight: 500; }}

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
        <div class="cover"><h1>{cover_title}</h1><p>{cover_desc}</p>{custom_info}</div>
        {toc_html}
        {html_content}
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
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_template)